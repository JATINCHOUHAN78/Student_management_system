# Student Information Management System

A Streamlit student-record management app backed by SQLite.

## Features
- Admin login
- Dashboard with student, course and branch counts
- Add, view, search, update and delete student records
- CSV export
- Unique roll-number validation

## Run locally
Use Python 3.11.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

## Demo login
- Username: `admin`
- Password: `Admin@123`

These are demonstration credentials only. Do not use them for a real deployment.

## Deploy on Streamlit Community Cloud
1. Push this repository to GitHub.
2. Visit https://share.streamlit.io/ and sign in with GitHub.
3. Select **Create app**.
4. Select this repository, the deployment branch, and `app.py` as the main file.
5. Select **Deploy**.

### Configure an admin password
In Streamlit Community Cloud, open the app's **Settings → Secrets** and set:

```toml
ADMIN_USERNAME = "your_admin_username"
ADMIN_PASSWORD_SHA256 = "your_sha256_password_hash"
```

Generate a SHA-256 hash locally (the command prompts without displaying your password):

```bash
python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('New password: ').encode()).hexdigest())"
```

Never commit passwords, API keys, or other secrets to GitHub.

## Important database limitation
This app stores records in a local SQLite file named `students.db`. Streamlit Community Cloud's local filesystem is not a durable database; data can be lost when the app is restarted, rebuilt, or redeployed. This version is suitable for a demonstration, not as the permanent system of record for a college. For real student data, migrate to a managed database such as PostgreSQL (for example, Supabase) and keep connection credentials in Streamlit Secrets.

## Security and privacy
This is an educational starter project, not a production-ready student information system. Before storing real student information, implement robust authentication and authorization, secure password hashing, database backups, audit logging, input validation, and an appropriate privacy policy.
