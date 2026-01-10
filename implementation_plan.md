# Deployment Plan: Streamlit Cloud

## 1. Secure Credentials (Secrets)
Instead of encrypting `co.json`, we will use **Streamlit Secrets**. This is the standard, secure way to handle keys in Streamlit Cloud.
*   **Local**: Continue using `json/co.json` (ignored by Git).
*   **Cloud**: Use `st.secrets` to inject the JSON content securely.

## 2. Code Changes (`client_onboard_gs.py`)
*   Update `get_sheet()` to checks for `st.secrets.gcp_service_account`.
*   If found, use `.from_json_keyfile_dict()`.
*   If not found, fall back to `.from_json_keyfile_name("json/co.json")`.

## 3. Git Configuration
*   Create `.gitignore` to strictly exclude `json/co.json` and `logo.png` (if proprietary) or just the credentials.
*   **Wait**, user added `logo.png`. That should probably be committed if it's the app logo. `co.json` MUST be ignored.

## 4. Dependencies
*   Update `requirements.txt` to ensure `gspread`, `oauth2client`, `pandas`, `streamlit` are pinned.

## 5. User Instructions
*   How to set up the secret in Streamlit Cloud Dashboard.
