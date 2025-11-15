from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, Boolean, JSON, ForeignKey, Text, Index
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, List
import sqlite3

def map_type(v):
    if v is None: return Text
    if isinstance(v, bool): return Boolean
    if isinstance(v, int): return Integer
    if isinstance(v, float): return Float
    # strings or mixed -> Text
    return Text

class SQLStore:
    def __init__(self, path="data_sql.db"):
        self.engine = create_engine(f"sqlite:///{path}")
        self.meta = MetaData()
        self.Session = sessionmaker(bind=self.engine)

    def ensure_schema(self, model: Dict[str, Any], sample_doc: Dict[str, Any]):
        # Build or update tables based on proposed model
        # Top-level table
        cols = [Column("id", Integer, primary_key=True, autoincrement=True)]
        for c in model["top_cols"]:
            sample_val = sample_doc.get(c, None)
            cols.append(Column(c, map_type(sample_val)))
        cols.append(Column("_raw", SQLITE_JSON))  # keep raw for fidelity
        items = Table(model["top_table"], self.meta, *cols, extend_existing=True)

        # Child tables
        child_ts = []
        for child in model["child_tables"]:
            name = child["name"]
            cols = [Column("id", Integer, primary_key=True, autoincrement=True),
                    Column("parent_id", Integer, ForeignKey(f"{model['top_table']}.id"))]
            # Infer child columns from first element if present
            child_sample = self._extract_first(child["root_path"], sample_doc) or {}
            for k, v in child_sample.items():
                cols.append(Column(k.replace(".", "_"), map_type(v)))
            cols.append(Column("_raw", SQLITE_JSON))
            t = Table(name, self.meta, *cols, extend_existing=True)
            child_ts.append(t)

        self.meta.create_all(self.engine)
        # Add basic indexes
        for t in [items] + child_ts:
            for c in t.columns:
                if c.name not in ("id", "_raw", "parent_id"):
                    try:
                        idx = Index(f"ix_{t.name}_{c.name}", c)
                        idx.create(self.engine)
                    except Exception:
                        pass

        return items, child_ts

    def _extract_first(self, root_path, doc):
        # root_path like 'orders' for top-level list of objects
        # or 'profile.addresses' etc.
        parts = root_path.split(".")
        cur = doc
        for p in parts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        if isinstance(cur, list) and cur and isinstance(cur[0], dict):
            return cur[0]
        return None

    def insert(self, model, docs: List[Dict[str, Any]]):
        items_table = self.meta.tables[model["top_table"]]
        session = self.Session()
        try:
            for doc in docs:
                row = {}
                for c in model["top_cols"]:
                    row[c] = doc.get(c)
                row["_raw"] = doc
                res = session.execute(items_table.insert().values(**row))
                parent_id = res.inserted_primary_key[0]

                for child in model["child_tables"]:
                    name = child["name"]
                    child_table = self.meta.tables[name]
                    data_list = self._get_by_path(doc, child["root_path"])
                    if isinstance(data_list, list):
                        for item in data_list:
                            crow = {"parent_id": parent_id, "_raw": item}
                            for k, v in item.items():
                                crow[k.replace(".", "_")] = v
                            session.execute(child_table.insert().values(**crow))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_by_path(self, doc, path):
        parts = path.split(".")
        cur = doc
        for p in parts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        return cur
