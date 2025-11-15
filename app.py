"""
app.py - Streamlit frontend
"""

import streamlit as st
import requests

BACKEND_URL = "http://192.168.2.14:8000"

st.set_page_config(page_title="File Uploader", layout="centered")

# -------------------------------------
# Login system
# -------------------------------------
if "token" not in st.session_state:
    st.session_state.token = None

st.title("Secure File Manager")

if not st.session_state.token:
    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        r = requests.post(f"{BACKEND_URL}/login", json={
            "username": username,
            "password": password
        })

        if r.status_code == 200 and r.json().get("success"):
            st.session_state.token = r.json()["token"]
            st.success("Logged in!")
            st.rerun()
        else:
            st.error("Invalid credentials")

else:
    st.success("Logged in")
    st.write("### Upload File")

    uploaded = st.file_uploader("Choose file")

    if uploaded:
        files = {"file": (uploaded.name, uploaded.read())}
        headers = {"Authorization": st.session_state.token}

        r = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers)

        if r.status_code == 200:
            info = r.json()
            st.success(f"Uploaded! File ID: {info['file_id']}")
            st.code(info["file_id"])
        else:
            st.error("Error during upload")

    st.write("### Download File")
    fid = st.text_input("Enter File ID")

    if st.button("Download"):
        headers = {"Authorization": st.session_state.token}
        url = f"{BACKEND_URL}/download/{fid}"

        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            st.download_button("Download file", r.content, file_name=f"{fid}")
        else:
            st.error(f"Error: {r.json().get('error')}")
