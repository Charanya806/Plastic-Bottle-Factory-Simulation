import sqlite3
from pathlib import Path


def save_data(produced, good, defective, efficiency, warehouse):
    db_path = Path(__file__).with_name("factory.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO production (produced, good, defective, efficiency, warehouse)
        VALUES (?, ?, ?, ?, ?)
        """,
        (produced, good, defective, efficiency, warehouse),
    )
    conn.commit()
    conn.close()
    return str(db_path)