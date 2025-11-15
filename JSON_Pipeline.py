# main.py
import streamlit as st
import json
import os
import shutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from JSON_handler import is_sql_compatible, generate_schema, handle_nosql_json


UPLOADS_DIR = "uploads"
SQL_DIR = "structured_data"
NOSQL_DIR = "unstructured_data"


def ensure_directories():
    """Create all required directories."""
    for d in [UPLOADS_DIR, SQL_DIR, NOSQL_DIR]:
        os.makedirs(d, exist_ok=True)


def classify_and_move(file_path):
    """Classify uploaded JSON file and move accordingly."""
    if not file_path.endswith(".json"):
        return

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        st.write(f"❌ Error reading {file_path}: {e}") #To be replaced by st.write()
        return

    filename = os.path.basename(file_path)
    name, _ = os.path.splitext(filename)

    if is_sql_compatible(data):
        st.write(f"✅ '{filename}' classified as SQL-compatible.")
        sql_schema = generate_schema(data, schema_name=name)

        # Move JSON file
        shutil.move(file_path, os.path.join(SQL_DIR, filename))

        # Save schema as .sql
        schema_path = os.path.join(SQL_DIR, f"{name}_schema.sql")
        with open(schema_path, "w") as f:
            f.write(sql_schema)

        st.write(f"→ Moved to '{SQL_DIR}' and created '{schema_path}'\n")
    else:
        st.write(f"⚠️ '{filename}' classified as NoSQL.")
        message = handle_nosql_json(data, collection_name=name)
        shutil.move(file_path, os.path.join(NOSQL_DIR, filename))
        st.write(f"→ Moved to '{NOSQL_DIR}'\n{message}\n")


# class UploadEventHandler(FileSystemEventHandler):
#     """Watches for new JSON uploads."""

#     def on_created(self, event):
#         if not event.is_directory:
#             classify_and_move(event.src_path)


if __name__ == "__main__":
    ensure_directories()
    st.title("JSON Handler - Upload & Process")
    st.write("📤 Upload JSON files to classify and process them")
    
    # Streamlit file uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type="json")
    
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            filename = uploaded_file.name
            name, _ = os.path.splitext(filename)
            
            # Save file to uploads directory
            file_path = os.path.join(UPLOADS_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())


           


            # Classify and process
            if is_sql_compatible(data):
                st.success(f"✅ '{filename}' classified as SQL-compatible.")
                shutil.move(file_path, os.path.join(SQL_DIR, filename))
               
                
                
            else:
                st.warning(f"⚠️ '{filename}' classified as NoSQL.")
                message = handle_nosql_json(data, collection_name=name)
                shutil.move(file_path, os.path.join(NOSQL_DIR, filename))
                st.info(f"→ Moved to '{NOSQL_DIR}'\n{message}")

             #Creating The Schema
            JSON_schema = generate_schema(data, schema_name=name)
            st.json(JSON_schema)
            schema_path = os.path.join(SQL_DIR, f"{name}_schema.sql")
            with open(schema_path, "w") as f:
                json.dump(JSON_schema, f, indent=4)
                st.info(f"→ Moved to '{SQL_DIR}' and created '{schema_path}'")
                
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
