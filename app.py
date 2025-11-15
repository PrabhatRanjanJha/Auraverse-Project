import streamlit as st
import requests
import json

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="Secure File Manager", layout="wide")

# -----------------------
# Login session state
# -----------------------
if "token" not in st.session_state:
    st.session_state.token = None

st.title("Secure File Uploader / Downloader")

# -----------------------
# LOGIN PAGE
# -----------------------
if not st.session_state.token:
    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            r = requests.post(f"{BACKEND}/login", json={
                "username": username,
                "password": password
            })
        except:
            st.error("Backend not running!")
            st.stop()

        if r.status_code == 200 and r.json().get("success"):
            st.session_state.token = r.json()["token"]
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error(r.json().get("error", "Login failed"))

    st.stop()

# -----------------------
# MAIN APP (AFTER LOGIN)
# -----------------------
st.success("Logged in")

token_header = {"Authorization": st.session_state.token}

col1, col2 = st.columns(2)

# ------------------------------------------------
#  COLUMN 1 - NORMAL FILE UPLOAD (images/videos/pdf/txt/etc.)
# ------------------------------------------------
with col1:
    st.header("Upload a file")

    uploaded_file = st.file_uploader("Choose any file", accept_multiple_files=False)

    if uploaded_file:
        files = {
            "file": (uploaded_file.name, uploaded_file.read())
        }
        r = requests.post(f"{BACKEND}/upload", files=files, headers=token_header)

        if r.status_code == 200:
            res = r.json()
            st.success(f"Uploaded! UUID: {res['uuid']}")
            st.code(res["uuid"])
            st.write(f"Type detected: **{res['type']}**")
        else:
            st.error("Upload failed.")
            st.write(r.text)

# ------------------------------------------------
#  COLUMN 1 (B) - JSON FILE OR TEXT UPLOAD
# ------------------------------------------------
with col1:
    st.subheader("Upload JSON")

    json_file = st.file_uploader("Upload .json file", type=["json"])

    if json_file:
        files = {"file": (json_file.name, json_file.read())}
        r = requests.post(f"{BACKEND}/upload", files=files, headers=token_header)

        if r.status_code == 200:
            res = r.json()
            st.success(f"JSON processed. UUID: {res['uuid']}")
            st.code(res["uuid"])
            st.info(f"Identified as: **{res['type']}**")
            st.write("Reason:")
            st.write(res["reason"])
        else:
            st.error("JSON upload failed.")
            st.write(r.text)

# ------------------------------------------------
#  COLUMN 1 (C) - JSON TEXT AREA
# ------------------------------------------------
with col1:
    st.subheader("Paste JSON Text")

    json_text = st.text_area("Enter JSON here")

    if st.button("Submit JSON Text"):
        if json_text.strip():
            data = {"text_json": json_text}
            r = requests.post(f"{BACKEND}/upload", data=data, headers=token_header)

            if r.status_code == 200:
                res = r.json()
                st.success(f"JSON processed. UUID: {res['uuid']}")
                st.code(res["uuid"])
                st.info(f"Identified as: **{res['type']}**")
                st.write(res["reason"])
            else:
                st.error("Invalid JSON text.")
                st.write(r.text)

# ------------------------------------------------
#  COLUMN 2 - DOWNLOAD SECTION
# ------------------------------------------------
with col2:
    st.header("Download by UUID")

    uuid_inp = st.text_input("Enter UUID to download")

    if st.button("Download", key="download_button"):
        if uuid_inp.strip():
            url = f"{BACKEND}/download/{uuid_inp}"
            r = requests.get(url, headers=token_header)

            if r.status_code == 200:
                filename = (
                    r.headers.get("Content-Disposition", "")
                    .replace("attachment; filename=", "")
                    .strip('"')
                )

                st.download_button(
                    "Click to Download",
                    r.content,
                    file_name=filename
                )

            else:
                st.error("Download failed.")
                st.write(r.text)

# ------------------------------------------------
#  COLUMN 2 (B) - SHOW JSON DB
# ------------------------------------------------
with col2:
    st.subheader("Show JSON Database Content")

    uuid_show = st.text_input("UUID for viewing DB")

    if st.button("Show Database"):
        url = f"{BACKEND}/show_db/{uuid_show}"
        r = requests.get(url, headers=token_header)

        if r.status_code == 200:
            res = r.json()
            st.json(res)
        else:
            st.error("Error loading database")

# ------------------------------------------------
# LOGOUT BUTTON
# ------------------------------------------------
if st.button("Logout"):
    st.session_state.token = None
    st.rerun()
