from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Set
import itertools

def _type_name(v):
    if v is None: return "null"
    if isinstance(v, bool): return "bool"
    if isinstance(v, int): return "int"
    if isinstance(v, float): return "float"
    if isinstance(v, str): return "str"
    if isinstance(v, list): return "list"
    if isinstance(v, dict): return "obj"
    return "unknown"

def flatten_paths(d: Dict[str, Any], parent=""):
    paths = {}
    for k, v in d.items():
        p = f"{parent}.{k}" if parent else k
        t = _type_name(v)
        paths[p] = t
        if isinstance(v, dict):
            paths.update(flatten_paths(v, p))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # treat list of objects as relation candidate
            paths[p + "[]"] = "obj_list"
            # sample first item for shape
            paths.update(flatten_paths(v[0], p + "[]"))
    return paths

def analyze_batch(docs: List[Dict[str, Any]]):
    path_types = defaultdict(Counter)
    for doc in docs:
        fp = flatten_paths(doc)
        for p, t in fp.items():
            path_types[p][t] += 1

    total = len(docs)
    common_paths = {p for p, c in path_types.items() if sum(c.values())/total >= 0.8}
    optionality = {p: 1 - (sum(c.values())/total) for p, c in path_types.items()}
    type_variability = {p: len(c) for p, c in path_types.items()}

    # Identify relation candidates (lists of objects)
    relations = [p for p in path_types if p.endswith("[]")]

    # Stability score: common paths high, low variability
    stability_score = (
        len(common_paths)/(len(path_types) or 1)
        - sum(type_variability.values())/(10 * (len(path_types) or 1))
        - sum(optionality.values())/(len(optionality) or 1)
    )

    decision = "SQL" if stability_score >= 0.15 or len(relations) > 0 else "DOC"

    return {
        "decision": decision,
        "common_paths": common_paths,
        "optionality": optionality,
        "type_variability": type_variability,
        "relations": relations,
        "path_types": path_types,
        "stability_score": stability_score
    }

def propose_sql_model(analysis: Dict[str, Any]):
    # Derive top-level table and child tables from relations
    top_cols = []
    child_tables = []

    for p, types in analysis["path_types"].items():
        if "obj_list" in types:  # relation root
            child_root = p.replace("[]", "")
            child_tables.append({"name": child_root.replace(".", "_"),
                                 "root_path": child_root})
        elif "." not in p and not p.endswith("[]"):  # top-level fields
            top_cols.append(p)

    return {
        "top_table": "items",
        "top_cols": [c.replace(".", "_") for c in top_cols],
        "child_tables": child_tables
    }
