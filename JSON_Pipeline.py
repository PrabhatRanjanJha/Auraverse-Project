from typing import List, Dict, Any
from storage.sql_store import SQLStore
from storage.doc_store import DocStore
from storage.schema_analyzer import analyze_batch, propose_sql_model
from models.registry import SchemaRegistry
from rag.retriever import SchemaRetriever
from rag.query_router import QueryRouter, build_sql_query, build_doc_query
import json
import sqlite3

class IngestionApp:
    def __init__(self, sql_path="data_sql.db", doc_path="data_doc.db"):
        self.sql = SQLStore(sql_path)
        self.doc = DocStore(doc_path)
        self.registry = SchemaRegistry()
        self.retriever = SchemaRetriever()
        self.router = QueryRouter(self.registry)

    def ingest(self, json_objects: List[Dict[str, Any]], metadata: str = ""):
        analysis = analyze_batch(json_objects)
        if analysis["decision"] == "SQL":
            model = propose_sql_model(analysis)
            # use first doc for initial types
            items, childs = self.sql.ensure_schema(model, json_objects[0])
            self.sql.insert(model, json_objects)
            # register schema
            self.registry.register(model["top_table"], model, notes=metadata)
        else:
            # Document store: record paths, keep snapshot
            paths = sorted(list(analysis["path_types"].keys()))
            schema = {"paths": paths, "namespace": "default"}
            self.doc.insert(json_objects, namespace="default")
            self.registry.register("default", schema, notes=metadata)
        # rebuild retriever
        self.retriever.build(self.registry)

    def search_schema(self, text_query: str, top_k=5):
        return self.retriever.search(text_query, top_k=top_k)

    def query(self, query_req: Dict[str, Any]):
        route, req = self.router.route(query_req)
        if route == "SQL":
            schema = self.registry.get(req["target"])
            sql, params = build_sql_query(schema, req)
            with sqlite3.connect(self.sql.engine.url.database) as conn:
                rows = conn.execute(sql, params).fetchall()
                cols = [d[0] for d in conn.execute(f"PRAGMA table_info({schema['top_table']})")]
            return {"type": "SQL", "rows": rows}
        else:
            dq = build_doc_query(req)
            res = self.doc.query(namespace=dq["namespace"], filters=dq["filters"])
            return {"type": "DOC", "docs": res}

# Example usage:
if __name__ == "__main__":
    app = IngestionApp()
    sample = [
        {"id": 1, "name": "Alice", "country": "IN", "orders": [{"sku": "A1", "qty": 2}]},
        {"id": 2, "name": "Bob", "country": "US", "orders": [{"sku": "B1", "qty": 1}, {"sku": "B2", "qty": 3}]}
    ]
    app.ingest(sample, metadata="Customer orders batch Nov15")
    print(app.search_schema("orders customers country"))
    print(app.query({"target": "items", "filters": {"country": "IN"}, "fields": ["id","name"], "limit": 10}))
    # Document path example
    docs = [{"event": "click", "user": {"id": 99}, "meta": {"page": "home"}},
            {"event": "view", "meta": {"page": "product"}, "score": 0.87}]
    app.ingest(docs, metadata="Telemetry stream")
    print(app.search_schema("events telemetry meta"))
    print(app.query({"target": "default", "filters": {"event": "click"}}))
