# Client Onboarding Application Walkthrough

## Overview
This Streamlit application (`client_onboard_gs.py`) streamlines the process of onboarding new clients, managing their brand and competitor data, and exporting formatted datasets. It is backed by **Google Sheets** for collaborative data storage.

## Key Features

### 1. New Client Onboarding
*   **Organization Check**: Enter an organization name and click "Check Organization". The app intelligently checks if it already exists.
    *   **New**: If new, it guides you to create the Organization and its first Brand.
    *   **Existing**: If found, it lists existing brands and allows you to add a new Brand to that organization.
*   **Brand & Competitor Entry**:
    *   **Brand Form**: Includes Name, Website, Social Links, Google Trends, and Platform Access details (Meta, GA, etc.).
    *   **Competitor Form**: Simplified entry (Name, Website, Socials) for direct competitors.
*   **Validation**: Prevents submitting empty names or missing access details.

### 2. Manage / Edit Clients
*   **View & Edit**: Select an organization to view all its brands.
*   **Expandable Details**: Click on a Brand to expand/collapse its details and its competitors.
*   **Update**: Modify fields (e.g., add a LinkedIn URL) and save changes instantly to Google Sheets.
*   **Add New**: Easily add new Competitors to an existing Brand or new Brands to an existing Organization.

### 3. Export Data
*   **Flexible Selection**: Select an Organization, then choose one, multiple, or all Brands to export.
*   **Preview**: See a live table of the data before downloading.
*   **One-Click Download**: Generates a flattened CSV file containing all Brand and Competitor data, ready for analysis or import into other tools.

## Technical Highlights
*   **Google Sheets Integration**: Uses `gspread` for real-time CRUD operations.
*   **Smart Caching**: API calls are cached to prevent `429 Quota Exceeded` errors and ensure a snappy UI.
*   **Robust Error Handling**: includes retry logic and user-friendly error messages (e.g., for network timeouts).
*   **Responsive UI**: Features spinners/loaders, clear layouts, and collapsible sections for a clean experience.

## Usage
Run the app locally with:
```bash
streamlit run client_onboard_gs.py
```
Ensure you have your `json/co.json` credentials file in place.

## Deployment & Secrets (Streamlit Cloud)
To deploy this app securely:
1.  **Push to GitHub**: Upload all files *except* `json/` and `.csv` files.
2.  **Streamlit Cloud**: Connect your repository.
3.  **Secrets**: Go to App Settings > Secrets and paste your Google Credentials using the TOML format:
    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    ...
    ```
    (The app is compatible with both the raw credentials and the `[gcp_service_account]` header).
