"""
NHS Waiting Lists portal (Task 9)
User-facing web app (no raw SQL console): connection controls, healthcare lookup,
patient lookup, and per-table browsing with guided filters.
"""

from __future__ import annotations

import configparser
import socket
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter, sleep
from typing import Dict, List, Sequence, Tuple

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
        "database": "nhs_database",
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
        # Ensure date/time names are returned in English (month/day names)
        try:
            self.cursor.execute("SET lc_time_names = 'en_US'")
        except Error:
            pass
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

    def execute_query(
        self, sql: str, params: Sequence | None = None
    ) -> Tuple[List[str], List[Tuple], float]:
        self.ensure_cursor()
        start = perf_counter()
        self.cursor.execute(sql, params or ())
        rows = self.cursor.fetchall()
        duration = perf_counter() - start
        columns = [desc[0] for desc in self.cursor.description]
        return columns, rows, duration

    def database_exists(self, settings: Dict[str, str]) -> bool:
        server_cfg = {
            "host": settings["host"],
            "port": int(settings["port"]),
            "user": settings["user"],
            "password": settings["password"],
        }
        database = settings["database"]
        conn: mysql.connector.MySQLConnection | None = None
        cursor: mysql.connector.cursor.MySQLCursor | None = None
        try:
            conn = mysql.connector.connect(**server_cfg)
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES LIKE %s", (database,))
            return cursor.fetchone() is not None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


TABLE_CONFIG: Dict[str, Dict] = {
    "country": {
        "label": "Country",
        "table": "Country",
        "columns": ["CountryID", "CountryName"],
        "search_cols": ["CountryName"],
        "order_by": "CountryID",
        "id_col": "CountryID",
    },
    "county": {
        "label": "County",
        "table": "County",
        "columns": ["CountyID", "CountyName", "CountryID"],
        "search_cols": ["CountyName"],
        "order_by": "CountyID",
        "id_col": "CountyID",
    },
    "district": {
        "label": "District",
        "table": "District",
        "columns": ["DistrictID", "DistrictName", "CountyID"],
        "search_cols": ["DistrictName"],
        "order_by": "DistrictID",
        "id_col": "DistrictID",
    },
    "healthcareorganisation": {
        "label": "Healthcare Organisation",
        "table": "HealthcareOrganisation",
        "columns": [
            "OrgID",
            "OrgName",
            "OrgType",
            "AddressLine",
            "City",
            "Postcode",
            "DistrictID",
        ],
        "search_cols": ["OrgName", "OrgType", "City", "Postcode"],
        "order_by": "OrgID",
        "id_col": "OrgID",
    },
    "hospital": {
        "label": "Hospital",
        "table": "Hospital",
        "columns": ["OrgID", "BedCapacity", "HasEmergency"],
        "search_cols": [],
        "order_by": "OrgID",
        "id_col": "OrgID",
    },
    "gppractice": {
        "label": "GP Practice",
        "table": "GPPractice",
        "columns": ["OrgID", "NumGPs", "OpeningHours"],
        "search_cols": ["OpeningHours"],
        "order_by": "OrgID",
        "id_col": "OrgID",
    },
    "socioeconomicgroup": {
        "label": "Socioeconomic Group",
        "table": "SocioeconomicGroup",
        "columns": ["SEGCode", "SEGName", "Description"],
        "search_cols": ["SEGName", "Description"],
        "order_by": "SEGCode",
        "id_col": "SEGCode",
    },
    "patient": {
        "label": "Patient",
        "table": "Patient",
        "columns": [
            "PatientID",
            "NHSNumber",
            "FirstName",
            "LastName",
            "DOB",
            "Gender",
            "Street",
            "City",
            "Postcode",
            "DistrictID",
            "SEGCode",
        ],
        "search_cols": ["FirstName", "LastName", "NHSNumber", "City", "Postcode"],
        "order_by": "PatientID",
        "id_col": "PatientID",
    },
    "patientphone": {
        "label": "Patient Phone",
        "table": "PatientPhone",
        "columns": ["PatientID", "Phone"],
        "search_cols": ["Phone"],
        "order_by": "PatientID, Phone",
        "id_col": None,
    },
    "proceduretype": {
        "label": "Procedure Type",
        "table": "ProcedureType",
        "columns": ["ProcedureCode", "ProcedureName", "Category"],
        "search_cols": ["ProcedureCode", "ProcedureName", "Category"],
        "order_by": "ProcedureCode",
        "id_col": "ProcedureCode",
    },
    "encounter": {
        "label": "Encounter",
        "table": "Encounter",
        "columns": [
            "EncounterID",
            "PatientID",
            "OrgID",
            "EncounterDateTime",
            "EncounterType",
            "DistrictID",
            "ProcedureCode",
        ],
        "search_cols": ["EncounterType", "ProcedureCode"],
        "order_by": "EncounterDateTime DESC",
        "id_col": "EncounterID",
    },
    "waitinglistentry": {
        "label": "Waiting List Entry",
        "table": "WaitingListEntry",
        "columns": [
            "WaitingID",
            "PatientID",
            "OrgID",
            "ProcedureCode",
            "RequestDate",
            "Status",
            "Priority",
            "EstimatedWaitDays",
        ],
        "search_cols": ["ProcedureCode", "Status", "Priority"],
        "order_by": "RequestDate DESC",
        "id_col": "WaitingID",
    },
    "populationfact": {
        "label": "Population Fact",
        "table": "PopulationFact",
        "columns": [
            "PopID",
            "DistrictID",
            "RefDate",
            "AgeGroup",
            "SEGCode",
            "PopulationCount",
        ],
        "search_cols": ["AgeGroup", "SEGCode"],
        "order_by": "RefDate DESC",
        "id_col": "PopID",
    },
    "firstminister": {
        "label": "First Minister",
        "table": "FirstMinister",
        "columns": ["MinisterID", "CountryID", "MinisterName", "TermStart", "TermEnd"],
        "search_cols": ["MinisterName"],
        "order_by": "MinisterID",
        "id_col": "MinisterID",
    },
    "policystatement": {
        "label": "Policy Statement",
        "table": "PolicyStatement",
        "columns": ["StatementID", "MinisterID", "StatementDate", "Topic", "Content"],
        "search_cols": ["Topic", "Content"],
        "order_by": "StatementDate DESC",
        "id_col": "StatementID",
    },
}


