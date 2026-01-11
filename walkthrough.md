# Walkthrough - Unified Streamlit App

I have combined the four Streamlit applications (`fpk_t`, `gt_t`, `sw_t`, `sp_t`) into a single unified application `main_app.py` with a shared navigation menu and a **Dark Blue** theme.

## Features
- **Unified Navigation**: A top-level navigation bar allows you to switch between the four tools instantly.
- **Dark Blue Theme**: The application uses a custom Dark Blue (`#002B5C`) styling for the header and buttons.
- **Modular Design**: Each individual app has been refactored into a module, allowing them to coexist within the same Streamlit session.

## How to Run
Run the main application using Streamlit:
```bash
streamlit run main_app.py
```

## Changes Made
- **Created [main_app.py](file:///g:/Python/ETL/main_app.py)**: The entry point that handles navigation and routing.
- **Refactored [fpk_t.py](file:///g:/Python/ETL/fpk_t.py)**: Removed `st.set_page_config` and wrapped logic in `app()`.
- **Refactored [gt_t.py](file:///g:/Python/ETL/gt_t.py)**: Removed `st.set_page_config` and wrapped logic in `app()`.
- **Refactored [sw_t.py](file:///g:/Python/ETL/sw_t.py)**: Removed `st.set_page_config` and wrapped logic in `app()`.
- **Refactored [sp_t.py](file:///g:/Python/ETL/sp_t.py)**: Removed `st.set_page_config` and wrapped logic in `app()`.

## Verification
1.  **Launch the App**: Run `streamlit run main_app.py`.
2.  **Navigation**: Click the buttons in the top navbar ("FPK Processor", "Google Trends", etc.).
3.  **Functionality**: Confirm that the respective tool loads below the navbar and functions as expected.
