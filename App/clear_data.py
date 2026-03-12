"""
Utility script to purge data from the nhs_database schema.

Usage examples:
    python clear_data.py                 # Truncate every table (default)
    python clear_data.py --drop          # Drop the whole database
    python clear_data.py --force         # Skip the confirmation prompt
"""

from __future__ import annotations

import argparse
import configparser
from getpass import getpass
import sys
from pathlib import Path
from typing import Dict, List

import mysql.connector
from mysql.connector import Error

APP_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = APP_ROOT / "db_config.ini"


def load_settings() -> Dict[str, str]:
    defaults = {
        "host": "localhost",
        "port": "3306",
        "user": "root",
        "database": "nhs_database",
    }
    parser = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        parser.read(CONFIG_FILE, encoding="utf-8")
        if parser.has_section("mysql"):
            mysql_section = parser["mysql"]
            for key in defaults:
                defaults[key] = mysql_section.get(key, defaults[key])
    return defaults


def confirm_action(database: str, force: bool) -> None:
    if force:
        return
    prompt = (
        f"This will permanently remove data from database '{database}'.\n"
        "Type the database name to continue: "
    )
    answer = input(prompt).strip()
    if answer != database:
        raise SystemExit("Cancelled.")


def drop_database(cursor, database: str) -> None:
    cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")


def truncate_tables(cursor, database: str) -> List[str]:
    cursor.execute(f"USE `{database}`")
    cursor.execute("SHOW FULL TABLES WHERE Table_Type = 'BASE TABLE'")
    tables = [row[0] for row in cursor.fetchall()]
    if not tables:
        return []

    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    for table in tables:
        cursor.execute(f"TRUNCATE TABLE `{table}`")
    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    return tables


def clear_database(drop: bool, force: bool) -> None:
    settings = load_settings()
    confirm_action(settings["database"], force)
    password = getpass(
        f"MySQL password for {settings['user']}@{settings['host']}: "
    )
    connection = None
    try:
        connection = mysql.connector.connect(
            host=settings["host"],
            port=int(settings["port"]),
            user=settings["user"],
            password=password,
        )
        cursor = connection.cursor()
        if drop:
            drop_database(cursor, settings["database"])
            connection.commit()
            print(f"Dropped database `{settings['database']}`.")
        else:
            tables = truncate_tables(cursor, settings["database"])
            connection.commit()
            if tables:
                print(
                    f"Truncated {len(tables)} tables in `{settings['database']}`:"
                )
                for name in tables:
                    print(f"  - {name}")
            else:
                print(f"No tables found in `{settings['database']}`.")
    except Error as exc:
        raise SystemExit(f"MySQL error: {exc}") from exc
    finally:
        if connection:
            connection.close()


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Purge data from the nhs_database schema.",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the entire database instead of truncating tables.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> None:
    args = parse_args(argv)
    clear_database(drop=args.drop, force=args.force)


if __name__ == "__main__":
    main(sys.argv[1:])
