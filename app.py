# app.py
import streamlit as st
import os
import tempfile
from classifier import classify_and_organize

st.set_page_config(page_title="Smart File Classifier", page_icon="📂", layout="wide")

st.title("📂 Smart File Classifier")
st.markdown("Upload files — I'll classify by *content* first, then by *file type*.")

uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)

base_dir = "categorized_data"
os.makedirs(base_dir, exist_ok=True)

if uploaded_files:
    st.write("Processing uploaded files...")

    for uploaded_file in uploaded_files:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
            tmp_name = uploaded_file.name

        # Rename to original name
        final_temp_path = os.path.join(tempfile.gettempdir(), tmp_name)
        os.rename(tmp_path, final_temp_path)

        # Classify and organize
        category, file_type, new_path = classify_and_organize(final_temp_path, base_dir)

        st.success(f"✅ {uploaded_file.name} → Category: {category} → Type: {file_type}")
        st.write(f"📁 Saved to: {new_path}")

    st.markdown("---")
    st.info("All files organized! Check 'categorized_data' folder.")