from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def schema_to_text(name: str, schema: Dict[str, Any], notes: str = ""):
    parts = [f"name: {name}", notes]
    # include tables, columns, relationships
    if "top_table" in schema:
        parts.append(f"top_table: {schema['top_table']}")
        parts.append("top_cols: " + " ".join(schema.get("top_cols", [])))
        for ct in schema.get("child_tables", []):
            parts.append(f"child_table: {ct['name']} root: {ct['root_path']}")
    else:
        # document store schema
        paths = schema.get("paths", [])
        parts.append("paths: " + " ".join(paths))
    return "\n".join(parts)

class SchemaRetriever:
    def __init__(self):
        self.names = []
        self.docs = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2))
        self.matrix = None

    def build(self, registry, notes_map: Dict[str, str] = None):
        self.names = []
        self.docs = []
        for name, sch in registry.list():
            notes = (notes_map or {}).get(name, "")
            self.names.append(name)
            self.docs.append(schema_to_text(name, sch, notes))
        if self.docs:
            self.matrix = self.vectorizer.fit_transform(self.docs)

    def search(self, query: str, top_k: int = 5):
        if not self.docs:
            return []
        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix)[0]
        ranked = sorted(zip(self.names, sims), key=lambda x: x[1], reverse=True)[:top_k]
        return ranked
