import streamlit as st
import pandas as pd
import easyocr
import numpy as np
import re
from io import BytesIO
from datetime import datetime, timedelta
st.markdown('\n<style>\n    .main {\n        background-color: #f5f5f5;\n    }\n    .stButton>button {\n        width: 100%;\n        border-radius: 8px;\n        height: 3em;\n        font-weight: bold;\n    }\n    .extract-btn>button {\n        background-color: #4CAF50;\n        color: white;\n    }\n    .clear-btn>button {\n        background-color: #f44336;\n        color: white;\n    }\n    .continue-btn>button {\n        background-color: #2196F3;\n        color: white;\n    }\n    /* Force primary buttons to be Blue */\n    div[data-testid="stButton"] > button[kind="primary"] {\n        background-color: #2196F3 !important;\n        border-color: #2196F3 !important;\n        color: white !important;\n    }\n    div[data-testid="stButton"] > button[kind="primary"]:hover {\n        background-color: #1976D2 !important;\n        border-color: #1976D2 !important;\n    }\n    h1, h2, h3 {\n        color: #333;\n    }\n    .footer {\n        position: fixed;\n        left: 0;\n        bottom: 0;\n        width: 100%;\n        background-color: #333;\n        color: white;\n        text-align: center;\n        padding: 10px;\n        font-size: 0.8em;\n    }\n</style>\n', unsafe_allow_html=True)

@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

def clean_value(x):
    if x is None or pd.isna(x):
        return 0
    if not isinstance(x, str):
        return x
    x = x.strip()
    if x.upper() in ['N/A', 'NIA', 'NAN', 'NONE', '', '-', 'NULL']:
        return 0
    if 'M' in x:
        try:
            return float(x.replace('M', '').replace(',', '')) * 1000000
        except:
            return 0
    if '%' in x:
        try:
            return float(x.replace('%', '').replace(',', '')) * 0.01
        except:
            return 0
    try:
        val_cleaned = x.replace(',', '')
        if '.' in val_cleaned:
            return float(val_cleaned)
        else:
            return int(val_cleaned)
    except:
        return 0

def normalize_website_name(website):
    website = website.replace('.', ' ')
    if 'Ik' in website and ' Ik' not in website:
        website = website.replace('Ik', ' Ik')
    return website.strip()

def clear_data_callback():
    st.session_state.df_engagement = None
    st.session_state.df_social = None
    st.session_state.df_channels = None
    st.session_state.uploader_key += 1
    if 'org_name' in st.session_state:
        st.session_state['org_name'] = ''
    if 'brand_name' in st.session_state:
        st.session_state['brand_name'] = ''

def continue_data_callback():
    st.session_state.df_engagement = None
    st.session_state.df_social = None
    st.session_state.df_channels = None
    st.session_state.uploader_key += 1

def extract_engagement(image_bytes, reader):
    results = reader.readtext(image_bytes)
    text_data = []
    for bbox, text, prob in results:
        tl, tr, br, bl = bbox
        y_center = (tl[1] + bl[1]) / 2
        x_center = (tl[0] + tr[0]) / 2
        text_data.append({'text': text, 'y': y_center, 'x': x_center, 'bbox': bbox})
    df_text = pd.DataFrame(text_data)
    if df_text.empty:
        return pd.DataFrame()
    df_text = df_text.sort_values(by='y')
    rows = []
    current_row = []
    last_y = -1
    y_tolerance = 15
    for index, row in df_text.iterrows():
        if last_y == -1 or abs(row['y'] - last_y) < y_tolerance:
            current_row.append(row)
            last_y = row['y']
        else:
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)
            current_row = [row]
            last_y = row['y']
    if current_row:
        current_row.sort(key=lambda x: x['x'])
        rows.append(current_row)
    header_row_index = -1
    for i, row in enumerate(rows):
        texts = [item['text'] for item in row]
        if 'Metric' in texts:
            header_row_index = i
            break
    if header_row_index != -1:
        header_texts = [item['text'] for item in rows[header_row_index]]
        data_start_idx = header_row_index + 1
        data_rows_captured = 0
        extracted_table = []
        extracted_table.append(header_texts)
        for i in range(data_start_idx, len(rows)):
            if data_rows_captured >= 7:
                break
            row_texts = [item['text'] for item in rows[i]]
            if len(row_texts) > 1 and 'Visits' in row_texts[0] and ('Unique' in row_texts[1]):
                row_texts[0] = row_texts[0] + ' / ' + row_texts[1]
                row_texts.pop(1)
            if len(row_texts) >= 2:
                extracted_table.append(row_texts)
                data_rows_captured += 1
        header = extracted_table[0]
        data = extracted_table[1:]
        normalized_data = []
        for r in data:
            if len(r) < len(header):
                r = r + [None] * (len(header) - len(r))
            elif len(r) > len(header):
                r = r[:len(header)]
            normalized_data.append(r)
        df = pd.DataFrame(normalized_data, columns=header)
        if 'Metric' in df.columns:
            df_engagement = df.set_index('Metric').T
        else:
            df_engagement = df.set_index(df.columns[0]).T
        df_engagement = df_engagement.map(clean_value)
        return df_engagement
    else:
        return pd.DataFrame()

