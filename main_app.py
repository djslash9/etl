import streamlit as st

st.set_page_config(page_title='Data Processing Studio', page_icon='🚀', layout='wide', initial_sidebar_state='expanded')

import fpk_t
import gt_t
import sw_t
import sp_t
st.markdown('\n<style>\n    /* Main Background and Text Defaults */\n    .stApp {\n        background-color: #f8f9fa;\n    }\n    \n    /* Navbar Container */\n    .nav-container {\n        display: flex;\n        justify-content: center;\n        background-color: #002b5c; /* Dark Blue */\n        padding: 1rem 0;\n        margin-bottom: 2rem;\n        border-radius: 0 0 10px 10px;\n        box-shadow: 0 4px 6px rgba(0,0,0,0.1);\n    }\n    \n    /* Navbar Buttons (simulated via columns in Streamlit, styled here for reference) */\n    div.stButton > button {\n        background-color: #002b5c;\n        color: white;\n        border: 1px solid rgba(255,255,255,0.2);\n        font-weight: 500;\n        border-radius: 5px;\n        transition: all 0.3s ease;\n    }\n    \n    div.stButton > button:hover {\n        background-color: #004080;\n        border-color: white;\n        transform: translateY(-2px);\n    }\n    \n    div.stButton > button:focus {\n        background-color: #004080;\n        color: white;\n        border-color: white;\n    }\n    \n    /* Active State Highlight (using conditional rendering in Python to add a border or color) */\n    \n    h1, h2, h3 {\n        color: #002b5c;\n    }\n    \n    /* Metric Cards */\n    div[data-testid="stMetricValue"] {\n        color: #002b5c;\n    }\n</style>\n', unsafe_allow_html=True)
if 'current_app' not in st.session_state:
    st.session_state.current_app = 'FPK Processor'
col1, col2, col3, col4 = st.columns(4)

def set_app(app_name):
    st.session_state.current_app = app_name
with col1:
    if st.button('📄 FPK Processor', use_container_width=True, type='primary' if st.session_state.current_app == 'FPK Processor' else 'secondary'):
        set_app('FPK Processor')
with col2:
    if st.button('📊 Google Trends', use_container_width=True, type='primary' if st.session_state.current_app == 'Google Trends' else 'secondary'):
        set_app('Google Trends')
with col3:
    if st.button('🌐 SimilarWeb', use_container_width=True, type='primary' if st.session_state.current_app == 'SimilarWeb' else 'secondary'):
        set_app('SimilarWeb')
with col4:
    if st.button('🧠 Sentiment', use_container_width=True, type='primary' if st.session_state.current_app == 'Sentiment' else 'secondary'):
        set_app('Sentiment')
st.markdown('---')
if st.session_state.current_app == 'FPK Processor':
    fpk_t.app()
elif st.session_state.current_app == 'Google Trends':
    gt_t.app()
elif st.session_state.current_app == 'SimilarWeb':
    sw_t.app()
elif st.session_state.current_app == 'Sentiment':
    sp_t.app()