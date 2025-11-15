# app.py
import streamlit as st
import requests
import json
import re
from typing import Optional

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="File & JSON Manager", layout="wide")

# ---------------------------
# Helpers
# ---------------------------
def parse_content_disposition(cd: Optional[str]) -> Optional[str]:
    """
    Parse filename from Content-Disposition header if present.
    Example header: 'attachment; filename="dog.jpeg"'
    """
    if not cd:
        return None
    m = re.search(r'filename\*?=(?:UTF-8\'\')?\"?([^\";]+)\"?', cd)
    if m:
        return m.group(1).strip()
    return None

def api_post_upload_file(token: str, file_tuple):
    """
    file_tuple: (fieldname, (filename, bytes, content_type?))
    returns: requests.Response
    """
    headers = {"Authorization": token} if token else {}
    try:
        # requests wants files dict like {'file': ('name', b'bytes', 'mime')}
        files = {"file": file_tuple}
        return requests.post(f"{BACKEND}/upload", files=files, headers=headers, timeout=30)
    except Exception as e:
        raise

def api_post_upload_text_json(token: str, text_json: str):
    headers = {"Authorization": token} if token else {}
    data = {"text_json": text_json}
    return requests.post(f"{BACKEND}/upload", data=data, headers=headers, timeout=30)

def api_login(username: str, password: str):
    try:
        return requests.post(f"{BACKEND}/login", json={"username": username, "password": password}, timeout=10)
    except Exception:
        raise

def api_download(uuid_code: str, token: str):
    headers = {"Authorization": token} if token else {}
    return requests.get(f"{BACKEND}/download/{uuid_code}", headers=headers, stream=True, timeout=30)

# ---------------------------
# Session / Auth
# ---------------------------
if "token" not in st.session_state:
    st.session_state.token = None

st.title("📁 Secure File & JSON Manager")

if not st.session_state.token:
    st.subheader("🔐 Login")

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        try:
            r = api_login(username, password)
        except Exception as e:
            st.error(f"Could not reach backend: {e}")
        else:
            try:
                j = r.json()
            except Exception:
                st.error("Backend returned invalid response.")
            else:
                if r.status_code == 200 and j.get("success"):
                    st.session_state.token = j.get("token")
                    st.success("Logged in successfully.")
                    st.rerun()
                else:
                    st.error(j.get("error") or "Invalid credentials.")

    st.stop()

# logged in
st.sidebar.success("Logged in")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_rerun()

st.write("### Choose upload method")
col_file, col_json = st.columns(2)

