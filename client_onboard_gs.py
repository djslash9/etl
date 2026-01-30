import streamlit as st
import pandas as pd
import json
import time
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
st.set_page_config(page_title='Client Onboarding Portal', page_icon='✨', layout='wide')
st.markdown('\n<style>\n    @import url(\'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap\');\n\n    html, body, [class*="css"] {\n        font-family: \'Plus Jakarta Sans\', sans-serif;\n    }\n\n    .block-container {\n        padding-top: 2rem;\n        padding-bottom: 5rem;\n    }\n\n    h1, h2, h3 {\n        font-weight: 700;\n        letter-spacing: -0.5px;\n    }\n    \n    .stCard {\n        background-color: #ffffff;\n        padding: 2rem;\n        border-radius: 16px;\n        box-shadow: 0 4px 20px rgba(0,0,0,0.05);\n        border: 1px solid #f0f0f0;\n        margin-bottom: 20px;\n    }\n\n    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {\n        border-radius: 12px;\n        border: 1px solid #e2e8f0;\n        padding: 12px;\n        font-size: 1rem;\n    }\n    \n    .streamlit-expanderHeader {\n        background-color: #f8fafc;\n        border-radius: 12px;\n        padding: 1rem;\n        font-weight: 600;\n        border: 1px solid #e2e8f0;\n    }\n\n    .info-box {\n        background: #eff6ff;\n        border: 1px solid #dbeafe;\n        color: #1e40af;\n        padding: 1rem;\n        border-radius: 12px;\n        margin-bottom: 1rem;\n    }\n\n    /* Hide Streamlit Cloud UI elements */\n    [data-testid="stToolbar"] {\n        display: none !important;\n    }\n    [data-testid="stDecoration"] {\n        display: none !important;\n    }\n    .stDeployButton {\n        visibility: hidden !important;\n        display: none !important;\n    }\n    div[data-testid="stStatusWidget"] {\n        visibility: hidden !important;\n        display: none !important;\n    }\n    #MainMenu {\n        visibility: hidden !important;\n        display: none !important;\n    }\n    footer {\n        visibility: hidden !important;\n        display: none !important;\n    }\n    header {\n        background: transparent !important;\n    }\n    /* Specific selector for Hosted with Streamlit */\n    .viewerBadge_container__1QSob {\n        display: none !important;\n    }\n    /* General footer catch-all */\n    [data-testid="stFooter"] {\n        display: none !important;\n    }\n\n</style>\n', unsafe_allow_html=True)
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'json/co.json'
CREDS_FILE = 'json/co.json'
try:
    SHEET_ID = st.secrets["sheet_id"]
except:
    SHEET_ID = '1avuWNfqfLykbvgtGCP52hif9nF4TqXAm5Q21Im8thps'
CONST_ORG_HEADERS = ['org_id', 'name', 'Created_User', 'Created_Date', 'Edited_User', 'Edited_Date']
CONST_USER_HEADERS = ['username', 'password', 'role']
CONST_BRAND_HEADERS = ['brand_id', 'org_id', 'name', 'Status', 'Updated_Date', 'Facebook_URL', 'Instagram_URL', 'Twitter_URL', 'Youtube_URL', 'TikTok_URL', 'LinkedIn_URL', 'Website_URL', 'Google_Trends', 'Social_Listening', 'Social_Listening_Keywords', 'Meta_Access', 'Meta_Access_Details', 'Meta_Ads_Access', 'Meta_Ads_Access_Details', 'GA_Access', 'GA_Access_Details', 'GAds_Access', 'GAds_Access_Details', 'LinkedIn_Access', 'LinkedIn_Access_Details', 'TikTok_Access', 'TikTok_Access_Details', 'Created_User', 'Created_Date', 'Edited_User', 'Edited_Date']
CONST_COMP_HEADERS = ['comp_id', 'brand_id', 'name', 'Facebook_URL', 'Instagram_URL', 'Twitter_URL', 'Youtube_URL', 'TikTok_URL', 'LinkedIn_URL', 'Website_URL']

