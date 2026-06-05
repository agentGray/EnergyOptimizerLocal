"""
CSV → DuckDB/SQLite loader for Energy Optimizer Agent.
Reads energy-related CSVs at startup and loads into database tables.
"""

import os
import csv
from .db import get_conn, DB_ENGINE

# Path to CSV data folder (relative to project root)
CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "csv")


def _csv_path(filename: str) -> str:
    return os.path.join(CSV_DIR, filename)


def _exec(con, sql, params=None):
    """Execute SQL on the connection, handling both DuckDB and SQLite."""
    if DB_ENGINE == "duckdb":
        if params:
            con.execute(sql, params)
        else:
            con.execute(sql)
    else:
        cursor = con.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)


def load_all():
    """Load all energy-related CSV data into DuckDB/SQLite."""
    con = get_conn()
    try:
        _create_tables(con)
        _load_energy_assets(con)
        _load_energy_hourly(con)
        _load_utilities(con)
        _load_machines(con)
        _load_twin_kpis(con)
        _load_production_orders(con)
        if DB_ENGINE == "sqlite":
            con.commit()
        print("[Loader] All energy data loaded successfully.")
    finally:
        con.close()


def _create_tables(con):
    """Create all tables for the energy optimizer."""
    _exec(con, """
        CREATE TABLE IF NOT EXISTS energy_assets (
            id TEXT PRIMARY KEY,
            name TEXT,
            rated_kw REAL,
            current_kw REAL,
            anomaly_threshold_pct REAL,
            shiftable INTEGER,
            critical INTEGER
        )
    """)

    _exec(con, """
        CREATE TABLE IF NOT EXISTS energy_hourly (
            hour TEXT,
            kw_base REAL
        )
    """)

    _exec(con, """
        CREATE TABLE IF NOT EXISTS utilities (
            id TEXT PRIMARY KEY,
            name TEXT,
            health REAL,
            rul INTEGER,
            status TEXT,
            vib REAL,
            temp REAL,
            pressure REAL,
            oee_link TEXT,
            degrade_rate REAL
        )
    """)

    _exec(con, """
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            name TEXT,
            line TEXT,
            plant TEXT,
            oee REAL,
            avail REAL,
            perf REAL,
            qual REAL,
            health REAL,
            rul INTEGER,
            status TEXT,
            loss TEXT,
            loss_min INTEGER,
            vib REAL,
            temp REAL,
            degrade_rate REAL
        )
    """)

    _exec(con, """
        CREATE TABLE IF NOT EXISTS twin_kpis (
            kpi_id TEXT,
            kpi_name TEXT,
            unit TEXT,
            actual REAL,
            twin_predicted REAL,
            divergence_threshold_pct REAL,
            asset_id TEXT
        )
    """)

    _exec(con, """
        CREATE TABLE IF NOT EXISTS production_orders (
            id TEXT,
            product TEXT,
            qty_kg REAL,
            plan_yield REAL,
            actual_yield REAL,
            status TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)


def _load_energy_assets(con):
    """Load energy_assets.csv."""
    _exec(con, "DELETE FROM energy_assets")
    filepath = _csv_path("energy_assets.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO energy_assets VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    row["id"],
                    row["name"],
                    float(row["rated_kw"]),
                    float(row["current_kw"]),
                    float(row["anomaly_threshold_pct"]),
                    1 if row["shiftable"].lower() == "true" else 0,
                    1 if row["critical"].lower() == "true" else 0,
                ],
            )


def _load_energy_hourly(con):
    """Load energy_hourly.csv."""
    _exec(con, "DELETE FROM energy_hourly")
    filepath = _csv_path("energy_hourly.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO energy_hourly VALUES (?, ?)",
                [row["hour"], float(row["kw_base"])],
            )


def _load_utilities(con):
    """Load utilities.csv."""
    _exec(con, "DELETE FROM utilities")
    filepath = _csv_path("utilities.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO utilities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    row["id"],
                    row["name"],
                    float(row["health"]),
                    int(row["rul"]),
                    row["status"],
                    float(row["vib"]),
                    float(row["temp"]),
                    float(row["pressure"]),
                    row["oee_link"] if row["oee_link"] else None,
                    float(row["degrade_rate"]),
                ],
            )


def _load_machines(con):
    """Load machines.csv."""
    _exec(con, "DELETE FROM machines")
    filepath = _csv_path("machines.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO machines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    row["id"],
                    row["name"],
                    row["line"],
                    row["plant"],
                    float(row["oee"]),
                    float(row["avail"]),
                    float(row["perf"]),
                    float(row["qual"]),
                    float(row["health"]),
                    int(row["rul"]),
                    row["status"],
                    row["loss"],
                    int(row["loss_min"]),
                    float(row["vib"]),
                    float(row["temp"]),
                    float(row["degrade_rate"]),
                ],
            )


def _load_twin_kpis(con):
    """Load twin_kpis.csv."""
    _exec(con, "DELETE FROM twin_kpis")
    filepath = _csv_path("twin_kpis.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO twin_kpis VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    row["kpi_id"],
                    row["kpi_name"],
                    row["unit"],
                    float(row["actual"]) if row["actual"] else None,
                    float(row["twin_predicted"]) if row["twin_predicted"] else None,
                    float(row["divergence_threshold_pct"]) if row["divergence_threshold_pct"] else None,
                    row["asset_id"] if row["asset_id"] else None,
                ],
            )


def _load_production_orders(con):
    """Load production_orders.csv."""
    _exec(con, "DELETE FROM production_orders")
    filepath = _csv_path("production_orders.csv")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _exec(con,
                "INSERT INTO production_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    row["id"],
                    row["product"],
                    float(row["qty_kg"]),
                    float(row["plan_yield"]),
                    float(row["actual_yield"]) if row["actual_yield"] else None,
                    row["status"],
                    row["start_date"],
                    row["end_date"],
                ],
            )
