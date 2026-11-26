# Student Information Management System

Streamlit app with PostgreSQL storage.

## Features
- Admin login
- Existing student CRUD: add, view, search, update, delete and CSV export
- Teacher directory: add, view and delete teachers (teachers linked to attendance cannot be deleted)
- Attendance entry by date, subject and teacher: Present / Absent / Late
- Re-entry for the same student/date/subject updates the existing record
- Date-range reports, student-wise attendance percentage and CSV export
- PostgreSQL foreign keys and indexes

## Run locally
Python 3.11 is recommended.

```bash
pip install -r requirements.txt
# Set DATABASE_URL to your PostgreSQL connection string
streamlit run app.py
```

## Deploy on Render with PostgreSQL
1. In Render Dashboard choose **New → PostgreSQL**. Create the database in the same region as the web service.
2. Open the database's **Connect** tab and copy its **Internal Database URL**.
3. Open the existing web service → **Environment**. Add `DATABASE_URL` with that Internal Database URL.
4. Add `ADMIN_USERNAME` (for example, `admin`) and `ADMIN_PASSWORD_SHA256` (SHA-256 digest of your chosen password). Do not store the raw password in GitHub.
5. Push/merge this branch to the branch configured for your Render service, or change the service's branch to this feature branch and deploy.
6. Confirm the deploy logs show the app started and then sign in.

Generate a password hash locally:
```bash
python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('New password: ').encode()).hexdigest())"
```

Use the database's **Internal Database URL** for a Render-hosted service in the same region. Use the external URL only for local tools, with TLS enabled. Never commit connection strings or secrets.

## Existing student data migration
The app automatically imports student rows from a legacy `students.db` SQLite file if that file is present beside `app.py` at startup. Import is idempotent by unique `roll_number`; existing PostgreSQL rows are not overwritten.

Important: Render's ordinary service filesystem is ephemeral. A deploy may not retain the old SQLite file. If the old records exist only in the previous Render instance, export the Students table to CSV before switching deployments, then import those rows into PostgreSQL. Do not assume a GitHub copy of the code contains the live SQLite data. Take a backup before changing the live service.

## Database schema
The app creates `students`, `teachers`, and `attendance` tables on startup. Existing student columns are retained. Deleting a student also deletes their attendance rows; a teacher with linked attendance cannot be deleted.

## Security and production notes
This is an educational starter app. For real student data, use a strong unique admin password, role-based authentication, backups, audit logs, HTTPS, and a managed database plan with suitable retention and backups. SHA-256 here preserves the existing demo login approach; use a modern password-hashing scheme before production use.
