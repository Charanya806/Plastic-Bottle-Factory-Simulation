import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt


def generate_report(output_path="factory_report.png"):
    db_path = Path(__file__).with_name("factory.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT produced, good, defective FROM production")
    data = cursor.fetchall()
    conn.close()

    if not data:
        raise ValueError("No production data available yet")

    produced = [row[0] for row in data]
    good = [row[1] for row in data]
    defective = [row[2] for row in data]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(produced, label="Produced", color="#2e86de")
    ax.plot(good, label="Good", color="#2ecc71")
    ax.plot(defective, label="Defective", color="#e74c3c")
    ax.set_title("Plastic Factory Production Report")
    ax.set_xlabel("Production Records")
    ax.set_ylabel("Bottle Count")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    output_path = generate_report()
    print(f"Report saved to {output_path}")