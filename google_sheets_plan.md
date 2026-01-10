# Google Sheets Integration Plan

## Goal
Migrate the `client_onboard_gs.py` backend from a local SQLite database (`onboard_data.db`) to a Google Sheet. This will allow the data to be edited directly in the Google Sheet (acting as a CRUD interface) while the Streamlit app remains the front-end interface.

## 1. Requirements (Action Required from User)
Before we can proceed with the code changes, you need to set up the Google Sheets environment. Please provide the following:

### Step A: Google Cloud Setup
1.  **Create a Project** in the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Enable APIs**: Search for and enable **Google Sheets API** and **Google Drive API**.
3.  **Create a Service Account**:
    *   Go to **IAM & Admin** > **Service Accounts**.
    *   Create a new Service Account.
    *   Go to the **Keys** tab of the new account and create a new **JSON** key.
    *   **Download this JSON file** and rename it to something simple like `credentials.json` (or paste its contents to me so I can save it securely).

### Step B: Sheet Configuration
1.  **Create a new Google Sheet** in your browser.
2.  **Share the Sheet**: Click `Share` and paste the **email address** of the Service Account (found inside the JSON file, usually `...@project-id.iam.gserviceaccount.com`) as an **Editor**.
3.  **Get the Sheet ID**: Copy the long string from the URL between `/d/` and `/edit`.
    *   Example: `docs.google.com/spreadsheets/d/`**`1BxiMVs0XRA5nFMdKbBdB_...`**`/edit`

### Step C: Provide Info
Please share:
1.  The **JSON Key content** (or confirm you've placed it in the folder).
2.  The **Google Sheet ID**.

---

## 2. Steps of Changing (My Implementation Plan)
Once the requirements are met, here is how I will modify `client_onboard_gs.py`:

### Phase 1: Dependency Setup
*   Add `gspread` and `oauth2client` to `requirements.txt`.
*   Set up authentication using the provided JSON key.

### Phase 2: Schema Migration (Tabs)
Instead of SQL tables, we will use **Worksheets (Tabs)** in your Google Sheet to maintain the relationship structure:
1.  **Tab 1: `Organizations`** (Columns: `id`, `name`)
2.  **Tab 2: `Brands`** (Columns: `id`, `org_id`, `name`, `social_links`, `meta_access`, etc.)
3.  **Tab 3: `Competitors`** (Columns: `id`, `brand_id`, `name`, `social_links`, etc.)

*I will assume we want to keep the relational structure (IDs) to handle the hierarchy (Organization -> Brands -> Competitors) reliably, rather than a single flat sheet which makes renaming organizations difficult.*

### Phase 3: Code Refactoring
I will replace the `sqlite3` functions with `gspread` functions:

| Current SQL Function | New Google Sheet Logic |
| :--- | :--- |
| `init_db()` | Connect to Sheet, check if tabs depend exist, create headers if empty. |
| `save_organization()` | Append row to `Organizations` tab. |
| `get_org_details()` | Read all tabs into Pandas DataFrames and merge them logic-side. |
| `update_organization()` | Find row by ID in `Organizations` tab and update the cell. |
| `save_brand()` / `save_competitor()` | Append or Update rows in respective tabs. |

### Phase 4: UI Adjustments
*   The "Export" function will still work, but instead of querying SQL, it will just read from the Google Sheet tabs.
*   The App loading speed might be slightly slower than SQLite due to API calls, so I will add caching (`@st.cache_data`) where appropriate.
