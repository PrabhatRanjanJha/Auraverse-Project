from typing import Dict, Any, Tuple, List

class QueryRouter:
    def __init__(self, registry):
        self.registry = registry

    def route(self, query: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        query format:
        {
          "target": "items" or schema name,
          "filters": {"status": "active", "country": "IN"},
          "fields": ["id", "name"],
          "limit": 50
        }
        """
        target = query.get("target")
        schema = self.registry.get(target)
        if not schema:
            return ("DOC", query)  # default to doc filtering
        if "top_table" in schema:
            return ("SQL", query)
        return ("DOC", query)

def build_sql_query(schema: Dict[str, Any], query: Dict[str, Any]) -> str:
    table = schema["top_table"]
    fields = query.get("fields") or ["*"]
    where_clauses = []
    params = []
    for k, v in (query.get("filters") or {}).items():
        where_clauses.append(f"{k} = ?")
        params.append(v)
    where = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    limit = f" LIMIT {int(query.get('limit', 100))}"
    return f"SELECT {', '.join(fields)} FROM {table}{where}{limit}", params

def build_doc_query(query: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "namespace": query.get("target", "default"),
        "filters": query.get("filters") or {}
    }