# ---------------------------
# Column 1: Non-JSON file upload
# ---------------------------
with col_file:
    st.markdown("## 📤 Upload Normal File (Images/Videos/PDFs/Docs/Audio)")
    st.markdown(
        "<div style='border:1px solid #ddd;padding:12px;border-radius:8px;'>",
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Choose a non-JSON file (images, videos, pdf, etc.)",
        type=None,
        key="nonjson_uploader"
    )

    if uploaded_file:
        st.info(f"Selected file: {uploaded_file.name} — size: {uploaded_file.size} bytes")
        if st.button("Upload file"):
            try:
                # requests file tuple: (filename, filebytes)
                file_bytes = uploaded_file.read()
                resp = api_post_upload_file(st.session_state.token, (uploaded_file.name, file_bytes))
            except Exception as e:
                st.error(f"Upload failed: {e}")
            else:
                try:
                    res = resp.json()
                except Exception:
                    st.error("Backend returned an invalid/non-JSON response.")
                    st.write(resp.text)
                else:
                    # If backend identifies JSON (unexpected here) show warning
                    if res.get("type") in ("sql", "doc"):
                        st.error("Backend treated this as JSON data. Please use the JSON section.")
                        st.write("Reason:", res.get("reason"))
                    else:
                        # Expecting 'uuid' for file uploads
                        uuid_val = res.get("uuid")
                        if uuid_val:
                            st.success("File uploaded successfully.")
                            st.write("**File UUID:**")
                            st.code(uuid_val)
                            st.info(f"Detected as: **{res.get('type', 'unknown')}**")
                        else:
                            st.warning("Upload succeeded but server did not return a UUID.")
                            st.write(res)

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Column 2: JSON (file & text)
# ---------------------------
with col_json:
    st.markdown("## 📝 Upload JSON Data (file or paste)")
    st.markdown(
        "<div style='border:1px solid #ddd;padding:12px;border-radius:8px;'>",
        unsafe_allow_html=True
    )

    st.write("Option A — Upload a `.json` file:")
    uploaded_json_file = st.file_uploader("Choose a JSON file", type=["json"], key="json_file_uploader")

    if uploaded_json_file:
        st.info(f"Selected JSON file: {uploaded_json_file.name}")
        if st.button("Upload JSON file"):
            try:
                file_bytes = uploaded_json_file.read()
                # send as file to backend; backend will detect .json and handle accordingly
                resp = api_post_upload_file(st.session_state.token, (uploaded_json_file.name, file_bytes))
            except Exception as e:
                st.error(f"Upload failed: {e}")
            else:
                try:
                    res = resp.json()
                except Exception:
                    st.error("Backend returned invalid response.")
                    st.write(resp.text)
                else:
                    # For JSON flows backend returns type 'sql' or 'doc' and credentials
                    if res.get("type") in ("sql", "doc"):
                        st.success("JSON processed.")
                        # show credentials if provided
                        user = res.get("username")
                        pwd = res.get("password")
                        if user and pwd:
                            st.write("**Database credentials (store safely):**")
                            st.code(f"Username: {user}\nPassword: {pwd}")
                        else:
                            st.info("Backend did not return DB credentials. Response:")
                            st.write(res)
                        st.write("Reason:")
                        st.code(res.get("reason", "No reason provided"))
                    else:
                        # could be error or file-type
                        st.error("Server did not classify the upload as JSON DB. Response:")
                        st.write(res)

    st.write("---")
    st.write("Option B — Paste JSON text directly:")
    json_text = st.text_area("Paste JSON here", height=220, key="json_text_area")

    if st.button("Submit JSON text"):
        if not json_text.strip():
            st.error("Please paste JSON text before submitting.")
        else:
            # Validate JSON quickly
            try:
                parsed = json.loads(json_text)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
            else:
                try:
                    resp = api_post_upload_text_json(st.session_state.token, json_text)
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                else:
                    try:
                        res = resp.json()
                    except Exception:
                        st.error("Backend returned invalid response.")
                        st.write(resp.text)
                    else:
                        if res.get("type") in ("sql", "doc"):
                            st.success("JSON processed.")
                            user = res.get("username")
                            pwd = res.get("password")
                            if user and pwd:
                                st.write("**Database credentials (store safely):**")
                                st.code(f"Username: {user}\nPassword: {pwd}")
                            else:
                                st.info("Backend did not return DB credentials. Response:")
                                st.write(res)
                            st.write("Reason:")
                            st.code(res.get("reason", "No reason provided"))
                        else:
                            st.error("Server did not classify the text as JSON DB. Response:")
                            st.write(res)

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# DOWNLOAD SECTION (global)
# ---------------------------
st.write("---")
st.write("## 📥 Download File by UUID")

download_uuid = st.text_input("Enter file UUID to download", key="download_uuid_input")

if st.button("Download file"):
    if not download_uuid.strip():
        st.error("Please enter a UUID.")
    else:
        try:
            r = api_download(download_uuid.strip(), st.session_state.token)
        except Exception as e:
            st.error(f"Download failed: {e}")
        else:
            if r.status_code == 200:
                cd = r.headers.get("content-disposition", "")
                suggested_name = parse_content_disposition(cd) or download_uuid.strip()
                try:
                    content = r.content
                    st.download_button("Click to download", content, file_name=suggested_name)
                except Exception as e:
                    st.error(f"Could not prepare download: {e}")
            else:
                # try parse JSON error
                try:
                    err = r.json()
                    st.error(err.get("error", f"Download failed (status {r.status_code})"))
                except Exception:
                    st.error(f"Download failed (status {r.status_code}). Response text: {r.text}")
