import sqlite3
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

DB_PATH = Path("charmsat_history.db")

class StorageEngine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Rule sets table
            c.execute("""
                CREATE TABLE IF NOT EXISTS rule_sets (
                    name TEXT PRIMARY KEY,
                    yaml_content TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Projects & Revisions table
            c.execute("""
                CREATE TABLE IF NOT EXISTS project_history (
                    id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    revision TEXT NOT NULL,
                    signals_json TEXT NOT NULL,
                    alloc_result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Benchmark results table
            c.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_name TEXT NOT NULL,
                    signal_count INTEGER NOT NULL,
                    engine TEXT NOT NULL,
                    violations INTEGER NOT NULL,
                    cabinets INTEGER NOT NULL,
                    lower_bound INTEGER NOT NULL,
                    rev_b_moves INTEGER NOT NULL,
                    runtime_s REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_rule_set(self, name: str, yaml_content: str):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO rule_sets (name, yaml_content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (name, yaml_content))
            conn.commit()

    def get_rule_set(self, name: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT yaml_content FROM rule_sets WHERE name = ?", (name,))
            row = c.fetchone()
            return row[0] if row else None

    def list_rule_sets(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM rule_sets ORDER BY updated_at DESC")
            return [row[0] for row in c.fetchall()]

    def save_benchmark(self, run_name: str, count: int, engine: str, viols: int, cabs: int, lb: int, moves: int, runtime: float):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO benchmark_runs (run_name, signal_count, engine, violations, cabinets, lower_bound, rev_b_moves, runtime_s)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_name, count, engine, viols, cabs, lb, moves, runtime))
            conn.commit()

    def get_benchmarks(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT run_name, signal_count, engine, violations, cabinets, lower_bound, rev_b_moves, runtime_s, created_at FROM benchmark_runs ORDER BY id DESC")
            rows = c.fetchall()
            return [
                {
                    "run_name": r[0],
                    "signal_count": r[1],
                    "engine": r[2],
                    "violations": r[3],
                    "cabinets": r[4],
                    "lower_bound": r[5],
                    "rev_b_moves": r[6],
                    "runtime_s": r[7],
                    "created_at": r[8]
                }
                for r in rows
            ]