def parse_limit(raw_value: str | None, default: int, max_allowed: int = 500) -> int:
    try:
        value = int(raw_value) if raw_value else default
    except ValueError:
        value = default
    value = max(1, value)
    return min(value, max_allowed)


def run_setup_script(settings: Dict[str, str]) -> str:
    script_path = APP_ROOT / "setup_nhs_database.py"
    if not script_path.exists():
        raise RuntimeError(f"Auto-import script missing: {script_path}")

    password = settings.get("password", "")
    args = [sys.executable, str(script_path), "--password", password]
    result = subprocess.run(
        args,
        cwd=str(APP_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Automatic database import failed (exit code {result.returncode}).\n{output}"
        )
    return (result.stdout + result.stderr).strip()


def ensure_database_ready(settings: Dict[str, str]) -> bool:
    if db_manager.database_exists(settings):
        return False
    db_manager.save_settings(settings)
    run_setup_script(settings)
    if not db_manager.database_exists(settings):
        raise RuntimeError(
            "Database still missing after running the setup script. Please verify your MySQL settings."
        )
    return True


def healthcare_search_query(args) -> Tuple[List[str], List[Tuple], float]:
    county = args.get("county", "").strip()
    district = args.get("district", "").strip()
    org_type = args.get("org_type", "").strip()
    emergency_only = args.get("emergency_only", "").lower() in {"1", "true", "yes"}
    limit = parse_limit(args.get("limit"), default=50, max_allowed=300)

    sql = [
        "SELECT o.OrgID, o.OrgName, o.OrgType,",
        "       d.DistrictName, c.CountyName,",
        "       h.BedCapacity, h.HasEmergency,",
        "       gp.NumGPs, gp.OpeningHours",
        "FROM HealthcareOrganisation o",
        "JOIN District d ON o.DistrictID = d.DistrictID",
        "JOIN County c ON d.CountyID = c.CountyID",
        "LEFT JOIN Hospital h ON o.OrgID = h.OrgID",
        "LEFT JOIN GPPractice gp ON o.OrgID = gp.OrgID",
        "WHERE 1=1",
    ]
    params: List = []

    if county:
        sql.append("AND c.CountyName LIKE %s")
        params.append(f"%{county}%")
    if district:
        sql.append("AND d.DistrictName LIKE %s")
        params.append(f"%{district}%")
    if org_type:
        sql.append("AND o.OrgType LIKE %s")
        params.append(f"%{org_type}%")
    if emergency_only:
        sql.append("AND h.HasEmergency = %s")
        params.append(True)

    sql.append("ORDER BY o.OrgName")
    sql.append("LIMIT %s")
    params.append(limit)

    return db_manager.execute_query("\n".join(sql), params)


def patient_search_query(args) -> Tuple[List[str], List[Tuple], float]:
    name = args.get("name", "").strip()
    nhs = args.get("nhs", "").strip()
    county = args.get("county", "").strip()
    district = args.get("district", "").strip()
    status_raw = args.get("status_list", "").strip()
    status_list = [s for s in status_raw.split(",") if s.strip()]
    enc_from = args.get("enc_from", "").strip()
    enc_to = args.get("enc_to", "").strip()
    order = args.get("order", "name").strip().lower()
    procedure = args.get("procedure", "").strip()
    limit = parse_limit(args.get("limit"), default=50, max_allowed=300)

    sql = [
        "SELECT p.PatientID, p.NHSNumber, p.FirstName, p.LastName,",
        "       p.Gender, p.DOB, p.City, p.Postcode,",
        "       d.DistrictName, c.CountyName,",
        "       w.Status, w.Priority, w.ProcedureCode, w.RequestDate, w.EstimatedWaitDays",
        "FROM Patient p",
        "JOIN District d ON p.DistrictID = d.DistrictID",
        "JOIN County c ON d.CountyID = c.CountyID",
        "LEFT JOIN WaitingListEntry w ON p.PatientID = w.PatientID",
        "WHERE 1=1",
    ]
    params: List = []

    if name:
        sql.append("AND (p.FirstName LIKE %s OR p.LastName LIKE %s)")
        params.extend([f"%{name}%", f"%{name}%"])
    if nhs:
        sql.append("AND p.NHSNumber LIKE %s")
        params.append(f"%{nhs}%")
    if county:
        sql.append("AND c.CountyName LIKE %s")
        params.append(f"%{county}%")
    if district:
        sql.append("AND d.DistrictName LIKE %s")
        params.append(f"%{district}%")
    if status_list:
        placeholders = ", ".join(["%s"] * len(status_list))
        sql.append(f"AND w.Status IN ({placeholders})")
        params.extend(status_list)
    if procedure:
        sql.append("AND w.ProcedureCode = %s")
        params.append(procedure)
    if enc_from or enc_to:
        enc_clauses: List[str] = []
        if enc_from:
            enc_clauses.append("EncounterDateTime >= %s")
            params.append(enc_from)
        if enc_to:
            enc_clauses.append("EncounterDateTime <= %s")
            params.append(enc_to)
        sql.append(
            "AND EXISTS (SELECT 1 FROM Encounter e1 "
            "WHERE e1.PatientID = p.PatientID AND "
            + (" AND ".join(enc_clauses)) +
            ")"
        )

    if order == "wait_desc":
        sql.append("ORDER BY w.EstimatedWaitDays DESC, p.LastName, p.FirstName")
    elif order == "req_desc":
        sql.append("ORDER BY w.RequestDate DESC, p.LastName, p.FirstName")
    else:
        sql.append("ORDER BY p.LastName, p.FirstName")
    sql.append("LIMIT %s")
    params.append(limit)

    return db_manager.execute_query("\n".join(sql), params)


def table_query(table_key: str, args) -> Tuple[List[str], List[Tuple], float]:
    cfg = TABLE_CONFIG[table_key]
    columns = cfg["columns"]
    search_cols = cfg.get("search_cols", [])
    id_col = cfg.get("id_col")
    search = args.get("search", "").strip()
    id_value = args.get("id")
    limit = parse_limit(args.get("limit"), default=100, max_allowed=400)

    sql_parts = [f"SELECT {', '.join(columns)} FROM {cfg['table']}"]
    where: List[str] = []
    params: List = []

    if id_col and id_value:
        where.append(f"{id_col} = %s")
        params.append(id_value)

    if search and search_cols:
        like_clause = " OR ".join([f"{col} LIKE %s" for col in search_cols])
        where.append(f"({like_clause})")
        params.extend([f"%{search}%"] * len(search_cols))

    if where:
        sql_parts.append("WHERE " + " AND ".join(where))

    order_by = cfg.get("order_by")
    if order_by:
        sql_parts.append(f"ORDER BY {order_by}")

    sql_parts.append("LIMIT %s")
    params.append(limit)

    return db_manager.execute_query("\n".join(sql_parts), params)


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
            "database": "nhs_database",  # locked to coursework database
            "auto_connect": "True" if data.get("auto_connect") else "False",
        }
        triggered_setup = ensure_database_ready(settings)
        status = db_manager.connect(**settings)
        return jsonify(
            {"success": True, "status": status, "setupTriggered": triggered_setup}
        )
    except (RuntimeError, Error) as exc:
        db_manager.close()
        return jsonify({"success": False, "message": str(exc)}), 400


