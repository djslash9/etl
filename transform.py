import streamlit as st
from streamlit_navigation_bar import st_navbar # Import the new navigation bar
import sys

# Import the page-rendering functions from your app files
from fpk_t import fpk_page
from gt_t import gt_page
from sp_t import sp_page

# --- Streamlit App Configuration (Called ONCE) ---
st.set_page_config(
    page_title="Data Processor Suite",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed" # Collapse sidebar by default
)

# --- Hide UI Function (Defined ONCE) ---
def hide_streamlit_ui():
    """
    Hides the default Streamlit "Made with Streamlit" footer, the main menu,
    and the top-right toolbar.
    """
    hide_menu_and_footer_css = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        [data-testid="stToolbar"] {display: none;}
        
        /* Hide the sidebar completely */
        [data-testid="stSidebar"] {
            display: none;
        }
        
        /* Adjust main content to be full width since sidebar is gone */
        [data-testid="stAppViewContainer"] > section {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        </style>
    """
    st.markdown(hide_menu_and_footer_css, unsafe_allow_html=True)

# Call the hide UI function
hide_streamlit_ui()

# --- Main App Navigation ---
# Use st_navbar for horizontal navigation.
# This returns the string of the selected page.
pages = ["Sentiment Analyzer", "FPK File Processor", "Google Trends Processor"]
page = st_navbar(
    pages,
    options={
        "show_sidebar": False,
        "show_menu": False,
    }
)

# --- Page Routing ---
# Based on the 'page' returned by st_navbar, call the correct function.
if page == "Sentiment Analyzer":
    sp_page()
elif page == "FPK File Processor":
    fpk_page()
elif page == "Google Trends Processor":
    gt_page()
else:
    # Default page
    sp_page()