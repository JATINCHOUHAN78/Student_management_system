import sqlite3
import hashlib
import os
from pathlib import Path
import streamlit as st
import pandas as pd

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "students.db"

st.set_page_config(page_title="Student Information System", page_icon="🎓", layout="wide")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                email TEXT,
                phone TEXT,
                course TEXT,
                branch TEXT,
                semester INTEGER,
                address TEXT
            )
        """)
        conn.commit()

def password_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def check_login(username, password):
    # Demo credentials. Change these in Streamlit Cloud Secrets for real use.
    expected_user = st.secrets.get("ADMIN_USERNAME", "admin")
    expected_hash = st.secrets.get(
        "ADMIN_PASSWORD_SHA256",
        password_hash("Admin@123")
    )
    return username == expected_user and password_hash(password) == expected_hash

def load_students():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return pd.DataFrame([dict(row) for row in rows])

def login_page():
    st.title("🎓 Student Information Management System")
    st.caption("Secure admin sign-in")
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
    page = st.sidebar.radio("Navigation", ["Dashboard", "Add Student", "View / Search", "Update Student", "Delete Student"])
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

    df = load_students()

    if page == "Dashboard":
        st.title("Dashboard")
        a, b, c = st.columns(3)
        a.metric("Total Students", len(df))
        b.metric("Courses", int(df["course"].nunique()) if not df.empty else 0)
        c.metric("Branches", int(df["branch"].nunique()) if not df.empty else 0)
        st.subheader("Recently Added Students")
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
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
                    with get_conn() as conn:
                        conn.execute("""INSERT INTO students
                            (student_name, roll_number, email, phone, course, branch, semester, address)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (name.strip(), roll.strip(), email.strip(), phone.strip(),
                             course.strip(), branch.strip(), int(semester), address.strip()))
                        conn.commit()
                    st.success("Student added successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("This Roll Number already exists. Please use a unique Roll Number.")
    elif page == "View / Search":
        st.title("View and Search Students")
        query = st.text_input("Search by name, roll number, course or branch")
        if not df.empty and query.strip():
            mask = df.astype(str).apply(lambda col: col.str.contains(query.strip(), case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "students.csv", "text/csv")
    elif page == "Update Student":
        st.title("Update Student Details")
        if df.empty:
            st.info("No student records available.")
        else:
            options = {f'{r["roll_number"]} — {r["student_name"]}': int(r["id"]) for _, r in df.iterrows()}
            selected = st.selectbox("Select student", list(options.keys()))
            student_id = options[selected]
            row = df[df["id"] == student_id].iloc[0]
            with st.form("update_student"):
                c1, c2 = st.columns(2)
                name = c1.text_input("Student Name *", str(row["student_name"]))
                roll = c2.text_input("Roll Number *", str(row["roll_number"]))
                email = c1.text_input("Email", str(row["email"] or ""))
                phone = c2.text_input("Phone", str(row["phone"] or ""))
                course = c1.text_input("Course", str(row["course"] or ""))
                branch = c2.text_input("Branch", str(row["branch"] or ""))
                sem_val = int(row["semester"]) if pd.notna(row["semester"]) else 1
                semester = st.number_input("Semester", min_value=1, max_value=12, value=max(1, min(12, sem_val)))
                address = st.text_area("Address", str(row["address"] or ""))
                submitted = st.form_submit_button("Update Student", use_container_width=True)
            if submitted:
                if not name.strip() or not roll.strip():
                    st.error("Student Name and Roll Number are required.")
                else:
                    try:
                        with get_conn() as conn:
                            conn.execute("""UPDATE students SET student_name=?, roll_number=?, email=?,
                                phone=?, course=?, branch=?, semester=?, address=? WHERE id=?""",
                                (name.strip(), roll.strip(), email.strip(), phone.strip(), course.strip(),
                                 branch.strip(), int(semester), address.strip(), student_id))
                            conn.commit()
                        st.success("Student updated successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That Roll Number is already assigned to another student.")
    elif page == "Delete Student":
        st.title("Delete Student")
        if df.empty:
            st.info("No student records available.")
        else:
            options = {f'{r["roll_number"]} — {r["student_name"]}': int(r["id"]) for _, r in df.iterrows()}
            selected = st.selectbox("Select student to delete", list(options.keys()))
            confirm = st.checkbox("I confirm that I want to permanently delete this record.")
            if st.button("Delete Student", type="primary", disabled=not confirm):
                with get_conn() as conn:
                    conn.execute("DELETE FROM students WHERE id=?", (options[selected],))
                    conn.commit()
                st.success("Student deleted.")
                st.rerun()

init_db()
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    main_app()
else:
    login_page()
