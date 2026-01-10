import streamlit as st
import pandas as pd
import os
import glob
import datetime
import calendar

def hide_streamlit_ui():
    hide_menu_and_footer_css = '\n        <style>\n        #MainMenu {display: none;}\n        footer {display: none;}\n        [data-testid="stToolbar"] {display: none;}\n        </style>\n    '
    st.markdown(hide_menu_and_footer_css, unsafe_allow_html=True)
hide_streamlit_ui()
st.markdown('\n<style>\n    /* Hide sidebar, though layout changes should make it redundant */\n    section[data-testid="stSidebar"] {\n        display: none;\n    }\n    .main-header {\n        font-size: 3rem;\n        color: #1f77b4;\n        text-align: center;\n        margin-bottom: 2rem;\n        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);\n    }\n    .sub-header {\n        font-size: 1.5rem;\n        color: #ff7f0e;\n        margin: 1rem 0;\n        border-bottom: 2px solid #ff7f0e;\n        padding-bottom: 0.5rem;\n    }\n    .success-box {\n        padding: 1rem;\n        border-radius: 0.5rem;\n        background-color: #d4edda;\n        border: 1px solid #c3e6cb;\n        margin: 1rem 0;\n    }\n    .warning-box {\n        padding: 1rem;\n        border-radius: 0.5rem;\n        background-color: #fff3cd;\n        border: 1px solid #ffeaa7;\n        margin: 1rem 0;\n    }\n    .error-box {\n        padding: 1rem;\n        border-radius: 0.5rem;\n        background-color: #f8d7da;\n        border: 1px solid #f5c6cb;\n        margin: 1rem 0;\n    }\n    /* Style for primary button */\n    .stButton > button {\n        font-weight: bold;\n        transition: all 0.3s;\n    }\n    .stButton > button:hover {\n        transform: translateY(-2px);\n        box-shadow: 0 4px 8px rgba(0,0,0,0.2);\n    }\n</style>\n', unsafe_allow_html=True)

