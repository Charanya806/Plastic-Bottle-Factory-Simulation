import sqlite3
from pathlib import Path


def initialize_database():
    db_path = Path(__file__).with_name("factory.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS production(
            id INTEGER PRIMARY KEY,
            produced INTEGER,
            good INTEGER,
            defective INTEGER,
            efficiency REAL,
            warehouse INTEGER
        )
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


initialize_database()