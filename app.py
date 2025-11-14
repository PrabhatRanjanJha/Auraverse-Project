# app.py
import streamlit as st
import os
import tempfile
from classifier import classify_and_organize

st.set_page_config(page_title="Smart File Classifier", page_icon="📂", layout="wide")
st.title("📂 Smart File Classifier")
st.markdown("Upload any file — I will classify it **by content topic** and organize it.")

uploaded_files = st.file_uploader(
    "Upload files",
    accept_multiple_files=True
)

base_dir = "categorized_data"
os.makedirs(base_dir, exist_ok=True)

if uploaded_files:
    st.info(f"Processing {len(uploaded_files)} file(s)...")
    progress = st.progress(0)
    i = 0

    for uploaded_file in uploaded_files:
        i += 1

        # Save to temp preserving original name
        tmp_dir = tempfile.gettempdir()
        temp_path = os.path.join(tmp_dir, uploaded_file.name)

        # Avoid collisions
        if os.path.exists(temp_path):
            name, ext = os.path.splitext(uploaded_file.name)
            counter = 1
            while os.path.exists(temp_path):
                temp_path = os.path.join(tmp_dir, f"{name}_{counter}{ext}")
                counter += 1

        # Write file
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

        # Classify and move
        try:
            topic, file_type, new_path = classify_and_organize(temp_path, base_dir)
            st.success(f"**{uploaded_file.name}** → Topic: `{topic}` → Type: `{file_type}`")
            st.code(new_path)
        except Exception as e:
            st.error(f"Failed to classify {uploaded_file.name}: {e}")

        progress.progress(int(i / len(uploaded_files) * 100))

    st.balloons()
    st.info("🎉 All files processed! Check the `categorized_data` folder.")
