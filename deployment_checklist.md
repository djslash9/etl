# GitHub Deployment Checklist

## ✅ Files to Upload
Push these files to your GitHub repository. They are safe and necessary for the app to run.

### 1. Application Code
*   `client_onboard_gs.py` (The main application)

### 2. Assets & Config
*   `logo.png` (Your sidebar logo)
*   `.streamlit/config.toml` (Contains the Light Theme settings)
*   `.gitignore` (Tells Git what *not* to upload)

### 3. Dependencies
*   `requirements.txt` (List of Python libraries for Streamlit Cloud to install)

---

## ⛔ Files to EXCLUDE (Do NOT Upload)
Ensure these are listed in your `.gitignore` and **never** pushed to GitHub.

*   ❌ `json/co.json` (Your Google Credentials - **High Security Risk**)
*   ❌ `json/` folder (unless empty)
*   ❌ `.env` (If you have one)
*   ❌ `*.csv` (Local data exports)
*   ❌ `__pycache__/`

## 🚀 Post-Upload Steps
1.  **Connect Repo**: Log in to Streamlit Cloud and select this repository.
2.  **Add Secrets**: Copy the content of `json/co.json` into the Streamlit Cloud "Secrets" area as `[gcp_service_account]`.
