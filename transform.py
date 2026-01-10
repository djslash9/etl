import streamlit as st
from streamlit_navigation_bar import st_navbar
import sys
from fpk_t import fpk_page
from gt_t import gt_page
from sp_t import sp_page
st.set_page_config(page_title='Data Processor Suite', layout='wide', page_icon='📊', initial_sidebar_state='collapsed')

def hide_streamlit_ui():
    hide_menu_and_footer_css = '\n        <style>\n        #MainMenu {display: none;}\n        footer {display: none;}\n        [data-testid="stToolbar"] {display: none;}\n        \n        /* Hide the sidebar completely */\n        [data-testid="stSidebar"] {\n            display: none;\n        }\n        \n        /* Adjust main content to be full width since sidebar is gone */\n        [data-testid="stAppViewContainer"] > section {\n            padding-left: 1rem;\n            padding-right: 1rem;\n        }\n        </style>\n    '
    st.markdown(hide_menu_and_footer_css, unsafe_allow_html=True)
hide_streamlit_ui()
pages = ['Sentiment Analyzer', 'FPK File Processor', 'Google Trends Processor']
page = st_navbar(pages, options={'show_sidebar': False, 'show_menu': False})
if page == 'Sentiment Analyzer':
    sp_page()
elif page == 'FPK File Processor':
    fpk_page()
elif page == 'Google Trends Processor':
    gt_page()
else:
    sp_page()