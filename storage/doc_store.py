import sqlite3
from typing import List, Dict, Any

class DocStore:
    def __init__(self, path="data_doc.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT,
                raw_json TEXT
            );
        """)
        # Simple key index via virtual table (optional) or path cache
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS key_index (
                doc_id INTEGER,
                key TEXT,
                value_text TEXT,
                FOREIGN KEY(doc_id) REFERENCES documents(id)
            );
        """)
        self.conn.commit()

    def insert(self, docs: List[Dict[str, Any]], namespace="default"):
        cur = self.conn.cursor()
        for doc in docs:
            cur.execute("INSERT INTO documents(namespace, raw_json) VALUES(?, json(?))", (namespace, json_dumps(doc)))
            doc_id = cur.lastrowid
            # Index top-level strings/numbers for quick filtering
            for k, v in doc.items():
                if isinstance(v, (str, int, float)):
                    cur.execute("INSERT INTO key_index(doc_id, key, value_text) VALUES(?, ?, ?)", (doc_id, k, str(v)))
        self.conn.commit()

    def query(self, namespace="default", filters: Dict[str, Any] = None):
        base = "SELECT id, raw_json FROM documents WHERE namespace=?"
        params = [namespace]
        if filters:
            for k, v in filters.items():
                base += " AND json_extract(raw_json, ?) = ?"
                params.append(f"$.{k}")
                params.append(v)
        return [dict(id=row[0], json=row[1]) for row in self.conn.execute(base, params)]
        
def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)