def app():
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = {}
    if 'file_date' not in st.session_state:
        today = datetime.date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        st.session_state.file_date = datetime.date(today.year, today.month, last_day)
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    def clear_files():
        st.session_state.uploader_key += 1
    st.markdown('<h1 style="text-align: center; color: #002b5c;">📊 Google Trends Data Processor</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-header" style="color: #1f77b4; border-color: #1f77b4;">🗂️ Step 1: Provide Inputs</h3>', unsafe_allow_html=True)
    st.date_input('File Date:', key='file_date', help='Select the date associated with these files.')
    st.markdown('---')
    col_header, col_clear = st.columns([3, 1])
    with col_header:
        st.markdown('<h3 class="sub-header" style="color: #1f77b4; border-color: #1f77b4; margin-top: 0;">📂 Upload Files</h3>', unsafe_allow_html=True)
    with col_clear:
        if st.button('🗑️ Clear All Files'):
            clear_files()
            st.rerun()
    col1, col2 = st.columns(2)
    key_suffix = str(st.session_state.uploader_key)
    with col1:
        st.session_state.web_timeline = st.file_uploader('1. Web Timeline CSV', type='csv', key=f'web_timeline_{key_suffix}')
        st.session_state.web_geomap_region = st.file_uploader('2. Web Geomap Region CSV', type='csv', key=f'web_geomap_region_{key_suffix}')
        st.session_state.web_geomap_city = st.file_uploader('3. Web Geomap City CSV', type='csv', key=f'web_geomap_city_{key_suffix}')
    with col2:
        st.session_state.youtube_timeline = st.file_uploader('4. Youtube Timeline CSV', type='csv', key=f'youtube_timeline_{key_suffix}')
        st.session_state.youtube_geomap_region = st.file_uploader('5. Youtube Geomap Region CSV', type='csv', key=f'youtube_geomap_region_{key_suffix}')
        st.session_state.youtube_geomap_city = st.file_uploader('6. Youtube Geomap City CSV', type='csv', key=f'youtube_geomap_city_{key_suffix}')
    st.markdown('---')
    process_button = st.button('🚀 Process All Data', use_container_width=True, type='primary')

    def process_timeline_file(file, platform_name, file_date):
        if file is None:
            return None
        try:
            df = pd.read_csv(file, skiprows=2)
            df.columns = [col.replace(': (Sri Lanka)', '') for col in df.columns]
            df['Platform'] = platform_name
            df['Date'] = file_date
            return df
        except Exception as e:
            st.error(f'Error processing {file.name}: {e}')
            return None

    def process_geomap_file(file, platform_name, file_date, breakdown_type):
        if file is None:
            return None
        try:
            df = pd.read_csv(file, skiprows=2)
            if df.columns[0].lower() != breakdown_type.lower():
                st.warning(f'File {file.name} does not appear to be {breakdown_type} data. Skipping.')
                return None
            df.columns = [col.split(':')[0] for col in df.columns]
            df['Breakdown'] = breakdown_type
            df['Platform'] = platform_name
            df['Date'] = file_date
            return df
        except Exception as e:
            st.error(f'Error processing {file.name}: {e}')
            return None
    if process_button:
        any_file_uploaded = st.session_state.web_timeline or st.session_state.web_geomap_region or st.session_state.web_geomap_city or st.session_state.youtube_timeline or st.session_state.youtube_geomap_region or st.session_state.youtube_geomap_city
        if not st.session_state.file_date:
            st.markdown('<div class="error-box"><strong>❌ Please select a File Date.</strong></div>', unsafe_allow_html=True)
        elif not any_file_uploaded:
            st.markdown('<div class="error-box"><strong>❌ Please upload at least one CSV file.</strong></div>', unsafe_allow_html=True)
        else:
            with st.spinner('Processing all data...'):
                try:
                    st.session_state.processed_data = {}
                    file_date = st.session_state.file_date
                    df_web_timeline = process_timeline_file(st.session_state.web_timeline, 'Web', file_date)
                    df_youtube_timeline = process_timeline_file(st.session_state.youtube_timeline, 'Youtube', file_date)
                    timeline_dfs = [df for df in [df_web_timeline, df_youtube_timeline] if df is not None]
                    if timeline_dfs:
                        df_timeline_merged = pd.concat(timeline_dfs, ignore_index=True)
                        st.session_state.processed_data['timeline'] = df_timeline_merged
                    df_web_region = process_geomap_file(st.session_state.web_geomap_region, 'Web', file_date, 'Region')
                    df_youtube_region = process_geomap_file(st.session_state.youtube_geomap_region, 'Youtube', file_date, 'Region')
                    region_dfs = [df for df in [df_web_region, df_youtube_region] if df is not None]
                    if region_dfs:
                        df_region_merged = pd.concat(region_dfs, ignore_index=True)
                        st.session_state.processed_data['region'] = df_region_merged
                    df_web_city = process_geomap_file(st.session_state.web_geomap_city, 'Web', file_date, 'City')
                    df_youtube_city = process_geomap_file(st.session_state.youtube_geomap_city, 'Youtube', file_date, 'City')
                    city_dfs = [df for df in [df_web_city, df_youtube_city] if df is not None]
                    if city_dfs:
                        df_city_merged = pd.concat(city_dfs, ignore_index=True)
                        st.session_state.processed_data['city'] = df_city_merged
                    st.markdown('<div class="success-box"><strong>✅ Data processed successfully! View results below.</strong></div>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="error-box"><strong>Error during processing: {e}</strong></div>', unsafe_allow_html=True)
    st.markdown('---')
    st.markdown('<h3 class="sub-header" style="color: #ff7f0e; border-color: #ff7f0e;">💾 Step 2: View & Download Results</h3>', unsafe_allow_html=True)
    if not st.session_state.processed_data:
        st.markdown('\n        <div class="warning-box">\n            <h3>👋 Welcome!</h3>\n            <p>Your processed data previews and download links will appear here after processing.</p>\n            <p>Please use <strong>Step 1</strong> above to upload your files and click <strong>"Process All Data"</strong>.</p>\n        </div>\n        ', unsafe_allow_html=True)
    else:
        date_suffix = st.session_state.file_date.strftime('%Y%m%d')
        tab1, tab2, tab3 = st.tabs(['🕒 Timeline', '🗺️ Region', '🏙️ City'])
        with tab1:
            if 'timeline' in st.session_state.processed_data:
                st.markdown('<h3 class="sub-header">Merged Timeline Data</h3>', unsafe_allow_html=True)
                st.download_button(label='Download Timeline CSV', data=st.session_state.processed_data['timeline'].to_csv(index=False).encode('utf-8'), file_name=f'gt_timeline_{date_suffix}.csv', mime='text/csv', use_container_width=True)
                st.dataframe(st.session_state.processed_data['timeline'].head(), use_container_width=True)
                st.write(f"Total rows: {st.session_state.processed_data['timeline'].shape[0]}")
            else:
                st.warning('No Timeline data was processed.')
        with tab2:
            if 'region' in st.session_state.processed_data:
                st.markdown('<h3 class="sub-header">Merged GeoMap Region Data</h3>', unsafe_allow_html=True)
                st.download_button(label='Download Region CSV', data=st.session_state.processed_data['region'].to_csv(index=False).encode('utf-8'), file_name=f'gt_geomap_region_{date_suffix}.csv', mime='text/csv', use_container_width=True)
                st.dataframe(st.session_state.processed_data['region'].head(), use_container_width=True)
                st.write(f"Total rows: {st.session_state.processed_data['region'].shape[0]}")
            else:
                st.warning('No Region data was processed.')
        with tab3:
            if 'city' in st.session_state.processed_data:
                st.markdown('<h3 class="sub-header">Merged GeoMap City Data</h3>', unsafe_allow_html=True)
                st.download_button(label='Download City CSV', data=st.session_state.processed_data['city'].to_csv(index=False).encode('utf-8'), file_name=f'gt_geomap_city_{date_suffix}.csv', mime='text/csv', use_container_width=True)
                st.dataframe(st.session_state.processed_data['city'].head(), use_container_width=True)
                st.write(f"Total rows: {st.session_state.processed_data['city'].shape[0]}")
            else:
                st.warning('No City data was processed.')
    st.markdown('---')
    st.markdown("\n        <div style='text-align: center; color: #666; margin-top: 2rem; margin-bottom: 2rem;'>\n            <p>Created by @djslash9 | 2025</p>\n        </div>\n        ", unsafe_allow_html=True)