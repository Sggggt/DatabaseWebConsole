"""
NHS database setup helper.

Features:
1. Reads MySQL connection info from db_config.ini (host/port/user/database).
2. Prompts for the password at runtime (never stored in the file).
3. Uses Tables.sql and Data.sql to create and seed the database.
4. Optional --reset flag to drop and recreate the database before loading data.
"""

from __future__ import annotations

import argparse
import configparser
from getpass import getpass
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import mysql.connector
from mysql.connector import Error

# Paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "db_config.ini"
TASK9_CREATE_FILE = BASE_DIR / "Tables.sql"
TASK9_INSERT_FILE = BASE_DIR / "Data.sql"

# Defaults
DEFAULT_DB = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "database": "nhs_database",
}


def load_db_config() -> dict:
    config = DEFAULT_DB.copy()
    parser = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        parser.read(CONFIG_FILE, encoding="utf-8")
        if parser.has_section("mysql"):
            section = parser["mysql"]
            for key in ("host", "port", "user", "database"):
                if section.get(key):
                    config[key] = section.get(key, config[key])
    config["port"] = int(config["port"])
    return config


def prompt_password(config: dict) -> None:
    config["password"] = getpass(
        f"MySQL password for {config['user']}@{config['host']}: "
    )


def resolve_sql_files() -> Tuple[str, Path, Path]:
    """
    Use the Tables.sql and Data.sql scripts.
    """
    if not (TASK9_CREATE_FILE.exists() and TASK9_INSERT_FILE.exists()):
        raise FileNotFoundError(
            f"Task9 SQL files not found: {TASK9_CREATE_FILE} / {TASK9_INSERT_FILE}"
        )
    return ("Task9", TASK9_CREATE_FILE, TASK9_INSERT_FILE)


def split_statements(sql_text: str) -> List[str]:
    statements: List[str] = []
    buffer: List[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buffer).rstrip().rstrip(";"))
            buffer.clear()
    if buffer:
        statements.append("\n".join(buffer).rstrip().rstrip(";"))
    return statements


def run_sql_file(cursor, path: Path, ignore_errors: Iterable[int] = ()) -> int:
    sql = path.read_text(encoding="utf-8")
    executed = 0
    for statement in split_statements(sql):
        if not statement.strip():
            continue
        try:
            cursor.execute(statement)
            executed += 1
        except Error as err:
            if err.errno in ignore_errors:
                print(f"  [skip] {err.msg}")
                continue
            raise
    return executed

def setup_database(
    reset: bool,
    password: str | None = None,
) -> None:
    config = load_db_config()
    if password is None:
        prompt_password(config)
    else:
        config["password"] = password

    server_cfg = {
        "host": config["host"],
        "port": config["port"],
        "user": config["user"],
        "password": config["password"],
    }

    model_name, create_file, insert_file = resolve_sql_files()

    print("=" * 60)
    print("NHS Database Setup")
    print("=" * 60)
    print(f"Using MySQL server {config['host']}:{config['port']} as {config['user']}")
    print(f"Selected model: {model_name}")

    try:
        conn = mysql.connector.connect(**server_cfg)
        cursor = conn.cursor()
    except Error as err:
        raise SystemExit(f"Unable to connect to MySQL: {err}") from err

    db_name = config["database"]

    try:
        if reset:
            print(f"\n- Dropping database `{db_name}` (reset requested)...")
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            conn.commit()

        print(f"\n- Ensuring database `{db_name}` exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"USE `{db_name}`")
        conn.commit()
        print("  [OK] Database ready.")

        print(f"\n- Executing table definitions from {create_file}")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        run_sql_file(cursor, create_file, ignore_errors=(1050, 1091, 1061))
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        print("  [OK] Table creation script finished.")

        print(f"\n- Executing data inserts from {insert_file}")
        run_sql_file(cursor, insert_file, ignore_errors=())
        conn.commit()
        print("  [OK] Data load script finished.")

        print("\n- Verifying tables...")
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        if tables:
            print(f"  Found {len(tables)} tables: {', '.join(tables[:8])}"
                  f"{' ...' if len(tables) > 8 else ''}")
        else:
            print("  [WARN] No tables found.")

        print("\nSetup complete. You can now run nhs_database_app.py and connect.")

    finally:
        cursor.close()
        conn.close()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and seed the NHS database from Tables/Data SQL files."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the target database before recreating it.",
    )
    parser.add_argument(
        "--password",
        help="Provide the MySQL password non-interactively.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> None:
    args = parse_args(argv)
    try:
        setup_database(
            reset=args.reset,
            password=args.password,
        )
    except FileNotFoundError as err:
        print(f"[ERROR] {err}")
        sys.exit(1)
    except Error as err:
        print(f"[ERROR] MySQL error: {err}")
        sys.exit(err.errno or 1)
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)


if __name__ == "__main__":
    main(sys.argv[1:])
