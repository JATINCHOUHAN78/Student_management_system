"""Import a previously exported students.csv into the PostgreSQL database.

Usage:
  set DATABASE_URL=postgresql://...
  python migrate_students_csv.py students.csv

Expected columns: student_name, roll_number, email, phone, course, branch, semester, address
"""
import csv
import os
import sys
import psycopg2

def main(path):
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL before running this migration.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    with open(path, newline="", encoding="utf-8-sig") as f, psycopg2.connect(url) as conn:
        reader = csv.DictReader(f)
        required = {"student_name", "roll_number"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise SystemExit("CSV must include student_name and roll_number columns.")
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS students (
                id BIGSERIAL PRIMARY KEY, student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE, email TEXT, phone TEXT,
                course TEXT, branch TEXT, semester INTEGER, address TEXT)""")
            count = 0
            for row in reader:
                roll = (row.get("roll_number") or "").strip()
                name = (row.get("student_name") or "").strip()
                if not roll or not name:
                    continue
                sem = row.get("semester") or None
                cur.execute("""INSERT INTO students
                    (student_name, roll_number, email, phone, course, branch, semester, address)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (roll_number) DO NOTHING""",
                    (name, roll, row.get("email") or None, row.get("phone") or None,
                     row.get("course") or None, row.get("branch") or None, sem, row.get("address") or None))
                count += cur.rowcount
        conn.commit()
    print(f"Imported {count} new student row(s). Existing roll numbers were left unchanged.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python migrate_students_csv.py students.csv")
    main(sys.argv[1])
