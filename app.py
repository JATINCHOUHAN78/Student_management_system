import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

APP_DIR = Path(__file__).parent
LEGACY_SQLITE = APP_DIR / "students.db"

st.set_page_config(page_title="Student Information System", page_icon="🎓", layout="wide")


def get_conn():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured. Add the Internal Database URL from Render PostgreSQL in Render → Web Service → Environment.")
    # Render's internal URL is preferred. External URLs require TLS.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "sslmode=" not in url and ".render.com" in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=10)


@contextmanager
def db_conn():
    """Commit/rollback a transaction and always close the PostgreSQL connection."""
    conn = get_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def migrate_legacy_sqlite(conn):
    """One-time, idempotent import of student rows if the old SQLite file is present."""
    if not LEGACY_SQLITE.exists():
        return 0
    try:
        old = sqlite3.connect(str(LEGACY_SQLITE))
        old.row_factory = sqlite3.Row
        names = {r["name"] for r in old.execute("PRAGMA table_info(students)").fetchall()}
        if not names:
            old.close()
            return 0
        rows = old.execute("SELECT * FROM students").fetchall()
        old.close()
        if not rows:
            return 0
        imported = 0
        with conn.cursor() as cur:
            for row in rows:
                data = dict(row)
                roll = str(data.get("roll_number") or "").strip()
                name = str(data.get("student_name") or "").strip()
                if not roll or not name:
                    continue
                cur.execute(
                    """INSERT INTO students
                    (student_name, roll_number, email, phone, course, branch, semester, address)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (roll_number) DO NOTHING""",
                    (name, roll, data.get("email"), data.get("phone"), data.get("course"),
                     data.get("branch"), data.get("semester"), data.get("address")),
                )
                imported += cur.rowcount
        conn.commit()
        return imported
    except Exception:
        conn.rollback()
        raise


def init_db():
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id BIGSERIAL PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    roll_number TEXT NOT NULL UNIQUE,
                    email TEXT, phone TEXT, course TEXT, branch TEXT,
                    semester INTEGER, address TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    id BIGSERIAL PRIMARY KEY,
                    teacher_name TEXT NOT NULL,
                    employee_id TEXT NOT NULL UNIQUE,
                    email TEXT, phone TEXT, department TEXT, subject TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id BIGSERIAL PRIMARY KEY,
                    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
                    attendance_date DATE NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('Present','Absent','Late')),
                    UNIQUE(student_id, attendance_date, subject)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
        conn.commit()
        imported = migrate_legacy_sqlite(conn)
    return imported


def password_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def admin_credentials():
    try:
        username = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME", "admin"))
        digest = st.secrets.get("ADMIN_PASSWORD_SHA256", os.getenv("ADMIN_PASSWORD_SHA256", password_hash("Admin@123")))
    except Exception:
        username = os.getenv("ADMIN_USERNAME", "admin")
        digest = os.getenv("ADMIN_PASSWORD_SHA256", password_hash("Admin@123"))
    return username, digest


def check_login(username, password):
    expected_user, expected_hash = admin_credentials()
    return username == expected_user and password_hash(password) == expected_hash


