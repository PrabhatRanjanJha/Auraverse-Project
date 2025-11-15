"""
app.py - Streamlit UI

Run:
    streamlit run app.py
"""
import os
import tempfile
import streamlit as st
from classifier import classify_and_organize

st.set_page_config(page_title="Smart File Classifier", layout="wide")
st.title("Smart File Classifier")
st.markdown("Upload files and they'll be organized into `categorized_data/<FileType>/`")

uploaded = st.file_uploader("Upload files", accept_multiple_files=True)

base_dir = "categorized_data"
os.makedirs(base_dir, exist_ok=True)

if uploaded:
    progress = st.progress(0)
    total = len(uploaded)
    i = 0

    for u in uploaded:
        i += 1
        tmpdir = tempfile.gettempdir()
        tmp_path = os.path.join(tmpdir, u.name)

        # avoid filename collisions in temp folder
        if os.path.exists(tmp_path):
            name, ext = os.path.splitext(u.name)
            cnt = 1
            while os.path.exists(tmp_path):
                tmp_path = os.path.join(tmpdir, f"{name}_{cnt}{ext}")
                cnt += 1

        with open(tmp_path, "wb") as f:
            f.write(u.read())

        try:
            _, _, ftype, new_path = classify_and_organize(tmp_path, base_dir)
            st.success(f"**{u.name}** → Type: `{ftype}`")
            st.code(new_path)
        except Exception as e:
            st.error(f"Failed to process {u.name}: {e}")

        progress.progress(int(i / total * 100))

    st.balloons()
    st.info("Done — check categorized_data.")