def extract_social(image_bytes, reader):
    results = reader.readtext(image_bytes, mag_ratio=1.5)
    sn_text_data = []
    for bbox, text, prob in results:
        tl, tr, br, bl = bbox
        y_center = (tl[1] + bl[1]) / 2
        x_center = (tl[0] + tr[0]) / 2
        text = text.replace('<', '').strip()
        if re.match('^[\\d\\.]*9$', text) and len(text) > 1:
            text = text[:-1] + '%'
        sn_text_data.append({'text': text, 'y': y_center, 'x': x_center})
    df_sn_text = pd.DataFrame(sn_text_data)
    if df_sn_text.empty:
        return pd.DataFrame()
    df_sn_text = df_sn_text.sort_values(by='y')
    sn_rows = []
    sn_current_row = []
    sn_last_y = -1
    y_tolerance = 15
    for index, row in df_sn_text.iterrows():
        if sn_last_y == -1 or abs(row['y'] - sn_last_y) < y_tolerance:
            sn_current_row.append(row)
            sn_last_y = row['y']
        else:
            sn_current_row.sort(key=lambda x: x['x'])
            sn_rows.append(sn_current_row)
            sn_current_row = [row]
            sn_last_y = row['y']
    if sn_current_row:
        sn_current_row.sort(key=lambda x: x['x'])
        sn_rows.append(sn_current_row)
    sn_header_row_index = -1
    for i, row in enumerate(sn_rows):
        texts = [item['text'] for item in row]
        if any(('Network' in t for t in texts)):
            sn_header_row_index = i
            break
    if sn_header_row_index != -1:
        header_items = sn_rows[sn_header_row_index]
        sn_headers = [{'text': item['text'], 'x': item['x']} for item in header_items]
        sn_extracted_data = []
        count = 0
        for i in range(sn_header_row_index + 1, len(sn_rows)):
            if count >= 7:
                break
            row_items = sn_rows[i]
            if len(row_items) < 1:
                continue
            mapped_row = {h['text']: None for h in sn_headers}
            for item in row_items:
                closest_header = min(sn_headers, key=lambda h: abs(h['x'] - item['x']))
                if mapped_row[closest_header['text']] is not None:
                    mapped_row[closest_header['text']] += ' ' + item['text']
                else:
                    mapped_row[closest_header['text']] = item['text']
            sn_extracted_data.append(mapped_row)
            count += 1
        df_sn = pd.DataFrame(sn_extracted_data)
        df_sn = df_sn.fillna('0%')
        network_col = next((c for c in df_sn.columns if 'Network' in c), None)
        if network_col:
            df_social = df_sn.set_index(network_col).T
        else:
            df_social = df_sn.set_index(df_sn.columns[0]).T
        return df_social.map(clean_value)
    else:
        return pd.DataFrame()