CONST_DB_BUSY_MSG = "Database is busy right now, please try again shortly. Sorry for the inconvenience"
def with_retry(func):
    def wrapper(*args, **kwargs):
        attempts = 3
        for i in range(attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == attempts - 1:
                    st.error(f"Database connection error: {e}")
                    st.stop()
                time.sleep(2 * (i + 1))
    return wrapper
@st.cache_resource
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    if os.path.exists(CREDS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
            client = gspread.authorize(creds)
            return client.open_by_key(SHEET_ID)
        except Exception as e:
            print(f"Local auth failed: {e}")
    try:
        try:
            secrets = st.secrets
        except Exception:
            secrets = {}
        if "gcp_service_account" in secrets:
            try:
                creds_dict = dict(secrets["gcp_service_account"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                client = gspread.authorize(creds)
                return client.open_by_key(SHEET_ID)
            except Exception as e:
                st.error(f"Secrets Error (Nested): {e}")
                st.stop()
        elif "type" in secrets and secrets["type"] == "service_account":
            try:
                creds_dict = dict(secrets)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                client = gspread.authorize(creds)
                return client.open_by_key(SHEET_ID)
            except Exception as e:
                st.warning(CONST_DB_BUSY_MSG)
                st.stop()
    except Exception:
        pass
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        st.warning(CONST_DB_BUSY_MSG)
        st.stop()
@st.cache_resource
def init_db():
    sheet = get_sheet()
    try:
        ws_org = sheet.worksheet('Organizations')
        cur_headers = ws_org.row_values(1)
        if len(cur_headers) < len(CONST_ORG_HEADERS):
             missing = CONST_ORG_HEADERS[len(cur_headers):]
             start_col_idx = len(cur_headers) + 1
             ws_org.update('A1:F1', [CONST_ORG_HEADERS])
    except gspread.WorksheetNotFound:
        ws_org = sheet.add_worksheet(title='Organizations', rows=100, cols=20)
        ws_org.append_row(CONST_ORG_HEADERS)
    try:
        ws_brands = sheet.worksheet('Brands')
        cur_headers = ws_brands.row_values(1)
        if len(cur_headers) < len(CONST_BRAND_HEADERS):
             ws_brands.update('A1:AE1', [CONST_BRAND_HEADERS])
    except gspread.WorksheetNotFound:
        ws_brands = sheet.add_worksheet(title='Brands', rows=100, cols=35)
        ws_brands.append_row(CONST_BRAND_HEADERS)
    try:
        ws_comps = sheet.worksheet('Competitors')
        ws_comps.update(range_name='A1:J1', values=[CONST_COMP_HEADERS])
    except gspread.WorksheetNotFound:
        ws_comps = sheet.add_worksheet(title='Competitors', rows=100, cols=20)
        ws_comps.append_row(CONST_COMP_HEADERS)
    
    ensure_users_sheet(sheet)

def ensure_users_sheet(sheet):
    try:
        ws_users = sheet.worksheet('Users')
        cur_headers = ws_users.row_values(1)
        if len(cur_headers) < len(CONST_USER_HEADERS):
             ws_users.update('A1:C1', [CONST_USER_HEADERS])
    except gspread.WorksheetNotFound:
        ws_users = sheet.add_worksheet(title='Users', rows=100, cols=10)
        ws_users.append_row(CONST_USER_HEADERS)
        # Add default admin
        ws_users.append_row(['Sisira', '161277', 'Admin'])

def get_next_id(worksheet):
    try:
        col_values = worksheet.col_values(1)
        if len(col_values) > 1:
            ids = [int(x) for x in col_values[1:] if str(x).isdigit()]
            return max(ids) + 1 if ids else 1
        return 1
    except Exception:
        return 1
@with_retry
def check_org_exists(name):
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records(expected_headers=['org_id', 'name'])
    for r in records:
        r_id = r.get('org_id') or r.get('id')
        if str(r.get('name', '')).strip().lower() == name.strip().lower():
            return r_id
    return None
@with_retry
def check_brand_exists(org_id, brand_name):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    records = ws.get_all_records(expected_headers=CONST_BRAND_HEADERS)
    for r in records:
        r_org_id = r.get('org_id')
        r_brand_id = r.get('brand_id') or r.get('id')
        if str(r_org_id) == str(org_id) and str(r.get('name', '')).strip().lower() == brand_name.strip().lower():
            return r_brand_id
    return None
@with_retry
def get_org_brands(org_id):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    records = ws.get_all_records(expected_headers=CONST_BRAND_HEADERS)
    return [r for r in records if str(r.get('org_id')) == str(org_id)]
@with_retry
def get_org_name(org_id):
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records(expected_headers=['org_id', 'name'])
    for r in records:
        r_id = r.get('org_id') or r.get('id')
        if str(r_id) == str(org_id):
            return r['name']
    return 'Unknown'
@with_retry
def save_organization(name):
    user = st.session_state.get('username', 'Unknown')
    ts = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    existing_id = check_org_exists(name)
    if existing_id:
        return existing_id

    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    new_id = get_next_id(ws)
    ws.append_row([new_id, name, user, ts, user, ts])
    return new_id
    
def transform_brand_row(brand_id, org_id, data, current_row=None):
    soc = data.get('social_links', {})
    acc = data.get('access', {})
    
    user = st.session_state.get('username', 'Unknown')
    ts = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    created_user = user
    created_ts = ts
    
    if current_row:
        if len(current_row) >= 31:
             created_user = current_row[27]
             created_ts = current_row[28]
        elif len(current_row) >= 27:
             created_user = current_row[25]
             created_ts = current_row[26]
        
    return [
        brand_id, org_id, data.get('name', ''), 
        data.get('status', 'Pending'), data.get('updated_date', ''),
        soc.get('Facebook', ''), soc.get('Instagram', ''), soc.get('Twitter(X)', ''), soc.get('Youtube', ''), soc.get('TikTok', ''), soc.get('LinkedIn', ''), 
        data.get('website_url', ''), data.get('google_trends', ''), 
        data.get('social_listening', 'False'), data.get('social_listening_keywords', ''),
        acc.get('Meta_Access', 'No'), acc.get('Meta_Access_Details', ''), 
        acc.get('Meta_Ads_Access', 'No'), acc.get('Meta_Ads_Access_Details', ''), 
        acc.get('GA_Access', 'No'), acc.get('GA_Access_Details', ''), 
        acc.get('GAds_Access', 'No'), acc.get('GAds_Access_Details', ''), 
        acc.get('LinkedIn_Access', 'No'), acc.get('LinkedIn_Access_Details', ''), 
        acc.get('TikTok_Access', 'No'), acc.get('TikTok_Access_Details', ''),
        created_user, created_ts, user, ts
    ]
def transform_comp_row(comp_id, brand_id, data):
    soc = data.get('social_links', {})
    return [comp_id, brand_id, data.get('name', ''), soc.get('Facebook', ''), soc.get('Instagram', ''), soc.get('Twitter(X)', ''), soc.get('Youtube', ''), soc.get('TikTok', ''), soc.get('LinkedIn', ''), data.get('website_url', '')]
@with_retry
def save_brand(org_id, brand_data, existing_id=None):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    if not existing_id:
        existing_id = check_brand_exists(org_id, brand_data['name'])
    if existing_id:
        cell = ws.find(str(existing_id), in_column=1)
        if cell:
            current_vals = ws.row_values(cell.row)
            row_data = transform_brand_row(existing_id, org_id, brand_data, current_vals)
            cell_range = f'A{cell.row}:AE{cell.row}'
            ws.update(range_name=cell_range, values=[row_data])
            return existing_id
    else:
        new_id = get_next_id(ws)
        row_data = transform_brand_row(new_id, org_id, brand_data)
        ws.append_row(row_data)
        return new_id
@with_retry
def save_competitor(brand_id, comp_data, existing_id=None):
    sheet = get_sheet()
    ws = sheet.worksheet('Competitors')
    if existing_id:
        cell = ws.find(str(existing_id), in_column=1)
        if cell:
            row_data = transform_comp_row(existing_id, brand_id, comp_data)
            cell_range = f'A{cell.row}:J{cell.row}'
            ws.update(range_name=cell_range, values=[row_data])
    else:
        new_id = get_next_id(ws)
        row_data = transform_comp_row(new_id, brand_id, comp_data)
        ws.append_row(row_data)
def archive_full_context(flat_data_list):
    try:
        sheet = get_sheet()
        try:
            ws_archive = sheet.worksheet('Deleted_Records')
        except gspread.WorksheetNotFound:
             ws_archive = sheet.add_worksheet(title='Deleted_Records', rows=1000, cols=40)
             headers = ['Deleted_At', 'Deleted_By', 'Entity_Type', 'Org_ID', 'Org_Name', 'Brand_ID', 'Brand_Name', 'Competitor_ID', 'Competitor_Name', 'Details_JSON']
             ws_archive.append_row(headers)
        
        user = st.session_state.get('username', 'Unknown')
        role = st.session_state.get('role', 'Unknown')
        ts = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        rows_to_add = []
        for item in flat_data_list:
            row = [ts, f"{user} ({role})"] + item
            rows_to_add.append(row)
            
        if rows_to_add:
            ws_archive.append_rows(rows_to_add)
    except Exception as e:
        print(f"Archive failed: {e}")

@with_retry
def delete_org_record(org_id):
    sheet = get_sheet()
    ws_org = sheet.worksheet('Organizations')
    ws_brand = sheet.worksheet('Brands')
    ws_comp = sheet.worksheet('Competitors')
    
    cell = ws_org.find(str(org_id), in_column=1)
    if not cell:
        return False
        
    org_name = ws_org.cell(cell.row, 2).value
    
    to_archive = []
    
    to_archive.append(['Organization', org_id, org_name, '', '', '', '', ''])
    
    brands_to_delete = [] # list of (row_idx, brand_id, brand_name)
    all_brands = ws_brand.get_all_records(expected_headers=CONST_BRAND_HEADERS)
    
    brand_cells = ws_brand.findall(str(org_id), in_column=2)
    brand_rows_indices = sorted([c.row for c in brand_cells], reverse=True)
    
    for r_idx in brand_rows_indices:
        b_vals = ws_brand.row_values(r_idx)
        b_id = b_vals[0]
        b_name = b_vals[2]
        to_archive.append(['Brand', org_id, org_name, b_id, b_name, '', '', json.dumps(b_vals)])
        
        comp_cells = ws_comp.findall(str(b_id), in_column=2)
        comp_rows_indices = sorted([c.row for c in comp_cells], reverse=True)
        for cr_idx in comp_rows_indices:
             c_vals = ws_comp.row_values(cr_idx)
             c_id = c_vals[0]
             c_name = c_vals[2]
             to_archive.append(['Competitor', org_id, org_name, b_id, b_name, c_id, c_name, json.dumps(c_vals)])
             ws_comp.delete_rows(cr_idx)
             
        ws_brand.delete_rows(r_idx)
        
    archive_full_context(to_archive)
    
    ws_org.delete_rows(cell.row)
    return True

@with_retry
def delete_brand_record(brand_id):
    sheet = get_sheet()
    ws_brand = sheet.worksheet('Brands')
    ws_comp = sheet.worksheet('Competitors')
    
    cell = ws_brand.find(str(brand_id), in_column=1)
    if not cell:
        return False
        
    b_vals = ws_brand.row_values(cell.row)
    b_id = b_vals[0]
    org_id = b_vals[1]
    b_name = b_vals[2]
    org_name = get_org_name(org_id)
    
    to_archive = []
    to_archive.append(['Brand', org_id, org_name, b_id, b_name, '', '', json.dumps(b_vals)])
    
    comp_cells = ws_comp.findall(str(b_id), in_column=2)
    comp_rows_indices = sorted([c.row for c in comp_cells], reverse=True)
    for cr_idx in comp_rows_indices:
         c_vals = ws_comp.row_values(cr_idx)
         c_id = c_vals[0]
         c_name = c_vals[2]
         to_archive.append(['Competitor', org_id, org_name, b_id, b_name, c_id, c_name, json.dumps(c_vals)])
         ws_comp.delete_rows(cr_idx)
         
    archive_full_context(to_archive)
    ws_brand.delete_rows(cell.row)
    return True
@st.cache_data(ttl=60)
def get_all_organizations():
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records(expected_headers=CONST_ORG_HEADERS)
    return pd.DataFrame(records)
def row_to_brand_dict(row):
    def g(k):
        return row.get(k, '')
    return {
        'id': row['brand_id'], 
        'name': row['name'], 
        'status': g('Status') if g('Status') else 'Pending',
        'updated_date': g('Updated_Date'),
        'website_url': g('Website_URL'), 
        'google_trends': g('Google_Trends'), 
        'social_listening': g('Social_Listening'),
        'social_listening_keywords': g('Social_Listening_Keywords'),
        'social_links': {
            'Facebook': g('Facebook_URL'), 'Instagram': g('Instagram_URL'), 'Twitter(X)': g('Twitter_URL'), 
            'Youtube': g('Youtube_URL'), 'TikTok': g('TikTok_URL'), 'LinkedIn': g('LinkedIn_URL')
        }, 
        'access': {
            'Meta_Access': g('Meta_Access'), 'Meta_Access_Details': g('Meta_Access_Details'), 
            'Meta_Ads_Access': g('Meta_Ads_Access'), 'Meta_Ads_Access_Details': g('Meta_Ads_Access_Details'), 
            'GA_Access': g('GA_Access'), 'GA_Access_Details': g('GA_Access_Details'), 
            'GAds_Access': g('GAds_Access'), 'GAds_Access_Details': g('GAds_Access_Details'), 
            'LinkedIn_Access': g('LinkedIn_Access'), 'LinkedIn_Access_Details': g('LinkedIn_Access_Details'), 
            'TikTok_Access': g('TikTok_Access'), 'TikTok_Access_Details': g('TikTok_Access_Details')
        }
    }
def row_to_comp_dict(row):
    def g(k):
        return row.get(k, '')
    return {'id': row['comp_id'], 'name': row['name'], 'website_url': g('Website_URL'), 'social_links': {'Facebook': g('Facebook_URL'), 'Instagram': g('Instagram_URL'), 'Twitter(X)': g('Twitter_URL'), 'Youtube': g('Youtube_URL'), 'TikTok': g('TikTok_URL'), 'LinkedIn': g('LinkedIn_URL')}}
def get_full_brand_details(brand_id):
    sheet = get_sheet()
    ws_comps = sheet.worksheet('Competitors')
    all_comps = ws_comps.get_all_records()
    my_comps = [c for c in all_comps if str(c.get('brand_id')) == str(brand_id)]
    return [row_to_comp_dict(c) for c in my_comps]
def render_access_inputs(label_prefix, key_prefix, current_data=None, db_key_base=None):
    if current_data is None:
        current_data = {}
    st.markdown(f'**{label_prefix}**')
    col1, col2 = st.columns([1, 4])
    base_key = db_key_base if db_key_base else label_prefix.replace(' ', '_')
    key_access = f'{base_key}_Access'
    key_details = f'{base_key}_Access_Details'
    current_val = current_data.get(key_access, 'No')
    current_det = current_data.get(key_details, '')
    with col1:
        idx = 1 if current_val == 'Yes' else 0
        access_val = st.selectbox(f'Access', ['No', 'Yes'], index=idx, key=f'{key_prefix}_bool')
    with col2:
        details_val = st.text_input(f'Details', value=current_det, placeholder='Access given person or link. Type details', key=f'{key_prefix}_details')
        if access_val == 'Yes' and not details_val.strip():
            st.warning('⚠️ Details required')
    return {key_access: access_val, key_details: details_val}
def render_social_inputs(key_prefix, current_soc=None):
    if current_soc is None:
        current_soc = {}
    platforms = ['Facebook', 'Instagram', 'Twitter(X)', 'Youtube', 'TikTok', 'LinkedIn']
    links = {}
    cols = st.columns(3)
    for i, p in enumerate(platforms):
        with cols[i % 3]:
            val = current_soc.get(p, '')
            links[p] = st.text_input(p, value=val, placeholder=f'{p} URL', key=f'{key_prefix}_{p}')
    return links
def render_entity_form(prefix, default_data=None, is_brand=True, check_org_id=None):
    if not default_data:
        default_data = {}
    status_val = default_data.get('status', 'Pending')
    updated_date_val = default_data.get('updated_date', '')
    if is_brand:
        name_val = st.text_input("Brand Name", value=default_data.get('name', ''), key=f'{prefix}_name')
        if check_org_id and name_val:
            dup_id = check_brand_exists(check_org_id, name_val)
            if dup_id:
                st.warning(f"⚠️ Brand **'{name_val}'** already exists for this organization (ID: {dup_id}). Please go to **Manage / Edit** to update it.")
                return {'name': name_val, 'exists': True}
    else:
        name_val = st.text_input("Competitor Name", value=default_data.get('name', ''), key=f'{prefix}_name')
    st.markdown('##### 🔗 Social Media')
    def_soc = default_data.get('social_links')
    socials = render_social_inputs(f'{prefix}_soc', def_soc)
    st.markdown('##### 🌐 Website')
    website = st.text_input('Website URL(s)', value=default_data.get('website_url', ''), key=f'{prefix}_web')
    google_trends = ''
    access_data = {}
    social_listening = 'False'
    social_listening_keywords = ''
    if is_brand:
        st.markdown('##### 📈 Google Trends')
        google_trends = st.text_area('Google Trends URL/Details', value=default_data.get('google_trends', ''), key=f'{prefix}_gt', height=68)
        
        st.markdown('##### 👂 Social Listening')
        sl_val = default_data.get('social_listening', 'False')
        sl_bool = True if str(sl_val).lower() == 'true' else False
        sl_toggle = st.toggle("Social Listening", value=sl_bool, key=f'{prefix}_sl_tog')
        social_listening = str(sl_toggle)
        
        if sl_toggle:
            st.info("Insert keywords to listen seperated by comma")
            social_listening_keywords = st.text_area("Keywords", value=default_data.get('social_listening_keywords', ''), key=f'{prefix}_sl_kw', placeholder="Insert keywords to listen seperated by comma")

        st.markdown('##### 🔐 Platform Access')
        def_acc = default_data.get('access')
        platforms = ['Meta', 'Meta_Ads', 'GA', 'GAds', 'LinkedIn', 'TikTok']
        for p in platforms:
            label = p.replace('_', ' ')
            if p == 'GA': label = 'Google Analytics'
            if p == 'GAds': label = 'Google Ads'
            chunk = render_access_inputs(label, f'{prefix}_{p}', def_acc, db_key_base=p)
            access_data.update(chunk)
    return {
        'name': name_val,
        'social_links': socials, 'website_url': website, 'google_trends': google_trends, 
        'social_listening': social_listening, 'social_listening_keywords': social_listening_keywords,
        'access': access_data,
        'exists': False
    }
def validate_entity(data, is_brand=True, context_label=None):
    errors = []
    prefix = f"{context_label}: " if context_label else ""
    if not data['name']:
        errors.append(f'{prefix}Name is required.')
    if is_brand:
        acc = data['access']
        for key, val in acc.items():
            if key.endswith('_Access') and val == 'Yes':
                det_key = key + '_Details'
                det_val = acc.get(det_key, '')
                if not det_val.strip():
                    friendly_name = key.replace('_Access', '')
                    errors.append(f'{prefix}{friendly_name}: Details cannot be blank if Access is Yes.')
    return errors
def set_custom_style():
    pass
def main():
    try:
        init_db()
    except Exception as e:
        st.warning(CONST_DB_BUSY_MSG)
        return
    
    # Ensure local secrets.toml has auth structure (REMOVED - Users now in Sheet)
    # ensure_admin_exists() 
    set_custom_style()
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if not st.session_state['authenticated']:
        render_login()
        return
    role = st.session_state.get('role', 'User')
    try:
        st.sidebar.image('logo.png')
    except:
        st.sidebar.warning('Logo not found (logo.png)')
    st.sidebar.title(f'🚀 Onboarding')
    st.sidebar.caption(f"Logged in as: {st.session_state['username']} ({role})")
    menu_options = []
    if role == 'Admin':
        menu_options = ['New Client', 'Export Data', 'Manage / Edit', 'Status Manager', 'User Manager', 'Delete Org/ Brand']
    elif role == 'Editor':
        menu_options = ['Status Manager']
    elif role == 'User':
        menu_options = ['New Client', 'Export Data', 'Manage / Edit']
    else:
        menu_options = [] 
    page = st.sidebar.radio('Navigate', menu_options)
    st.sidebar.divider()
    if st.sidebar.button("Logout", key='logout_btn'):
        st.session_state['authenticated'] = False
        st.session_state['role'] = None
        st.session_state['username'] = None
        st.rerun()
    if page == 'New Client':
        render_new_client_flow()
    elif page == 'Export Data':
        render_export()
    elif page == 'Manage / Edit':
        render_manage_edit()
    elif page == 'Status Manager':
        render_status_page()
    elif page == 'User Manager':
        render_user_manager()
    elif page == 'Delete Org/ Brand':
        render_delete_page()


def check_login(username, password):
    try:
        sheet = get_sheet()
        ws = sheet.worksheet('Users')
        records = ws.get_all_records(expected_headers=CONST_USER_HEADERS)
        
        for r in records:
            if str(r.get('username', '')).strip().lower() == username.strip().lower():
                # In a real app, hash this. Here we compare plain text as per existing logic.
                if str(r.get('password', '')).strip() == str(password).strip():
                    return r.get('role', 'User')
        return None
    except Exception as e:
        # Fallback for safety or initial setup issues
        print(f"Login check failed: {e}")
        return None

def create_user(username, password, role):
    try:
        sheet = get_sheet()
        ws = sheet.worksheet('Users')
        records = ws.get_all_records(expected_headers=CONST_USER_HEADERS)
        
        # Check existence
        for r in records:
            if str(r.get('username', '')).strip().lower() == username.strip().lower():
                return False, "Username already exists."
        
        ws.append_row([username, password, role])
        return True, "User created successfully."
    except Exception as e:
        return False, f"Failed to create user: {e}"

def get_all_users():
    try:
        sheet = get_sheet()
        ws = sheet.worksheet('Users')
        records = ws.get_all_records(expected_headers=CONST_USER_HEADERS)
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame(columns=CONST_USER_HEADERS)
def render_login():
    st.markdown("## 🔐 Login")
    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            role = check_login(user, pwd)
            if role:
                st.session_state['authenticated'] = True
                st.session_state['role'] = role
                st.session_state['username'] = user
                st.success(f"Welcome {user} ({role})!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid Username or Password")
def render_delete_page():
    st.markdown('<h1>Delete Org / Brand</h1>', unsafe_allow_html=True)
    st.warning("⚠️ Deletion is permanent. Please double check IDs before proceeding.")
    with st.expander("🔍 Lookup IDs (Optional)", expanded=False):
        st.info("Select an Organization (and Brand) to find their IDs.")
        df_orgs = get_all_organizations()
        if not df_orgs.empty:
            sel_org = st.selectbox("Select Organization", [""] + df_orgs['name'].tolist(), key='del_lookup_org')
            if sel_org:
                org_row = df_orgs[df_orgs['name'] == sel_org].iloc[0]
                lu_org_id = org_row['org_id']
                st.code(f"{lu_org_id}", language="text")
                st.caption("Copy this Organization ID above if you want to delete it.")
                brands = get_org_brands(lu_org_id)
                if brands:
                    brand_names = [b['name'] for b in brands]
                    sel_brand = st.selectbox("Select Brand", [""] + brand_names, key='del_lookup_brand')
                    if sel_brand:
                        for b in brands:
                            if b['name'] == sel_brand:
                                lu_brand_id = b['brand_id'] or b['id']
                                st.code(f"{lu_brand_id}", language="text")
                                st.caption("Copy this Brand ID above if you want to delete it.")
                                break
                else:
                    st.warning("No brands found for this organization.")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        org_id_in = st.text_input("Organization ID", placeholder="Enter ID to delete Org").strip()
    with col2:
        brand_id_in = st.text_input("Brand ID", placeholder="Enter ID to delete Brand").strip()
    if st.button("Check for Deletion"):
        st.session_state['del_checked'] = True
        st.session_state['del_org_id'] = org_id_in
        st.session_state['del_brand_id'] = brand_id_in
    if st.session_state.get('del_checked'):
        d_org = st.session_state.get('del_org_id')
        d_brand = st.session_state.get('del_brand_id')
        found_something = False
        target_brand_name = None
        target_org_name_for_brand = None
        if d_brand:
            try:
                sheet = get_sheet()
                ws_brand = sheet.worksheet('Brands')
                cell = ws_brand.find(str(d_brand), in_column=1)
                if cell:
                    b_row = ws_brand.row_values(cell.row)
                    if len(b_row) > 2:
                        target_brand_name = b_row[2] 
                        linked_org_id = b_row[1]
                        target_org_name_for_brand = get_org_name(linked_org_id)
                    st.info(f"🏷️ **Brand Found**: '{target_brand_name}' (ID: {d_brand}) belonging to Org: '{target_org_name_for_brand}'")
                    found_something = True
                else:
                    st.error(f"❌ Brand ID {d_brand} not found.")
            except Exception as e:
                st.warning(CONST_DB_BUSY_MSG)
        target_org_name = None
        if d_org:
            try:
                target_org_name = get_org_name(d_org)
                if target_org_name != 'Unknown':
                    st.info(f"🏢 **Organization Found**: '{target_org_name}' (ID: {d_org})")
                    found_something = True
                else:
                    st.error(f"❌ Organization ID {d_org} not found.")
            except Exception as e:
                st.warning(CONST_DB_BUSY_MSG)
        if found_something:
            st.markdown("### confirm Deletion")
            st.write("Are you sure you want to delete the identified records above?")
            if st.button("🗑️ Permanent Delete", type="primary"):
                try:
                    success_msgs = []
                    if d_brand and target_brand_name:
                        if delete_brand_record(d_brand):
                            success_msgs.append(f"Brand '{target_brand_name}' (ID: {d_brand}) deleted.")
                    if d_org and target_org_name and target_org_name != 'Unknown':
                        if delete_org_record(d_org):
                            success_msgs.append(f"Organization '{target_org_name}' (ID: {d_org}) deleted.")
                    if success_msgs:
                        for m in success_msgs:
                            st.success(m)
                        
                        st.session_state['del_checked'] = False
                        st.session_state['del_org_id'] = ""
                        st.session_state['del_brand_id'] = ""
                        
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Deletion failed or records no longer exist.")
                except Exception as e:
                    st.warning(CONST_DB_BUSY_MSG)
def render_export():
    st.markdown('<h1>Export Data</h1>', unsafe_allow_html=True)
    df_orgs = get_all_organizations()
    if df_orgs.empty:
        st.info('No organizations found.')
        return
    selected_org_name = st.selectbox('Select Organization to Export', df_orgs['name'].tolist())
    if selected_org_name:
        org_row = df_orgs[df_orgs['name'] == selected_org_name].iloc[0]
        org_id = int(org_row['org_id'])
        st.subheader(f"Exporting data for {selected_org_name}")
        brands_data = get_org_brands(org_id)
        if not brands_data:
            st.info('No brands found for this organization.')
            return
        export_data = []
        for brand in brands_data:
            full_details = get_full_brand_details(brand['id'])
            brand_row = {
                'Organization Name': selected_org_name,
                'Organization ID': org_id,
                'Brand Name': brand['name'],
                'Brand ID': brand['id'],
                'Status': brand.get('status', 'Pending'),
                'Updated Date': brand.get('updated_date', ''),
            }
            for key, value in brand.items():
                if key.endswith('_Access') or key.endswith('_Details'):
                    brand_row[key] = value
            
            export_data.append(brand_row)
            
            for comp in full_details.get('competitors', []):
                comp_row = {
                    'Organization Name': selected_org_name,
                    'Organization ID': org_id,
                    'Brand Name': brand['name'],
                    'Brand ID': brand['id'],
                    'Competitor Name': comp['name'],
                    'Competitor ID': comp['id'],
                }
                for key, value in comp.items():
                    if key.endswith('_Access') or key.endswith('_Details'):
                        comp_row[key] = value
                export_data.append(comp_row)
        
        df_export = pd.DataFrame(export_data)
        st.dataframe(df_export, use_container_width=True)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f'export_{selected_org_name.replace(" ", "_")}.csv',
            mime='text/csv'
        )
    
    st.divider()
    st.subheader("🗑️ Export Deleted Records")
    if st.button("Fetch Deleted Records"):
        try:
            sheet = get_sheet()
            try:
                ws_del = sheet.worksheet('Deleted_Records')
                del_recs = ws_del.get_all_records()
                if del_recs:
                    df_del = pd.DataFrame(del_recs)
                    st.dataframe(df_del, use_container_width=True)
                    csv_del = df_del.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Deleted Records CSV",
                        data=csv_del,
                        file_name=f'deleted_records_archive.csv',
                        mime='text/csv'
                    )
                else:
                    st.info("No deleted records found.")
            except gspread.WorksheetNotFound:
                st.info("No deleted records archive found.")
        except Exception as e:
            st.error(f"Error fetching deleted records: {e}")

def render_user_manager():
    st.markdown('<h1>User Manager</h1>', unsafe_allow_html=True)
    with st.expander("➕ Add New User", expanded=True):
        with st.form("create_user_form"):
            new_user = st.text_input("Username").strip()
            new_pass = st.text_input("Password", type="password").strip()
            new_role = st.selectbox("Role", ["User", "Editor", "Admin"])
            if st.form_submit_button("Create User"):
                if new_user and new_pass:
                    ok, msg = create_user(new_user, new_pass, new_role)
                    if ok:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Username and Password are required.")
    st.divider()
    st.subheader("Existing Users")
    df_users = get_all_users()
    if not df_users.empty:
        display_df = df_users[['username', 'role']]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No users found.")
def render_new_client_flow():
    st.markdown('<h1>New Client Onboarding</h1>', unsafe_allow_html=True)
    org_name_input = st.text_input('🏢 Enter Organization Name', placeholder='e.g. Acme Corp')
    if 'last_input_org' not in st.session_state:
        st.session_state['last_input_org'] = ''
    if st.session_state['last_input_org'] != org_name_input:
        st.session_state['last_input_org'] = org_name_input
        for k in ['checked_org_id', 'checked_org_found', 'new_client_mode', 'target_org_id', 'target_org_name']:
            if k in st.session_state: del st.session_state[k]
    if st.button('Check Organization'):
        if not org_name_input:
            st.error('Please enter an organization name.')
            return
        with st.spinner('Checking organization...'):
            existing_id = check_org_exists(org_name_input)
            st.session_state['checked_org_id'] = existing_id
            st.session_state['checked_org_found'] = True
            if existing_id:
                st.session_state['new_client_mode'] = 'add_brand'
                st.session_state['target_org_id'] = existing_id
                st.session_state['target_org_name'] = org_name_input
            else:
                st.session_state['new_client_mode'] = 'new_org'
                st.session_state['target_org_name'] = org_name_input
    if st.session_state.get('checked_org_found'):
        existing_id = st.session_state.get('checked_org_id')
        if existing_id:
            st.info(f"✅ Organization **'{org_name_input}'** found (ID: {existing_id}).")
            brands = get_org_brands(existing_id)
            if brands:
                st.markdown('### Existing Brands:')
                for b in brands:
                    s_txt = b.get('Status', 'Pending')
                    d_txt = b.get('Updated_Date', '')
                    suffix = f" [{s_txt}" + (f" - {d_txt}" if d_txt else "") + "]"
                    st.write(f"- {b['name']}{suffix}")
                st.markdown('---')
            st.subheader(f'➕ Create New Brand for {org_name_input}')
        else:
            st.success(f"🆕 Creating New Organization: **'{org_name_input}'**")
            st.subheader(f'➕ Create First Brand')
    mode = st.session_state.get('new_client_mode')
    if mode == 'add_brand':
        render_brand_creation_form(st.session_state['target_org_id'], st.session_state['target_org_name'], is_new_org=False)
    elif mode == 'new_org':
        render_brand_creation_form(None, st.session_state['target_org_name'], is_new_org=True)
    st.markdown('---')
    if st.button('Reset Form'):
        for key in ['new_client_mode', 'target_org_id', 'target_org_name']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
def render_brand_creation_form(org_id, org_name, is_new_org=False):
    check_id = org_id if not is_new_org else None
    b_data = render_entity_form('new_brand', is_brand=True, check_org_id=check_id)
    if b_data.get('exists'):
        return
    st.markdown('### Competitors (Optional)')
    num_comps = st.number_input('Number of Competitors', 0, 10, 0)
    comps_payload = []
    for i in range(num_comps):
        st.markdown(f'**Competitor {i + 1}**')
        c_data = render_entity_form(f'new_comp_{i}', is_brand=False)
        comps_payload.append(c_data)
    if st.button('💾 Save Brand & Competitors'):
        errors = validate_entity(b_data, True, context_label="Brand")
        for i, c in enumerate(comps_payload):
            errors.extend(validate_entity(c, False, context_label=f"Competitor {i+1}"))
        if errors:
            for e in errors:
                st.error(e)
            return
        target_org_id = org_id
        if not is_new_org:
            dup_brand_id = check_brand_exists(target_org_id, b_data['name'])
            if dup_brand_id:
                st.error(f"Brand '{b_data['name']}' already exists for this organization (Brand ID: {dup_brand_id}). Please use Manage/Edit.")
                return
        try:
            with st.spinner('Saving data...'):
                if is_new_org:
                    target_org_id = save_organization(org_name)
                full_b_data = b_data.copy()
                full_b_data['status'] = 'Pending'
                full_b_data['updated_date'] = ''
                b_id = save_brand(target_org_id, full_b_data)
                for c_data in comps_payload:
                    save_competitor(b_id, c_data)
            st.success(f"Successfully saved Brand '{b_data['name']}' with {len(comps_payload)} competitors.")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.warning(CONST_DB_BUSY_MSG)
def render_status_page():
    st.markdown('<h1>Status Manager</h1>', unsafe_allow_html=True)
    df_orgs = get_all_organizations()
    if df_orgs.empty:
        st.info('No clients found.')
        return
    selected_org_name = st.selectbox('Select Organization', df_orgs['name'].tolist(), key='status_org_sel')
    if selected_org_name:
        org_row = df_orgs[df_orgs['name'] == selected_org_name].iloc[0]
        org_id = int(org_row['org_id'])
        with st.spinner('Loading brands...'):
            brand_rows = get_org_brands(org_id)
        if not brand_rows:
            st.warning('No brands found.')
            return
        st.markdown(f"### Update Status for **{selected_org_name}**")
        for b_row in brand_rows:
            b_data = row_to_brand_dict(b_row)
            b_id = b_data['id']
            b_name = b_data['name']
            curr_status = b_data.get('status', 'Pending')
            curr_date = b_data.get('updated_date', '')
            with st.container():
                st.markdown(f"#### {b_name}")
                new_status = st.selectbox("Status", ["Pending", "Updated Web App"], 
                                        index=0 if curr_status == "Pending" else 1, 
                                        key=f'st_stat_{b_id}')
                d_val = None
                if curr_date:
                    try: d_val = pd.to_datetime(curr_date).date()
                    except: pass
                if new_status == "Updated Web App" and curr_status != "Updated Web App":
                        d_val = pd.Timestamp.now().date()
                elif new_status == "Updated Web App" and not d_val:
                        d_val = pd.Timestamp.now().date()
                new_date = st.date_input("Updated Date", value=d_val, key=f'st_date_{b_id}')
                if st.button("Save Status & Date", key=f'save_stat_{b_id}'):
                    try:
                        updated_b_data = b_data.copy()
                        updated_b_data['status'] = new_status
                        updated_b_data['updated_date'] = new_date.strftime('%Y-%m-%d') if new_date else ''
                        save_brand(org_id, updated_b_data, existing_id=b_id)
                        st.toast(f"✅ Updated {b_name}!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.warning(CONST_DB_BUSY_MSG)
                st.divider()
                st.divider()
def render_manage_edit():
    st.markdown('<h1>Manage Clients</h1>', unsafe_allow_html=True)
    df_orgs = get_all_organizations()
    if df_orgs.empty:
        st.info('No clients found.')
        return
    selected_org_name = st.selectbox('Select Organization', df_orgs['name'].tolist())
    if selected_org_name:
        org_row = df_orgs[df_orgs['name'] == selected_org_name].iloc[0]
        org_id = int(org_row['org_id'])
        brand_rows = get_org_brands(org_id)
        if not brand_rows:
            st.info("No brands found.")
        else:
            st.markdown(f"### Brands for {selected_org_name}")
            for b_row in brand_rows:
                brand_dict = row_to_brand_dict(b_row)
                b_id = brand_dict['id']
                b_name = brand_dict['name']
                status_summ = brand_dict.get('status', 'Pending')
                date_summ = brand_dict.get('updated_date', '')
                summ_text = f" [{status_summ}" + (f" - {date_summ}" if date_summ else "") + "]"
                with st.expander(f'🏷️ Brand: {b_name}{summ_text}', expanded=False):
                    comps_list = get_full_brand_details(b_id)
                    st.markdown('### 📝 Edit Brand Details')
                    edited_brand = render_entity_form(f'edit_b_{b_id}', default_data=brand_dict, is_brand=True)
                    st.markdown('### ⚔️ Edit Competitors')
                    edited_comps_list = []
                    for c_dict in comps_list:
                        c_id = c_dict['id']
                        st.markdown(f"**Competitor: {c_dict['name']}**")
                        ec = render_entity_form(f'edit_c_{c_id}', default_data=c_dict, is_brand=False)
                        ec['id'] = c_id
                        edited_comps_list.append(ec)
                        st.divider()
                    if st.checkbox(f'Add New Competitor for {b_name}?', key=f'chk_new_c_{b_id}'):
                        new_c_data = render_entity_form(f'add_c_to_{b_id}', is_brand=False)
                        new_c_data['is_new'] = True
                        edited_comps_list.append(new_c_data)
                    if st.button(f'Update {selected_org_name} details for {b_name}', key=f'upd_btn_{b_id}'):
                        errors = validate_entity(edited_brand, True, context_label="Brand Details")
                        for i, ec in enumerate(edited_comps_list):
                            errors.extend(validate_entity(ec, False, context_label=f"Competitor {i+1}"))
                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            try:
                                with st.spinner('Updating details...'):
                                    edited_brand['status'] = brand_dict.get('status', 'Pending')
                                    edited_brand['updated_date'] = brand_dict.get('updated_date', '')
                                    save_brand(org_id, edited_brand, existing_id=b_id)
                                    for ec in edited_comps_list:
                                        if ec.get('is_new'):
                                            save_competitor(b_id, ec)
                                        else:
                                            save_competitor(b_id, ec, existing_id=ec['id'])
                                st.success('Updated successfully!')
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.warning(CONST_DB_BUSY_MSG)
                    st.markdown('---')
                    csv_data = generate_brand_csv(selected_org_name, edited_brand, edited_comps_list)
                    st.download_button('📥 Download CSV', csv_data, f'{selected_org_name}_{b_name}.csv', 'text/csv')
        st.markdown('---')
        with st.expander('➕ Add New Brand', expanded=False):
            render_brand_creation_form(org_id, selected_org_name, is_new_org=False)
@st.cache_data(ttl=60)
def get_all_competitors():
    sheet = get_sheet()
    ws = sheet.worksheet('Competitors')
    records = ws.get_all_records()
    return pd.DataFrame(records)
def generate_export_df(org_name, brands_data, comps_df):
    rows = []
    for brand in brands_data:
        b_row = brand.copy()
        b_row['Organization'] = org_name
        b_row['Type'] = 'Brand'
        b_row['Parent Brand'] = brand['name']
        b_row['Status'] = brand.get('status', 'Pending')
        b_row['Updated Date'] = brand.get('updated_date', '')
        socials = b_row.pop('social_links', {})
        access = b_row.pop('access', {})
        b_row.pop('status', None)
        b_row.pop('updated_date', None)
        combined = {**b_row, **socials, **access}
        rows.append(combined)
        b_id = brand['id']
        if not comps_df.empty:
            my_comps = comps_df[comps_df['brand_id'].astype(str) == str(b_id)]
            for _, comp_row in my_comps.iterrows():
                c_dict = row_to_comp_dict(comp_row)
                c_base = c_dict.copy()
                c_base['Organization'] = org_name
                c_base['Type'] = 'Competitor'
                c_base['Parent Brand'] = brand['name']
                c_soc = c_base.pop('social_links', {})
                c_base.pop('id', None)
                combined_c = {**c_base, **c_soc}
                rows.append(combined_c)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    priority = ['Organization', 'Type', 'Parent Brand', 'name', 'Status', 'Updated Date', 'website_url', 'google_trends', 'social_listening', 'social_listening_keywords']
    cols = [c for c in df.columns if c in priority] + [c for c in df.columns if c not in priority]
    params = []
    seen = set()
    for c in priority:
        if c in df.columns:
            params.append(c)
            seen.add(c)
    for c in df.columns:
        if c not in seen:
            params.append(c)
    return df[params]
def render_export():
    st.markdown('<h1>Export Data</h1>', unsafe_allow_html=True)
    orgs_df = get_all_organizations()
    if orgs_df.empty:
        st.info('No data available.')
        return
    org_names = orgs_df['name'].tolist()
    selected_org = st.selectbox('Select Organization', org_names)
    if selected_org:
        org_row = orgs_df[orgs_df['name'] == selected_org].iloc[0]
        org_id = int(org_row.get('org_id') or org_row.get('id'))
        with st.spinner('Fetching brands...'):
            brand_rows = get_org_brands(org_id)
        if not brand_rows:
            st.warning('No brands found for this organization.')
            return
        brands_list = [row_to_brand_dict(r) for r in brand_rows]
        brand_names = [b['name'] for b in brands_list]
        selected_brand_names = st.multiselect('Select Brands to Export', brand_names, default=brand_names)
        if selected_brand_names:
            selected_brands_data = [b for b in brands_list if b['name'] in selected_brand_names]
            with st.spinner('Fetching competitors...'):
                all_comps_df = get_all_competitors()
            df_export = generate_export_df(selected_org, selected_brands_data, all_comps_df)
            st.markdown('### 📊 Data Preview')
            st.dataframe(df_export)
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(label='📥 Download CSV', data=csv, file_name=f'{selected_org}_Export.csv', mime='text/csv', type='primary')
def generate_brand_csv(org_name, brand, comps_list_of_dicts):
    rows = []
    b_row = brand.copy()
    b_row['Organization'] = org_name
    b_row['Type'] = 'Brand'
    b_row['Parent Brand'] = brand['name']
    b_row['Status'] = brand.get('status', 'Pending')
    b_row['Updated Date'] = brand.get('updated_date', '')
    soc = b_row.pop('social_links', {})
    acc = b_row.pop('access', {})
    b_row.pop('status', None)
    b_row.pop('updated_date', None)
    rows.append({**b_row, **soc, **acc})
    for c in comps_list_of_dicts:
        c_row = c.copy()
        c_row['Organization'] = org_name
        c_row['Type'] = 'Competitor'
        c_row['Parent Brand'] = brand['name']
        c_soc = c_row.pop('social_links', {})
        c_row.pop('id', None)
        c_row.pop('is_new', None)
        rows.append({**c_row, **c_soc})
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode('utf-8')
if __name__ == '__main__':
    main()
