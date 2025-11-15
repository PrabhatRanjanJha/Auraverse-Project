import json, os
from genson import SchemaBuilder

                            #  ____   ___  _
                            # / ___| / _ \| |
                            # \___ \| | | | |
                            #  ___) | |_| | |___
                            # |____/ \__\_\_____|

def generate_schema(data, schema_name="My Schema"):
    builder = SchemaBuilder()
    builder.add_object(data)
    schema = builder.to_schema()
    return schema


def is_sql_compatible(data):
    """
    Checks if JSON is SQL-compatible (all records have same keys)
    """
    if isinstance(data, dict):
        return True

    if isinstance(data, list) and all(isinstance(d, dict) for d in data):
        first_keys = set(data[0].keys())
        return all(set(d.keys()) == first_keys for d in data)

    return False


# def generate_sql_table(data, table_name="MyTable"):
#     """
#     Generate SQL CREATE TABLE statement based on JSON keys and value types
#     """
#     if isinstance(data, list):
#         sample = data[0]
#     else:
#         sample = data

#     sql_types = {
#         int: "INTEGER",
#         float: "FLOAT",
#         str: "TEXT",
#         bool: "BOOLEAN",
#     }


#     fields = []
#     for key, value in sample.items():
#         sql_type = sql_types.get(type(value), "TEXT")
#         fields.append(f"{key} {sql_type}")

#     fields_str = ",\n    ".join(fields)
#     create_stmt = f"CREATE TABLE {table_name} (\n    {fields_str}\n);"

#     return create_stmt

                #  _   _      ____   ___  _
                # | \ | | ___/ ___| / _ \| |
                # |  \| |/ _ \___ \| | | | |
                # | |\  | (_) |__) | |_| | |___
                # |_| \_|\___/____/ \__\_\_____|


def handle_nosql_json(data, collection_name="MyCollection", output_dir="nosql_collections"):
    """
    Saves NoSQL-compatible JSON as a collection file
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{collection_name}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return output_path