def query_df(sql, params=()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def execute(sql, params=()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def load_students():
    return query_df("SELECT * FROM students ORDER BY id DESC")


def load_teachers():
    return query_df("SELECT * FROM teachers ORDER BY teacher_name")


def student_options(df):
    return {f'{r["roll_number"]} — {r["student_name"]}': int(r["id"]) for _, r in df.iterrows()}


def teacher_options(df):
    return {f'{r["employee_id"]} — {r["teacher_name"]}': int(r["id"]) for _, r in df.iterrows()}


def login_page():
    st.title("🎓 Student Information Management System")
    st.caption("Admin sign-in")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
    if submitted:
        if check_login(username.strip(), password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")


def main_app():
    st.sidebar.title("🎓 Student Management")
    page = st.sidebar.radio("Navigation", [
        "Dashboard", "Add Student", "View / Search", "Update Student", "Delete Student",
        "Teacher Management", "Mark Attendance", "Attendance Reports"
    ])
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

    students = load_students()
    teachers = load_teachers()

    if page == "Dashboard":
        st.title("Dashboard")
        total_att = int(query_df("SELECT COUNT(*) AS n FROM attendance").iloc[0]["n"])
        a, b, c, d = st.columns(4)
        a.metric("Total Students", len(students))
        b.metric("Total Teachers", len(teachers))
        c.metric("Attendance Entries", total_att)
        d.metric("Courses", int(students["course"].nunique()) if not students.empty else 0)
        st.subheader("Recently Added Students")
        st.dataframe(students.head(10), use_container_width=True, hide_index=True)

    elif page == "Add Student":
        st.title("Add New Student")
        with st.form("add_student", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Student Name *")
            roll = c2.text_input("Roll Number *")
            email = c1.text_input("Email")
            phone = c2.text_input("Phone")
            course = c1.text_input("Course")
            branch = c2.text_input("Branch")
            semester = st.number_input("Semester", min_value=1, max_value=12, value=1)
            address = st.text_area("Address")
            submitted = st.form_submit_button("Save Student", use_container_width=True)
        if submitted:
            if not name.strip() or not roll.strip():
                st.error("Student Name and Roll Number are required.")
            else:
                try:
                    execute("""INSERT INTO students
                        (student_name, roll_number, email, phone, course, branch, semester, address)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (name.strip(), roll.strip(), email.strip(), phone.strip(), course.strip(),
                         branch.strip(), int(semester), address.strip()))
                    st.success("Student added successfully.")
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error("This Roll Number already exists.")

    elif page == "View / Search":
        st.title("View and Search Students")
        query = st.text_input("Search by name, roll number, course or branch")
        view = students.copy()
        if not view.empty and query.strip():
            mask = view.astype(str).apply(lambda col: col.str.contains(query.strip(), case=False, na=False)).any(axis=1)
            view = view[mask]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", view.to_csv(index=False).encode("utf-8"), "students.csv", "text/csv")

    elif page == "Update Student":
        st.title("Update Student Details")
        if students.empty:
            st.info("No student records available.")
        else:
            options = student_options(students)
            selected = st.selectbox("Select student", list(options))
            sid = options[selected]
            row = students[students["id"] == sid].iloc[0]
            with st.form("update_student"):
                c1, c2 = st.columns(2)
                name = c1.text_input("Student Name *", str(row["student_name"]))
                roll = c2.text_input("Roll Number *", str(row["roll_number"]))
                email = c1.text_input("Email", str(row["email"] or ""))
                phone = c2.text_input("Phone", str(row["phone"] or ""))
                course = c1.text_input("Course", str(row["course"] or ""))
                branch = c2.text_input("Branch", str(row["branch"] or ""))
                sem = int(row["semester"]) if pd.notna(row["semester"]) else 1
                semester = st.number_input("Semester", 1, 12, max(1, min(12, sem)))
                address = st.text_area("Address", str(row["address"] or ""))
                submitted = st.form_submit_button("Update Student", use_container_width=True)
            if submitted:
                if not name.strip() or not roll.strip():
                    st.error("Student Name and Roll Number are required.")
                else:
                    try:
                        execute("""UPDATE students SET student_name=%s, roll_number=%s, email=%s,
                            phone=%s, course=%s, branch=%s, semester=%s, address=%s WHERE id=%s""",
                            (name.strip(), roll.strip(), email.strip(), phone.strip(), course.strip(),
                             branch.strip(), int(semester), address.strip(), sid))
                        st.success("Student updated successfully.")
                        st.rerun()
                    except psycopg2.errors.UniqueViolation:
                        st.error("That Roll Number is already assigned to another student.")

    elif page == "Delete Student":
        st.title("Delete Student")
        if students.empty:
            st.info("No student records available.")
        else:
            options = student_options(students)
            selected = st.selectbox("Select student to delete", list(options))
            confirm = st.checkbox("I confirm permanent deletion of this record.")
            if st.button("Delete Student", type="primary", disabled=not confirm):
                execute("DELETE FROM students WHERE id=%s", (options[selected],))
                st.success("Student deleted. Linked attendance records were also deleted.")
                st.rerun()

    elif page == "Teacher Management":
        st.title("Teacher Management")
        with st.form("add_teacher", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Teacher Name *")
            employee_id = c2.text_input("Employee ID *")
            email = c1.text_input("Email")
            phone = c2.text_input("Phone")
            department = c1.text_input("Department")
            subject = c2.text_input("Subject")
            save = st.form_submit_button("Add Teacher", use_container_width=True)
        if save:
            if not name.strip() or not employee_id.strip():
                st.error("Teacher Name and Employee ID are required.")
            else:
                try:
                    execute("""INSERT INTO teachers
                        (teacher_name, employee_id, email, phone, department, subject)
                        VALUES (%s,%s,%s,%s,%s,%s)""",
                        (name.strip(), employee_id.strip(), email.strip(), phone.strip(),
                         department.strip(), subject.strip()))
                    st.success("Teacher added.")
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error("Employee ID already exists.")
        st.subheader("Teacher Directory")
        st.dataframe(teachers, use_container_width=True, hide_index=True)
        if not teachers.empty:
            with st.expander("Remove a teacher"):
                opts = teacher_options(teachers)
                selected = st.selectbox("Select teacher", list(opts), key="remove_teacher")
                if st.button("Delete Teacher"):
                    try:
                        execute("DELETE FROM teachers WHERE id=%s", (opts[selected],))
                        st.success("Teacher deleted.")
                        st.rerun()
                    except psycopg2.errors.ForeignKeyViolation:
                        st.error("This teacher has attendance records. Reassign or retain the teacher record.")

    elif page == "Mark Attendance":
        st.title("Mark Student Attendance")
        if students.empty:
            st.warning("Add students before marking attendance.")
        elif teachers.empty:
            st.warning("Add at least one teacher first.")
        else:
            with st.form("attendance_form"):
                c1, c2, c3 = st.columns(3)
                att_date = c1.date_input("Attendance Date", value=date.today())
                t_opts = teacher_options(teachers)
                teacher_label = c2.selectbox("Teacher", list(t_opts))
                subject = c3.text_input("Subject *")
                statuses = {}
                st.caption("Select each student's status. Saving again for the same date and subject updates the previous entry.")
                for _, student in students.iterrows():
                    label = f'{student["roll_number"]} — {student["student_name"]}'
                    statuses[int(student["id"])] = st.selectbox(
                        label, ["Present", "Absent", "Late"], key=f'att_{student["id"]}'
                    )
                save = st.form_submit_button("Save Attendance", use_container_width=True)
            if save:
                if not subject.strip():
                    st.error("Subject is required.")
                else:
                    with get_conn() as conn:
                        with conn.cursor() as cur:
                            for sid, status in statuses.items():
                                cur.execute("""INSERT INTO attendance
                                    (student_id, teacher_id, attendance_date, subject, status)
                                    VALUES (%s,%s,%s,%s,%s)
                                    ON CONFLICT (student_id, attendance_date, subject)
                                    DO UPDATE SET teacher_id=EXCLUDED.teacher_id, status=EXCLUDED.status""",
                                    (sid, t_opts[teacher_label], att_date, subject.strip(), status))
                        conn.commit()
                    st.success(f"Attendance saved for {len(statuses)} students.")
                    st.rerun()

    elif page == "Attendance Reports":
        st.title("Attendance Reports")
        c1, c2 = st.columns(2)
        start = c1.date_input("From date", value=date(date.today().year, date.today().month, 1), key="from_date")
        end = c2.date_input("To date", value=date.today(), key="to_date")
        if start > end:
            st.error("Start date cannot be after end date.")
        else:
            report = query_df("""SELECT s.roll_number, s.student_name, a.attendance_date,
                a.subject, t.teacher_name, a.status
                FROM attendance a JOIN students s ON s.id=a.student_id
                JOIN teachers t ON t.id=a.teacher_id
                WHERE a.attendance_date BETWEEN %s AND %s
                ORDER BY a.attendance_date DESC, s.roll_number""", (start, end))
            if report.empty:
                st.info("No attendance records found for this date range.")
            else:
                totals = report["status"].value_counts()
                a, b, c = st.columns(3)
                a.metric("Present", int(totals.get("Present", 0)))
                b.metric("Absent", int(totals.get("Absent", 0)))
                c.metric("Late", int(totals.get("Late", 0)))
                st.dataframe(report, use_container_width=True, hide_index=True)
                st.download_button("Download Attendance CSV", report.to_csv(index=False).encode("utf-8"),
                                   "attendance_report.csv", "text/csv")
                report["attended"] = report["status"].isin(["Present", "Late"]).astype(int)
                pct = report.groupby(["roll_number", "student_name"]).agg(
                    classes=("status", "count"), attended=("attended", "sum")).reset_index()
                pct["attendance_percentage"] = (pct["attended"] / pct["classes"] * 100).round(2)
                st.subheader("Student-wise Attendance Percentage")
                st.dataframe(pct, use_container_width=True, hide_index=True)


try:
    imported_count = init_db()
except Exception as exc:
    st.error("Database setup failed. Check DATABASE_URL in your hosting environment.")
    st.exception(exc)
    st.stop()

if imported_count:
    st.sidebar.success(f"Imported {imported_count} existing student record(s) from legacy SQLite database.")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    main_app()
else:
    login_page()
