# Google Sheets Integration Walkthrough

## 1. Requirements Checklist
You provided the following, which are now integrated:
*   [x] **JSON Service Account Key**: Located at `json/co.json`.
*   [x] **Google Sheet ID**: `1avuWNfqfLykbvgtGCP52hif9nF4TqXAm5Q21Im8thps`.
*   [x] **Permissions**: The Service Account email (inside `co.json`) must be an **Editor** on the Google Sheet.

## 2. Changes Made
I successfully migrated `client_onboard_gs.py` from SQLite to Google Sheets.

### Dependencies
Added `gspread` and `oauth2client` to `requirements.txt` and installed them.

### Codebase Refactoring
1.  **Imports**: Added `gspread` and `oauth2client`.
2.  **Configuration**:
    *   Set `SCOPE` to allow Google Drive and Sheets access.
    *   Set `CREDS_FILE` to `json/co.json`.
    *   Set `SHEET_ID` to your provided ID.
3.  **Database Logic Replaced**:
    *   `init_db()`: Now creates `Organizations`, `Brands`, and `Competitors` tabs in your Google Sheet if they don't exist.
    *   **Saving Data**: Instead of `INSERT INTO...`, the app now uses `worksheet.append_row()` and `worksheet.update_cell()`.
    *   **Loading Data**: Instead of `SELECT * FROM...`, the app uses `worksheet.get_all_records()` and processes the data using Pandas.
4.  **Export Logic**: The "Export Data" tab now fetches live data from Google Sheets, processes JSON fields, and generates the CSV.

## 3. How to Use
1.  **Run the App**:
    ```bash
    streamlit run client_onboard_gs.py
    ```
2.  **First Run**: The app will automatically generate the header rows in your Google Sheet tabs (`Organizations`, `Brands`, `Competitors`) if they are empty.
3.  **Verify**:
    *   Go to **New Client** -> Add an Organization (e.g., "Test Org").
    *   Check your valid Google Sheet; you should see "Test Org" in the **Organizations** tab immediately.
    *   Add a Brand and Competitor and verify they appear in their respective tabs.
    *   Go to **Manange / Edit** to verify you can edit names and details, and changes reflect in the Sheet.
    *   Go to **Export Data** to download the CSV generated from the Sheet data.

## 4. Troubleshooting
*   **"SpreadsheetNotFound"**: Ensure the Service Account email is added as an **Editor** to the Sheet ID `1avuWNfq...`.
*   **"APIError"**: If you hit quota limits, wait a minute. The current implementation fetches all records which is efficient for small-to-medium datasets.
