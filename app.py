"""
Lightweight MySQL web console.

Originally built for a coursework database, now simplified to connect to any
schema through a Flask backend and single-page JavaScript UI.
"""

from __future__ import annotations

import configparser
import socket
import threading
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter, sleep
from typing import Dict, List, Tuple

import mysql.connector
from flask import Flask, jsonify, render_template_string, request
from mysql.connector import Error

APP_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = APP_ROOT / "db_config.ini"


def default_settings() -> Dict[str, str]:
    return {
        "host": "localhost",
        "port": "3306",
        "user": "root",
        "password": "",
        "database": "",
        "auto_connect": "False",
    }


def open_browser_when_ready(
    url: str, host: str, port: int, retries: int = 20, delay: float = 0.5
) -> None:
    """Spawn a daemon thread that opens the UI when the server accepts connections."""

    def _worker() -> None:
        for _ in range(retries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(delay)
                try:
                    sock.connect((host, port))
                except OSError:
                    sleep(delay)
                    continue
                webbrowser.open(url)
                return
        webbrowser.open(url)

    threading.Thread(target=_worker, daemon=True).start()


@dataclass
class DatabaseManager:
    """Handle the lifecycle of the MySQL connection."""

    config_path: Path
    connection: mysql.connector.MySQLConnection | None = None
    cursor: mysql.connector.cursor.MySQLCursor | None = None
    settings: Dict[str, str] = field(default_factory=default_settings)

    def __post_init__(self) -> None:
        self.load_settings()
        if (
            self.settings.get("auto_connect", "False") == "True"
            and self.settings.get("password")
            and self.settings.get("database")
        ):
            try:
                self.connect(**self.settings)
            except Error:
                self.close()

    def load_settings(self) -> Dict[str, str]:
        config = configparser.ConfigParser()
        if self.config_path.exists():
            config.read(self.config_path, encoding="utf-8")
            if config.has_section("mysql"):
                mysql_cfg = config["mysql"]
                for key, value in mysql_cfg.items():
                    self.settings[key] = value
        return self.settings

    def save_settings(self, new_settings: Dict[str, str]) -> None:
        to_store = new_settings.copy()
        config = configparser.ConfigParser()
        config["mysql"] = to_store
        with self.config_path.open("w", encoding="utf-8") as fh:
            config.write(fh)
        self.settings.update(to_store)

    def connect(self, **kwargs: str) -> Dict[str, str]:
        self.close()
        params = {
            "host": kwargs["host"],
            "port": int(kwargs["port"]),
            "user": kwargs["user"],
            "password": kwargs["password"],
            "database": kwargs["database"],
        }
        self.connection = mysql.connector.connect(**params)
        self.cursor = self.connection.cursor()
        self.save_settings(kwargs)
        return self.status()

    def close(self) -> None:
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None

    def ensure_cursor(self) -> None:
        if not self.connection or not self.connection.is_connected():
            raise RuntimeError("Connect to the database first.")

    def status(self) -> Dict[str, str | bool]:
        connected = bool(self.connection and self.connection.is_connected())
        return {
            "connected": connected,
            "database": self.settings.get("database", ""),
            "host": self.settings.get("host", ""),
            "auto_connect": self.settings.get("auto_connect", "False") == "True",
        }

    def execute_query(self, sql: str) -> Tuple[List[str], List[Tuple], float, int]:
        self.ensure_cursor()
        start = perf_counter()
        self.cursor.execute(sql)
        duration = perf_counter() - start
        if self.cursor.with_rows:
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            row_count = len(rows)
        else:
            # Commit non-select statements and report the affected row count.
            self.connection.commit()
            rows = []
            columns = []
            row_count = self.cursor.rowcount if self.cursor.rowcount != -1 else 0
        return columns, rows, duration, row_count

    def list_tables(self) -> List[str]:
        self.ensure_cursor()
        self.cursor.execute("SHOW TABLES")
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_table(self, table_name: str) -> Tuple[List[str], List[Tuple], float, int]:
        self.ensure_cursor()
        safe_name = table_name.replace("`", "``")
        query = f"SELECT * FROM `{safe_name}`"
        return self.execute_query(query)


app = Flask(__name__)
db_manager = DatabaseManager(CONFIG_FILE)


@app.get("/")
def index() -> str:
    return render_template_string(UI_TEMPLATE)


@app.get("/api/config")
def get_config():
    return jsonify(db_manager.settings)


@app.get("/api/status")
def get_status():
    return jsonify(db_manager.status())


@app.post("/api/connect")
def connect():
    data = request.get_json(force=True)
    try:
        settings = {
            "host": data.get("host", "localhost"),
            "port": str(data.get("port", "3306")),
            "user": data.get("user", "root"),
            "password": data.get("password", ""),
            "database": data.get("database", ""),
            "auto_connect": "True" if data.get("auto_connect") else "False",
        }
        if not settings["database"]:
            raise RuntimeError("Database name is required.")
        status = db_manager.connect(**settings)
        return jsonify({"success": True, "status": status})
    except (RuntimeError, Error) as exc:
        db_manager.close()
        return jsonify({"success": False, "message": str(exc)}), 400


@app.post("/api/disconnect")
def disconnect():
    db_manager.close()
    return jsonify({"success": True, "status": db_manager.status()})


@app.post("/api/execute")
def execute_sql():
    data = request.get_json(force=True)
    sql = data.get("sql", "").strip()
    if not sql:
        return jsonify({"success": False, "message": "Please enter an SQL statement."}), 400
    try:
        columns, rows, duration, row_count = db_manager.execute_query(sql)
        return jsonify(
            {
                "success": True,
                "columns": columns,
                "rows": rows,
                "rowCount": row_count,
                "duration": duration,
            }
        )
    except (RuntimeError, Error) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/tables")
def list_tables():
    try:
        tables = db_manager.list_tables()
        return jsonify({"tables": tables})
    except (RuntimeError, Error) as exc:
        return jsonify({"message": str(exc)}), 400


@app.get("/api/tables/<string:table_name>")
def get_table(table_name: str):
    try:
        columns, rows, duration, row_count = db_manager.fetch_table(table_name)
        return jsonify(
            {
                "columns": columns,
                "rows": rows,
                "rowCount": row_count,
                "duration": duration,
            }
        )
    except (RuntimeError, Error) as exc:
        return jsonify({"message": str(exc)}), 400


def main():
    host = "127.0.0.1"
    port = 5000
    open_browser_when_ready(f"http://{host}:{port}", host, port)
    app.run(host=host, port=port, debug=False)


UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Database Console</title>
    <style>
        :root {
            --bg-dark: #080b17;
            --bg-card: #121830;
            --bg-card-alt: #1c2342;
            --text-main: #f2f4ff;
            --text-soft: #b6bdd8;
            --accent-blue: #3694ff;
            --accent-lime: #7cd992;
            --accent-orange: #ff9d5c;
            --accent-purple: #9c7bff;
            --border: rgba(255,255,255,0.08);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Inter", "Segoe UI", sans-serif;
            background: radial-gradient(circle at top, #1b265a, #05060f);
            color: var(--text-main);
            min-height: 100vh;
        }
        .app-shell {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 20px 60px;
        }
        header.hero {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 26px;
        }
        .hero h1 {
            margin: 0;
            font-size: 28px;
            background: linear-gradient(120deg, #91b4ff, #c1f0ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-chip {
            padding: 8px 16px;
            border-radius: 999px;
            border: 1px solid var(--border);
            font-size: 14px;
        }
        .status-chip[data-state="on"] {
            background: rgba(124, 217, 146, 0.15);
            color: var(--accent-lime);
        }
        .status-chip[data-state="off"] {
            background: rgba(255, 155, 92, 0.12);
            color: var(--accent-orange);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }
        section.panel {
            padding: 20px;
            border-radius: 18px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            box-shadow: 0 18px 40px rgba(0,0,0,0.4);
        }
        section.panel h2 {
            margin-top: 0;
            font-size: 20px;
            letter-spacing: 0.02em;
        }
        section.panel p {
            margin: 6px 0 18px;
            color: var(--text-soft);
            font-size: 14px;
        }
        .panel.accent-blue { border-top: 3px solid var(--accent-blue); }
        .panel.accent-lime { border-top: 3px solid var(--accent-lime); }
        .panel.accent-orange { border-top: 3px solid var(--accent-orange); }
        .panel.accent-purple { border-top: 3px solid var(--accent-purple); }
        form.grid-form {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px 18px;
        }
        label {
            font-size: 13px;
            color: var(--text-soft);
        }
        input, select, textarea {
            width: 100%;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--bg-card-alt);
            color: var(--text-main);
            padding: 10px 14px;
            font-size: 15px;
            transition: border 0.2s ease, background 0.2s ease;
        }
        textarea {
            min-height: 130px;
            resize: vertical;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: var(--accent-blue);
            background: rgba(8, 20, 45, 0.6);
        }
        .full-row { grid-column: 1 / -1; }
        .button-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 8px;
        }
        button {
            border: none;
            border-radius: 12px;
            padding: 10px 18px;
            font-size: 15px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.15s ease, opacity 0.15s ease;
        }
        button:active { transform: scale(0.98); }
        button.primary { background: var(--accent-blue); color: #041326; }
        button.secondary { background: rgba(255,255,255,0.08); color: var(--text-main); }
        .token {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--text-soft);
        }
        .table-wrapper {
            margin-top: 14px;
            border-radius: 14px;
            overflow: auto;
            border: 1px solid var(--border);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 420px;
        }
        th, td {
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding: 8px 12px;
            font-size: 14px;
            text-align: left;
        }
        th {
            background: rgba(255,255,255,0.04);
            font-weight: 600;
        }
        .meta {
            margin-top: 10px;
            font-size: 13px;
            color: var(--text-soft);
        }
        .notice {
            margin-top: 10px;
            padding: 10px 14px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            font-size: 13px;
            color: var(--text-soft);
        }
        .toast {
            position: fixed;
            right: 20px;
            bottom: 20px;
            padding: 14px 18px;
            border-radius: 12px;
            background: var(--bg-card-alt);
            border: 1px solid var(--border);
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.3s ease, transform 0.3s ease;
            pointer-events: none;
            font-size: 14px;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        .toast.success { color: var(--accent-lime); }
        .toast.error { color: var(--accent-orange); }
        @media (max-width: 860px) {
            form.grid-form { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="app-shell">
        <header class="hero">
            <div>
                <div class="token">SQL DATA CONSOLE</div>
                <h1>Connect · Explore · Query</h1>
                <p style="color:var(--text-soft);max-width:640px;">
                    Point this lightweight web UI at any MySQL database, browse its tables, and run ad-hoc SQL.
                </p>
            </div>
            <div class="status-chip" id="status-chip" data-state="off">Disconnected</div>
        </header>
        <div class="grid">
            <section class="panel accent-blue">
                <h2>Database Connection</h2>
                <p>Enter your MySQL settings once, save them, and optionally auto-connect.</p>
                <form id="connection-form" class="grid-form">
                    <label>
                        Host
                        <input id="host" required>
                    </label>
                    <label>
                        Port
                        <input id="port" required>
                    </label>
                    <label>
                        User
                        <input id="user" required>
                    </label>
                    <label>
                        Password
                        <input id="password" type="password">
                    </label>
                    <label class="full-row">
                        Database
                        <input id="database" required>
                    </label>
                    <label class="full-row" style="display:flex;align-items:center;gap:10px;">
                        <input type="checkbox" id="auto-connect" style="width:auto;">
                        Auto-connect on launch and remember password
                    </label>
                    <div class="button-row full-row">
                        <button class="primary" type="submit">Connect to Database</button>
                        <button class="secondary" type="button" id="disconnect-btn">Disconnect</button>
                    </div>
                </form>
                <div class="notice" id="connection-note">Fill in the details above and press "Connect to Database".</div>
            </section>

            <section class="panel accent-lime">
                <h2>Browse Tables</h2>
                <p>Quickly inspect any table already inside the connected database.</p>
                <label>
                    Table
                    <select id="table-select">
                        <option value="">Select a table...</option>
                    </select>
                </label>
                <div class="button-row" style="margin-top:16px;">
                    <button class="primary" type="button" id="load-table">Load Table Data</button>
                    <button class="secondary" type="button" id="refresh-tables">Refresh Tables</button>
                </div>
                <div class="table-wrapper" id="table-results"></div>
                <div class="meta" id="table-meta">Records: 0 · Duration: 0.000s</div>
            </section>

            <section class="panel accent-purple">
                <h2>Custom SQL</h2>
                <p>Perfect for ad-hoc analysis or debugging.</p>
                <label>
                    SQL / Custom Query
                    <textarea id="custom-sql" spellcheck="false"></textarea>
                </label>
                <div class="button-row">
                    <button class="primary" type="button" id="run-custom">Run Custom Query</button>
                    <button class="secondary" type="button" id="clear-custom">Clear</button>
                </div>
                <div class="table-wrapper" id="custom-results"></div>
                <div class="meta" id="custom-meta">Rows: 0 · Duration: 0.000s</div>
            </section>
        </div>
    </div>
    <div class="toast" id="toast"></div>
    <script>
        const toast = document.getElementById('toast');
        const statusChip = document.getElementById('status-chip');
        const connectionNote = document.getElementById('connection-note');
        const tableSelect = document.getElementById('table-select');

        const showToast = (message, tone = 'success') => {
            toast.textContent = message;
            toast.className = `toast show ${tone}`;
            setTimeout(() => { toast.classList.remove('show'); }, 2600);
        };

        const updateStatusChip = (connected, text) => {
            statusChip.dataset.state = connected ? 'on' : 'off';
            statusChip.textContent = text;
        };

        const renderTable = (containerId, columns, rows) => {
            const wrapper = document.getElementById(containerId);
            wrapper.innerHTML = '';
            if (!rows || !rows.length) {
                wrapper.innerHTML = '<div class="notice">No records found.</div>';
                return;
            }
            const table = document.createElement('table');
            const thead = document.createElement('thead');
            const headRow = document.createElement('tr');
            columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                headRow.appendChild(th);
            });
            thead.appendChild(headRow);
            table.appendChild(thead);
            const tbody = document.createElement('tbody');
            rows.forEach(row => {
                const tr = document.createElement('tr');
                row.forEach(cell => {
                    const td = document.createElement('td');
                    td.textContent = cell === null ? 'NULL' : cell;
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            wrapper.appendChild(table);
        };

        const fetchConfig = async () => {
            const res = await fetch('/api/config');
            if (!res.ok) return;
            const cfg = await res.json();
            document.getElementById('host').value = cfg.host || 'localhost';
            document.getElementById('port').value = cfg.port || '3306';
            document.getElementById('user').value = cfg.user || 'root';
            document.getElementById('password').value = cfg.password || '';
            document.getElementById('database').value = cfg.database || '';
            document.getElementById('auto-connect').checked = cfg.auto_connect == 'True';
        };

        const refreshStatus = async () => {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();
            if (data.connected) {
                updateStatusChip(true, `Connected · ${data.database}`);
                connectionNote.textContent = `Connected to ${data.database} @ ${data.host}`;
            } else {
                updateStatusChip(false, 'Disconnected');
                connectionNote.textContent = 'Not connected yet. Provide the details to begin.';
            }
        };

        const refreshTables = async (silent = false) => {
            const res = await fetch('/api/tables');
            if (!res.ok) {
                if (!silent) {
                    const err = await res.json();
                    showToast(err.message || 'Unable to fetch tables', 'error');
                }
                return;
            }
            const data = await res.json();
            tableSelect.innerHTML = '<option value="">Select a table...</option>';
            data.tables.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                tableSelect.appendChild(option);
            });
        };

        const executeSQL = async (sql, containerId, metaId) => {
            const res = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql })
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.message || 'Query failed.');
            }
            renderTable(containerId, data.columns, data.rows);
            const meta = document.getElementById(metaId);
            meta.textContent = `Rows: ${data.rowCount} · Duration: ${data.duration.toFixed(3)}s`;
        };

        document.getElementById('connection-form').addEventListener('submit', async (evt) => {
            evt.preventDefault();
            const payload = {
                host: document.getElementById('host').value.trim(),
                port: document.getElementById('port').value.trim(),
                user: document.getElementById('user').value.trim(),
                password: document.getElementById('password').value,
                database: document.getElementById('database').value.trim(),
                auto_connect: document.getElementById('auto-connect').checked
            };
            const res = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                showToast(data.message || 'Connection failed.', 'error');
                await refreshStatus();
                return;
            }
            showToast('Database connected.');
            await refreshStatus();
            await refreshTables(true);
        });

        document.getElementById('disconnect-btn').addEventListener('click', async () => {
            await fetch('/api/disconnect', { method: 'POST' });
            showToast('Disconnected from database.', 'error');
            await refreshStatus();
        });

        document.getElementById('run-custom').addEventListener('click', async () => {
            const sql = document.getElementById('custom-sql').value.trim();
            if (!sql) { showToast('Please enter an SQL statement.', 'error'); return; }
            try {
                await executeSQL(sql, 'custom-results', 'custom-meta');
                showToast('Custom query completed.');
            } catch (err) {
                showToast(err.message, 'error');
            }
        });

        document.getElementById('clear-custom').addEventListener('click', () => {
            document.getElementById('custom-sql').value = '';
            document.getElementById('custom-results').innerHTML = '';
            document.getElementById('custom-meta').textContent = 'Rows: 0 · Duration: 0.000s';
        });

        document.getElementById('refresh-tables').addEventListener('click', () => refreshTables());

        document.getElementById('load-table').addEventListener('click', async () => {
            const tableName = tableSelect.value;
            if (!tableName) { showToast('Please select a table.', 'error'); return; }
            const res = await fetch(`/api/tables/${encodeURIComponent(tableName)}`);
            const data = await res.json();
            if (!res.ok) {
                showToast(data.message || 'Load failed.', 'error');
                return;
            }
            renderTable('table-results', data.columns, data.rows);
            document.getElementById('table-meta').textContent =
                `Records: ${data.rowCount} · Duration: ${data.duration.toFixed(3)}s`;
            showToast(`Loaded ${tableName}`);
        });

        window.addEventListener('load', async () => {
            await fetchConfig();
            await refreshStatus();
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
