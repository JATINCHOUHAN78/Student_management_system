# Student Information Management System

A Streamlit-based student record management application using SQLite.

## Features
- Admin login
- Dashboard with student/course/branch counts
- Add, view, search, update and delete student records
- Export student records to CSV
- Unique roll-number validation

## Run locally
1. Install Python 3.11 or newer.
2. Open a terminal in this project folder.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the local URL shown in the terminal (usually http://localhost:8501).

## Demo login
- Username: `admin`
- Password: `Admin@123`

Change the demo credentials before using this app with real student data.

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository and upload all project files (including the `.streamlit` folder).
2. Open https://share.streamlit.io/ and sign in with GitHub.
3. Select **Create app**, choose your repository, branch, and `app.py`.
4. Click **Deploy**.

### Optional: set a custom admin password
In your Streamlit app dashboard, open **App settings → Secrets** and add:

```toml
ADMIN_USERNAME = "your_admin_username"
ADMIN_PASSWORD_SHA256 = "paste_sha256_hash_here"
```

Generate the SHA-256 hash locally:

```bash
python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('New password: ').encode()).hexdigest())"
```

Do not commit secrets or real student data to GitHub.

## Database persistence warning
This starter project uses a local SQLite database file (`students.db`). It is suitable for local testing and a basic demonstration. Streamlit Community Cloud's local filesystem is not a reliable permanent database: records may be lost when the app is restarted or redeployed. For a real college deployment, connect a hosted database such as Supabase PostgreSQL and keep credentials in Streamlit Secrets.

## Security and privacy
This is an educational starter project, not a production-ready student information system. Before storing real student data, add role-based access, stronger authentication, HTTPS-only access, audit logs, backups, input validation, and a privacy policy.
