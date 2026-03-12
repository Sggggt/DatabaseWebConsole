## NHS Database Web App - Task 9

Interactive Flask dashboard for the NHS hospitals & waiting lists coursework.

### 1. Environment setup
- Install Python 3.10+ and ensure python / pip are available (optional venv: python -m venv .venv && .\.venv\Scripts\activate).
- Install dependencies: python install_package.py (add --upgrade if needed).

### 2. Initialize the database
1) Edit db_config.ini with MySQL host/port/user/database (database is locked to 
hs_database). password may be left empty.
2) Ensure the MySQL user can create DB, tables, and insert data.
3) Run python setup_nhs_database.py --reset (or use the batch script below).

Batch shortcut: 
un_app_full.bat runs in order:
1) check Python → 2) install dependencies → 3) setup_nhs_database.py --reset → 4) start the app.

### 3. Run the web app
`bash
python nhs_database_app.py
`
- Open http://127.0.0.1:5000 in your browser.
- In the “Connection” panel, enter MySQL connection info and click Connect (DB name is fixed to nhs_database).
- Browse table data and run the built-in queries.

### 4. Clean/reset
- Clear all tables: python clear_data.py
- Drop the entire 
hs_database: python clear_data.py --drop
- Both support --force to skip confirmation.

### 5. Directory guide
- 
hs_database_app.py: Flask app (includes front-end template)
- setup_nhs_database.py: Database setup/seed (uses Tables.sql, Data.sql)
- install_package.py: Install required Python packages
- Tables.sql, Data.sql: DDL, data seeds, sample queries
- db_config.ini: MySQL connection config
