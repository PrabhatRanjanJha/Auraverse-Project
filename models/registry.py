from typing import Dict, Any, List
import time

class SchemaRegistry:
    def __init__(self):
        self.schemas = {}  # name -> dict
        self.snapshots = []  # list of {ts, name, schema, notes}

    def register(self, name: str, schema: Dict[str, Any], notes: str = ""):
        self.schemas[name] = schema
        self.snapshots.append({
            "ts": time.time(),
            "name": name,
            "schema": schema,
            "notes": notes
        })

    def list(self):
        return list(self.schemas.items())

    def get(self, name):
        return self.schemas.get(name)

    def history(self, name):
        return [s for s in self.snapshots if s["name"] == name]