@app.post("/api/disconnect")
def disconnect():
    db_manager.close()
    return jsonify({"success": True, "status": db_manager.status()})


@app.get("/api/healthcare-search")
def healthcare_search():
    try:
        columns, rows, duration = healthcare_search_query(request.args)
        return jsonify(
            {
                "success": True,
                "columns": columns,
                "rows": rows,
                "rowCount": len(rows),
                "duration": duration,
            }
        )
    except (RuntimeError, Error) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/patient-search")
def patient_search():
    try:
        columns, rows, duration = patient_search_query(request.args)
        return jsonify(
            {
                "success": True,
                "columns": columns,
                "rows": rows,
                "rowCount": len(rows),
                "duration": duration,
            }
        )
    except (RuntimeError, Error) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/tables")
def list_tables():
    items = [
        {"key": key, "label": cfg["label"], "table": cfg["table"]}
        for key, cfg in TABLE_CONFIG.items()
    ]
    return jsonify({"tables": items})


@app.get("/api/table/<string:table_key>")
def get_table(table_key: str):
    key = table_key.lower()
    if key not in TABLE_CONFIG:
        return jsonify({"success": False, "message": "Unknown table."}), 404
    try:
        columns, rows, duration = table_query(key, request.args)
        return jsonify(
            {
                "success": True,
                "columns": columns,
                "rows": rows,
                "rowCount": len(rows),
                "duration": duration,
            }
        )
    except (RuntimeError, Error) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


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
    <title>NHS Access Portal</title>
    <style>
        :root {
            --bg: #05060f;
            --panel: #0c1024;
            --panel-alt: #10152e;
            --text: #eaf0ff;
            --muted: #b7c1de;
            --accent: #6dd3ff;
            --accent-2: #7edfa2;
            --accent-3: #ffb37a;
            --border: rgba(255,255,255,0.08);
            --shadow: 0 20px 60px rgba(0,0,0,0.35);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Manrope", "Segoe UI", sans-serif;
            background: radial-gradient(circle at 20% 20%, #112058, var(--bg));
            color: var(--text);
            min-height: 100vh;
            padding: 32px 18px 48px;
        }
        h1, h2, h3 { margin: 0; font-weight: 700; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 18px;
        }
        .panel {
            background: linear-gradient(160deg, var(--panel), var(--panel-alt));
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: var(--shadow);
            min-width: 0; /* allow contents to shrink within grid */
            overflow: visible; /* keep inner scrollbars visible */
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 14px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            font-size: 13px;
            letter-spacing: 0.01em;
        }
        .chip[data-state="on"] { color: var(--accent-2); border-color: rgba(126,223,162,0.5); }
        .chip[data-state="off"] { color: #ff8b8b; border-color: rgba(255,139,139,0.4); }
        label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
        input, select {
            width: 100%;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: rgba(255,255,255,0.04);
            color: var(--text);
            font-size: 14px;
        }
        input:focus, select:focus { outline: 1px solid var(--accent); border-color: var(--accent); }
        .actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        button {
            border: none;
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 14px;
            cursor: pointer;
            font-weight: 600;
            color: #041226;
            transition: transform 0.08s ease, box-shadow 0.2s ease;
        }
        button.primary { background: linear-gradient(120deg, var(--accent), #82b1ff); box-shadow: 0 10px 30px rgba(61,166,255,0.35); }
        button.secondary { background: linear-gradient(120deg, var(--accent-2), #9df1b9); color: #032511; }
        button.ghost { background: transparent; color: var(--text); border: 1px solid var(--border); }
        button:active { transform: translateY(1px); }
        .stack { display: grid; gap: 12px; }
        .section-title { font-size: 18px; letter-spacing: 0.01em; }
        .muted { color: var(--muted); font-size: 14px; }
        .table-wrap {
            width: 100%;
            max-height: 360px;
            overflow-x: auto;
            overflow-y: auto;
            border: 1px solid var(--border);
            border-radius: 10px;
            max-width: 100%;
            display: block;
            padding-bottom: 6px; /* keep scrollbars visible inside */
            scrollbar-color: #8b8b8b #0c1024;
            scrollbar-width: thin;
            min-height: 120px;
            position: relative;
        }
        .result-box {
            width: 100%;
            max-height: 360px;
            overflow-x: auto;
            overflow-y: auto;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px;
            margin-top: 10px;
            background: rgba(255,255,255,0.03);
        }
        table { width: max-content; min-width: 1400px; border-collapse: collapse; }
        /* Custom horizontal scrollbar */
        .table-wrap::-webkit-scrollbar {
            height: 16px;
            background: #0c1024;
        }
        .table-wrap::-webkit-scrollbar-track {
            background: linear-gradient(90deg, #0c1024 0%, #0c1024 100%);
            border-radius: 999px;
            margin: 3px 10px;
        }
        .table-wrap::-webkit-scrollbar-thumb {
            background: #8b8b8b;
            border-radius: 999px;
            border: 4px solid #0c1024;
        }
        .table-wrap::-webkit-scrollbar-thumb:hover { background: #a0a0a0; }
        th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
        th { color: var(--accent); font-weight: 700; }
        tr:hover td { background: rgba(255,255,255,0.02); }
        .notice { color: var(--muted); padding: 12px 10px; }
        .meta { color: var(--muted); font-size: 12px; margin-top: 6px; }
        .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 12px;
            color: var(--muted);
        }
        .toast {
            position: fixed;
            bottom: 18px;
            right: 18px;
            background: #111b36;
            border: 1px solid var(--border);
            padding: 12px 14px;
            border-radius: 12px;
            box-shadow: var(--shadow);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.25s ease;
            pointer-events: none;
        }
        .toast.show { opacity: 1; transform: translateY(0); }
        @media (max-width: 640px) { body { padding: 20px 14px; } }
    </style>
</head>
<body>
    <header class="header" style="margin-bottom: 22px;">
        <div>
            <div class="pill">NHS Coursework · Task 9</div>
            <h1 style="margin-top: 8px;">NHS Access Portal</h1>
            <div class="muted">Search healthcare organisations, patients, and every table without writing SQL.</div>
        </div>
        <div class="chip" id="status-chip" data-state="off">Disconnected</div>
    </header>

    <div class="grid" style="margin-bottom: 18px;">
        <div class="panel stack">
            <div class="header">
                <div class="section-title">Connection</div>
                <div class="muted" id="connection-note">Provide connection details to start.</div>
            </div>
            <form id="connection-form" class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 12px;">
                <div><label>Host</label><input id="host" required value="localhost"></div>
                <div><label>Port</label><input id="port" required value="3306"></div>
                <div><label>User</label><input id="user" required value="root"></div>
                <div><label>Password</label><input id="password" type="password"></div>
                <div><label>Database</label><input id="database" value="nhs_database" readonly style="opacity:0.7; cursor:not-allowed;"></div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:12px;">
                    <input id="auto-connect" type="checkbox" style="width:auto;">
                    <label style="margin:0;">Remember & auto-connect</label>
                </div>
                <div class="actions" style="grid-column: 1 / -1;">
                    <button class="primary" type="submit" id="connect-btn">Connect</button>
                    <button class="ghost" type="button" id="disconnect-btn">Disconnect</button>
                </div>
            </form>
        </div>
    </div>

    <div class="grid" style="margin-bottom: 18px;">
        <div class="panel stack">
            <div class="header"><div class="section-title">Healthcare lookup</div><div class="muted">Filter by county, district, type, and emergency cover.</div></div>
            <form id="healthcare-form" class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 12px;">
                <div><label>County</label><input id="hc-county" placeholder="e.g. Greater London"></div>
                <div><label>District</label><input id="hc-district" placeholder="e.g. City of London"></div>
                <div><label>Organisation type</label><input id="hc-type" placeholder="Hospital / GP / Consultant"></div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:12px;">
                    <input id="hc-emergency" type="checkbox" style="width:auto;">
                    <label style="margin:0;">Emergency hospitals only</label>
                </div>
                <div><label>Limit</label><input id="hc-limit" type="number" min="1" max="300" value="50"></div>
                <div class="actions" style="grid-column:1/-1;">
                    <button class="primary" type="submit" id="hc-submit">Search organisations</button>
                </div>
            </form>
            <div class="result-box"><div id="healthcare-results"></div></div>
            <div class="meta" id="healthcare-meta"></div>
        </div>

        <div class="panel stack">
            <div class="header"><div class="section-title">Patient lookup</div><div class="muted">Find patients with optional waiting-list status.</div></div>
            <form id="patient-form" class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 12px;">
                <div><label>Name</label><input id="pt-name" placeholder="Partial first/last name"></div>
                <div><label>NHS number</label><input id="pt-nhs" placeholder="Exact or partial"></div>
                <div><label>County</label><input id="pt-county" placeholder="County name"></div>
                <div><label>District</label><input id="pt-district" placeholder="District name"></div>
                <div>
                    <label>Waiting status (multi)</label>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                        <label><input type="checkbox" class="pt-status-opt" value="WAITING"> WAITING</label>
                        <label><input type="checkbox" class="pt-status-opt" value="SCHEDULED"> SCHEDULED</label>
                        <label><input type="checkbox" class="pt-status-opt" value="COMPLETED"> COMPLETED</label>
                        <label><input type="checkbox" class="pt-status-opt" value="CANCELLED"> CANCELLED</label>
                    </div>
                </div>
                <div><label>Procedure code</label><input id="pt-procedure" placeholder="e.g. HIP"></div>
                <div><label>Encounter from</label><input id="pt-enc-from" type="date"></div>
                <div><label>Encounter to</label><input id="pt-enc-to" type="date"></div>
                <div><label>Limit</label><input id="pt-limit" type="number" min="1" max="300" value="50"></div>
                <div>
                    <label>Sort by</label>
                    <select id="pt-sort">
                        <option value="name">Last name A→Z</option>
                        <option value="wait_desc">Wait days (desc)</option>
                        <option value="req_desc">Request date (newest)</option>
                    </select>
                </div>
                <div class="actions" style="grid-column:1/-1;">
                    <button class="secondary" type="submit" id="pt-submit">Search patients</button>
                </div>
            </form>
            <div class="result-box">
                <div id="patient-results"></div>
            </div>
            <div class="meta" id="patient-meta"></div>
        </div>
    </div>

        <div class="panel stack">
            <div class="header"><div class="section-title">Data browser</div><div class="muted">Every table, searchable without SQL.</div></div>
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 12px;">
                <div>
                    <label>Table</label>
                <select id="table-select"></select>
            </div>
            <div>
                <label>Search text</label>
                <input id="table-search" placeholder="Matches name/code fields">
            </div>
            <div>
                <label>Limit</label>
                <input id="table-limit" type="number" min="1" max="400" value="100">
            </div>
            <div class="actions" style="grid-column:1/-1;">
                <button class="primary" type="button" id="load-table">Load table</button>
            </div>
        </div>
        <div class="result-box"><div id="table-results"></div></div>
        <div class="meta" id="table-meta"></div>
    </div>

    <div class="toast" id="toast" role="status" aria-live="polite"></div>

    <script>
        const toast = document.getElementById('toast');
        const statusChip = document.getElementById('status-chip');
        const connectionNote = document.getElementById('connection-note');
        const tableSelect = document.getElementById('table-select');
        const connectBtn = document.getElementById('connect-btn');
        const hcBtn = document.getElementById('hc-submit');
        const ptBtn = document.getElementById('pt-submit');
        const loadTableBtn = document.getElementById('load-table');

        const setLoading = (btn, loading, text) => {
            if (!btn) return;
            if (loading) {
                btn.dataset.prevLabel = btn.textContent;
                if (text) btn.textContent = text;
                btn.disabled = true;
            } else {
                btn.disabled = false;
                if (btn.dataset.prevLabel) {
                    btn.textContent = btn.dataset.prevLabel;
                    delete btn.dataset.prevLabel;
                }
            }
        };

        const showToast = (message, tone = 'info') => {
            toast.textContent = message;
            toast.style.borderColor = tone === 'error' ? 'rgba(255,139,139,0.6)' : 'var(--border)';
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2400);
        };

        const updateStatus = (connected, text) => {
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
            const outer = document.createElement('div');
            outer.className = 'table-wrap';
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
                    // Force date strings into an English-readable format if possible
                    if (typeof cell === 'string' && cell.match(/^\\d{4}-\\d{2}-\\d{2}/)) {
                        const parsed = new Date(cell);
                        if (!isNaN(parsed.getTime())) {
                            cell = parsed.toDateString();
                        }
                    }
                    const td = document.createElement('td');
                    td.textContent = cell === null ? 'NULL' : cell;
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            outer.appendChild(table);
            wrapper.appendChild(outer);
        };

        const fetchConfig = async () => {
            const res = await fetch('/api/config');
            if (!res.ok) return;
            const cfg = await res.json();
            document.getElementById('host').value = cfg.host || 'localhost';
            document.getElementById('port').value = cfg.port || '3306';
            document.getElementById('user').value = cfg.user || 'root';
            document.getElementById('password').value = cfg.password || '';
            document.getElementById('database').value = 'nhs_database';
            document.getElementById('auto-connect').checked = cfg.auto_connect == 'True';
        };

        const refreshStatus = async () => {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();
            if (data.connected) {
                updateStatus(true, `Connected · ${data.database}`);
                connectionNote.textContent = `Connected to ${data.database} @ ${data.host}`;
            } else {
                updateStatus(false, 'Disconnected');
                connectionNote.textContent = 'Provide connection details to start.';
            }
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
            try {
                setLoading(connectBtn, true, 'Connecting...');
                const res = await fetch('/api/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok || !data.success) {
                    showToast(data.message || 'Connection failed', 'error');
                    await refreshStatus();
                    return;
                }
                showToast('Database connected');
                await refreshStatus();
            } finally {
                setLoading(connectBtn, false);
            }
        });

        document.getElementById('disconnect-btn').addEventListener('click', async () => {
            await fetch('/api/disconnect', { method: 'POST' });
            showToast('Disconnected', 'error');
            await refreshStatus();
        });

        document.getElementById('healthcare-form').addEventListener('submit', async (evt) => {
            evt.preventDefault();
            const params = new URLSearchParams({
                county: document.getElementById('hc-county').value.trim(),
                district: document.getElementById('hc-district').value.trim(),
                org_type: document.getElementById('hc-type').value.trim(),
                emergency_only: document.getElementById('hc-emergency').checked ? '1' : '',
                limit: document.getElementById('hc-limit').value || '50'
            });
            try {
                setLoading(hcBtn, true, 'Loading...');
                const res = await fetch('/api/healthcare-search?' + params.toString());
                const data = await res.json();
                if (!res.ok || !data.success) {
                    showToast(data.message || 'Search failed', 'error');
                    return;
                }
                renderTable('healthcare-results', data.columns, data.rows);
                document.getElementById('healthcare-meta').textContent = `Records: ${data.rowCount} · Duration: ${data.duration.toFixed(3)}s`;
            } finally {
                setLoading(hcBtn, false);
            }
        });

        document.getElementById('patient-form').addEventListener('submit', async (evt) => {
            evt.preventDefault();
            const statuses = Array.from(document.querySelectorAll('.pt-status-opt:checked')).map(el => el.value);
            const params = new URLSearchParams({
                name: document.getElementById('pt-name').value.trim(),
                nhs: document.getElementById('pt-nhs').value.trim(),
                county: document.getElementById('pt-county').value.trim(),
                district: document.getElementById('pt-district').value.trim(),
                status_list: statuses.join(','),
                procedure: document.getElementById('pt-procedure').value.trim(),
                enc_from: document.getElementById('pt-enc-from').value,
                enc_to: document.getElementById('pt-enc-to').value,
                order: document.getElementById('pt-sort').value,
                limit: document.getElementById('pt-limit').value || '50'
            });
            try {
                setLoading(ptBtn, true, 'Loading...');
                const res = await fetch('/api/patient-search?' + params.toString());
                const data = await res.json();
                if (!res.ok || !data.success) {
                    showToast(data.message || 'Search failed', 'error');
                    return;
                }
                renderTable('patient-results', data.columns, data.rows);
                document.getElementById('patient-meta').textContent = `Records: ${data.rowCount} · Duration: ${data.duration.toFixed(3)}s`;
            } finally {
                setLoading(ptBtn, false);
            }
        });

        const loadTables = async () => {
            const res = await fetch('/api/tables');
            if (!res.ok) return;
            const data = await res.json();
            tableSelect.innerHTML = '';
            data.tables.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.key;
                opt.textContent = `${item.label} (${item.table})`;
                tableSelect.appendChild(opt);
            });
        };

        document.getElementById('load-table').addEventListener('click', async () => {
            const key = tableSelect.value;
            if (!key) { showToast('Pick a table first', 'error'); return; }
            const params = new URLSearchParams({
                search: document.getElementById('table-search').value.trim(),
                limit: document.getElementById('table-limit').value || '100'
            });
            try {
                setLoading(loadTableBtn, true, 'Loading...');
                const res = await fetch(`/api/table/${encodeURIComponent(key)}?${params.toString()}`);
                const data = await res.json();
                if (!res.ok || !data.success) {
                    showToast(data.message || 'Load failed', 'error');
                    return;
                }
                renderTable('table-results', data.columns, data.rows);
                document.getElementById('table-meta').textContent = `Records: ${data.rowCount} · Duration: ${data.duration.toFixed(3)}s`;
            } finally {
                setLoading(loadTableBtn, false);
            }
        });

        window.addEventListener('load', async () => {
            await fetchConfig();
            await refreshStatus();
            await loadTables();
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
