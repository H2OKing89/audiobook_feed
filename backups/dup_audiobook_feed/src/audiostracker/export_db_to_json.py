import sqlite3
import json
import os

def export_db_to_json(db_path='audiobooks.db', out_path='audiobooks_export.json'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM audiobooks')
    rows = [dict(row) for row in cur.fetchall()]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(rows)} audiobooks to {out_path}")
    conn.close()

if __name__ == "__main__":
    # Use the DB in the current directory by default
    db_path = os.path.join(os.path.dirname(__file__), 'audiobooks.db')
    out_path = os.path.join(os.path.dirname(__file__), 'audiobooks_export.json')
    export_db_to_json(db_path, out_path)