def extract_channel(image_bytes, col_name, reader):
    results = reader.readtext(image_bytes, mag_ratio=1.5)
    c_text_data = []
    for bbox, text, prob in results:
        tl, tr, br, bl = bbox
        y_center = (tl[1] + bl[1]) / 2
        x_center = (tl[0] + tr[0]) / 2
        text = text.replace('<', '').strip()
        if re.match('^[\\d\\.]*9$', text) and len(text) > 1:
            text = text[:-1] + '%'
        c_text_data.append({'text': text, 'y': y_center, 'x': x_center})
    df_c = pd.DataFrame(c_text_data)
    if df_c.empty:
        return pd.DataFrame(columns=['Website', col_name])
    df_c = df_c.sort_values(by='y')
    c_rows = []
    c_current = []
    last_y = -1
    y_tolerance = 15
    for index, row in df_c.iterrows():
        if last_y == -1 or abs(row['y'] - last_y) < y_tolerance:
            c_current.append(row)
            last_y = row['y']
        else:
            c_current.sort(key=lambda x: x['x'])
            c_rows.append(c_current)
            c_current = [row]
            last_y = row['y']
    if c_current:
        c_current.sort(key=lambda x: x['x'])
        c_rows.append(c_current)
    extracted_data = []
    for row in c_rows:
        texts = [item['text'] for item in row]
        if len(texts) >= 2:
            website = ' '.join(texts[:-1])
            value = texts[-1]
            website = normalize_website_name(website)
            extracted_data.append({'Website': website, col_name: value})
    df_temp = pd.DataFrame(extracted_data)
    if not df_temp.empty:
        df_temp[col_name] = df_temp[col_name].apply(clean_value)
    return df_temp

