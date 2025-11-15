"""
app.py - Streamlit frontend
"""

import streamlit as st
import requests

# <-- set this to your laptop backend URL (LAN address)
BACKEND_URL = "http://192.168.2.14:8000"

st.set_page_config(page_title="Secure File Manager", layout="centered")

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None

st.title("Secure File Manager")

# small CSS to avoid green validation box
hide_css = """
<style>
    .stTextInput > div > div > input:valid {
        box-shadow: none !important;
        border-color: #ced4da !important;
    }
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# ------------------ LOGIN ------------------
if not st.session_state.token:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            r = requests.post(f"{BACKEND_URL}/login", json={"username": username, "password": password}, timeout=10)
        except Exception as e:
            st.error(f"Failed to reach backend: {e}")
        else:
            if r.status_code == 200 and r.json().get("success"):
                st.session_state.token = r.json()["token"]
                st.session_state.username = username
                st.success("Logged in")
                st.rerun()
            else:
                msg = r.json().get("msg") if r.headers.get("Content-Type", "").startswith("application/json") else "Invalid credentials"
                st.error(msg)

# ------------------ MAIN ------------------
else:
    st.write(f"Logged in as **{st.session_state.username}**")
    st.button("Logout", on_click=lambda: (st.session_state.clear(), st.experimental_rerun()))

    st.write("## Upload a file")
    uploaded = st.file_uploader("Choose a file", type=None)

    if uploaded is not None:
        if st.button("Upload"):
            files = {"file": (uploaded.name, uploaded.read())}
            headers = {"Authorization": st.session_state.token}
            try:
                r = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers, timeout=60)
            except Exception as e:
                st.error(f"Upload failed: {e}")
            else:
                if r.status_code == 200:
                    j = r.json()
                    st.success("Upload successful")
                    st.write("File ID (save this to download later):")
                    st.code(j.get("file_id"))
                    st.write("File type detected:", j.get("file_type"))
                else:
                    try:
                        st.error(r.json().get("error", "Upload error"))
                    except:
                        st.error("Upload error")

    st.write("---")
    st.write("## Download by File ID")
    fid = st.text_input("Enter File ID to download")

    if st.button("Download"):
        if not fid:
            st.error("Enter a File ID")
        else:
            headers = {"Authorization": st.session_state.token}
            try:
                r = requests.get(f"{BACKEND_URL}/download/{fid}", headers=headers, stream=True, timeout=60)
            except Exception as e:
                st.error(f"Failed to reach backend: {e}")
            else:
                ct = r.headers.get("Content-Type", "")
                # If JSON -> error
                if ct.startswith("application/json"):
                    try:
                        st.error(r.json().get("error", "Error"))
                    except:
                        st.error("Download error")
                else:
                    # get filename from header or fallback to fid
                    cd = r.headers.get("Content-Disposition", "")
                    if "filename=" in cd:
                        fname = cd.split("filename=")[-1].strip().strip('"')
                    else:
                        # attempt to derive extension from content-type
                        fname = fid
                    # download via Streamlit
                    st.download_button(
                        label="Click to download file",
                        data=r.content,
                        file_name=fname,
                        mime=ct if ct else None
                    )