def app():
    st.markdown('<h1 style="text-align: center; color: #002b5c;">🌐 SW Table Extractor</h1>', unsafe_allow_html=True)
    st.markdown('Extract data from SimilarWeb images and convert to CSV.')
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            org_name = st.text_input('Organization', placeholder='e.g. MyCompany', key='org_name')
        with col2:
            brand_name = st.text_input('Brand', placeholder='e.g. MyBrand', key='brand_name')
        with col3:
            today = datetime.today()
            next_month = today.replace(day=28) + timedelta(days=4)
            end_of_month = next_month - timedelta(days=next_month.day)
            selected_date = st.date_input('Select Date', value=end_of_month)
    if 'df_engagement' not in st.session_state:
        st.session_state.df_engagement = None
    if 'df_social' not in st.session_state:
        st.session_state.df_social = None
    if 'df_channels' not in st.session_state:
        st.session_state.df_channels = None
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0
    st.markdown('---')
    st.header('1. Upload Images')
    col_eng, col_soc = st.columns(2)
    with col_eng:
        st.subheader('Website Traffic Engagement')
        img_engagement = st.file_uploader("Upload 'Engagement' Image", type=['png', 'jpg', 'jpeg'], key=f'up_eng_{st.session_state.uploader_key}')
    with col_soc:
        st.subheader('Social Network Traffic')
        img_social = st.file_uploader("Upload 'Social Network' Image", type=['png', 'jpg', 'jpeg'], key=f'up_soc_{st.session_state.uploader_key}')
    st.subheader('Channel Traffic')
    st.markdown('Upload images for each channel type:')
    channel_types = ['direct', 'display', 'email', 'gen_ai', 'referrals', 'search_organic', 'search_paid', 'social_organic', 'social_paid']
    c_cols = st.columns(3)
    channel_uploads = {}
    for i, c_type in enumerate(channel_types):
        col = c_cols[i % 3]
        with col:
            channel_uploads[c_type] = st.file_uploader(f'Channel: {c_type}', type=['png', 'jpg', 'jpeg'], key=f'up_{c_type}_{st.session_state.uploader_key}')
    st.markdown('---')
    st.markdown('### 2. Extract Data')
    if st.button('Proceed Extracting Data', key='extract_data', help='Run OCR', type='primary'):
        if not org_name or not brand_name:
            st.error("⚠️ Please provide both 'Organization' and 'Brand' names to proceed.")
        elif not (img_engagement or img_social or any(channel_uploads.values())):
            st.warning('Please upload at least one image to proceed.')
        else:
            reader = load_reader()
            timestamp_str = selected_date.strftime('%Y%m%d')
            with st.spinner('Extracting data from images... This may take a moment.'):
                if img_engagement:
                    st.info('Processing Engagement Data...')
                    try:
                        eng_bytes = img_engagement.getvalue()
                        df_res = extract_engagement(eng_bytes, reader)
                        if df_res.empty:
                            st.error("Error: Could not find 'Metric' table in Engagement image.")
                        else:
                            df_res.insert(0, 'Organization', org_name)
                            df_res.insert(1, 'Brand', brand_name)
                            df_res.insert(2, 'Date', timestamp_str)
                            st.session_state.df_engagement = df_res
                    except Exception as e:
                        st.error(f'Error processing Engagement image: {e}')
                if img_social:
                    st.info('Processing Social Network Data...')
                    try:
                        soc_bytes = img_social.getvalue()
                        df_res = extract_social(soc_bytes, reader)
                        if df_res.empty:
                            st.error("Error: Could not find 'Network' table in Social image.")
                        else:
                            df_res = df_res.map(clean_value)
                            df_res.insert(0, 'Organization', org_name)
                            df_res.insert(1, 'Brand', brand_name)
                            df_res.insert(2, 'Date', timestamp_str)
                            st.session_state.df_social = df_res
                    except Exception as e:
                        st.error(f'Error processing Social Network image: {e}')
                if any(channel_uploads.values()):
                    st.info('Processing Channel Traffic Data...')
                    df_merged = pd.DataFrame()
                    for c_type, uploaded_file in channel_uploads.items():
                        if uploaded_file:
                            try:
                                c_bytes = uploaded_file.getvalue()
                                df_part = extract_channel(c_bytes, c_type, reader)
                                if not df_part.empty:
                                    if df_merged.empty:
                                        df_merged = df_part
                                    else:
                                        df_merged = pd.merge(df_merged, df_part, on='Website', how='outer')
                                else:
                                    st.warning(f'Warning: Could not extract data from {c_type} image.')
                            except Exception as e:
                                st.error(f'Error processing {c_type}: {e}')
                    if not df_merged.empty:
                        df_merged.insert(0, 'Organization', org_name)
                        df_merged.insert(1, 'Brand', brand_name)
                        df_merged.insert(2, 'Date', timestamp_str)
                    st.session_state.df_channels = df_merged
            st.success('Extraction Complete!')
    if st.session_state.df_engagement is not None or st.session_state.df_social is not None or st.session_state.df_channels is not None:
        st.markdown('---')
        st.header('3. Preview & Download')
        file_prefix = f"{org_name}_{brand_name}_{selected_date.strftime('%Y-%m-%d')}" if org_name and brand_name else f"data_{selected_date.strftime('%Y-%m-%d')}"
        if st.session_state.df_engagement is not None and (not st.session_state.df_engagement.empty):
            st.subheader('Engagement Data')
            st.dataframe(st.session_state.df_engagement)
            csv_eng = st.session_state.df_engagement.to_csv().encode('utf-8')
            st.download_button(label='Download Engagement CSV', data=csv_eng, file_name=f'{file_prefix}_engagement.csv', mime='text/csv')
        if st.session_state.df_social is not None and (not st.session_state.df_social.empty):
            st.subheader('Social Network Data')
            st.dataframe(st.session_state.df_social)
            csv_soc = st.session_state.df_social.to_csv().encode('utf-8')
            st.download_button(label='Download Social Network CSV', data=csv_soc, file_name=f'{file_prefix}_social.csv', mime='text/csv')
        if st.session_state.df_channels is not None and (not st.session_state.df_channels.empty):
            st.subheader('Channel Traffic Data')
            st.dataframe(st.session_state.df_channels)
            csv_chan = st.session_state.df_channels.to_csv(index=False).encode('utf-8')
            st.download_button(label='Download Channel Traffic CSV', data=csv_chan, file_name=f'{file_prefix}_channel_traffic.csv', mime='text/csv')
    st.markdown('---')
    col_clear, col_continue = st.columns([1, 1])
    with col_clear:
        st.button('Clear All Data', type='secondary', key='clear_all', on_click=clear_data_callback)
    with col_continue:
        st.button('Continue with Another Dataset', type='primary', key='continue_next', on_click=continue_data_callback)
    st.markdown('---')
    st.markdown("\n    <div style='text-align: center; color: #666; margin-top: 2rem; margin-bottom: 2rem;'>\n        <p>Created by @djslash9 | 2025</p>\n    </div>\n    ", unsafe_allow_html=True)