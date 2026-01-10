import streamlit as st
import pandas as pd
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
st.set_page_config(page_title='Client Onboarding Portal', page_icon='✨', layout='wide')
st.markdown('\n<style>\n    @import url(\'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap\');\n\n    html, body, [class*="css"] {\n        font-family: \'Plus Jakarta Sans\', sans-serif;\n        color: #1a1a1a;\n    }\n\n    .block-container {\n        padding-top: 2rem;\n        padding-bottom: 5rem;\n    }\n\n    h1, h2, h3 {\n        font-weight: 700;\n        letter-spacing: -0.5px;\n    }\n    \n    h1 {\n        background: linear-gradient(120deg, #2563eb, #7c3aed);\n        -webkit-background-clip: text;\n        -webkit-text-fill-color: transparent;\n        font-size: 3rem !important;\n        padding-bottom: 1rem;\n    }\n\n    .stCard {\n        background-color: #ffffff;\n        padding: 2rem;\n        border-radius: 16px;\n        box-shadow: 0 4px 20px rgba(0,0,0,0.05);\n        border: 1px solid #f0f0f0;\n        margin-bottom: 20px;\n    }\n\n    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {\n        border-radius: 12px;\n        border: 1px solid #e2e8f0;\n        padding: 12px;\n        font-size: 1rem;\n    }\n    \n    .stButton button {\n        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);\n        color: white;\n        border: none;\n        padding: 0.75rem 2rem;\n        border-radius: 12px;\n        font-weight: 600;\n        letter-spacing: 0.5px;\n        transition: all 0.3s ease;\n        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);\n        width: 100%;\n    }\n    .stButton button:hover {\n        opacity: 0.9;\n        transform: translateY(-1px);\n        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.3);\n    }\n    \n    .streamlit-expanderHeader {\n        background-color: #f8fafc;\n        border-radius: 12px;\n        padding: 1rem;\n        font-weight: 600;\n        border: 1px solid #e2e8f0;\n    }\n\n    .info-box {\n        background: #eff6ff;\n        border: 1px solid #dbeafe;\n        color: #1e40af;\n        padding: 1rem;\n        border-radius: 12px;\n        margin-bottom: 1rem;\n    }\n\n</style>\n', unsafe_allow_html=True)
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'json/co.json'
SHEET_ID = '1avuWNfqfLykbvgtGCP52hif9nF4TqXAm5Q21Im8thps'
CONST_BRAND_HEADERS = ['brand_id', 'org_id', 'name', 'Facebook_URL', 'Instagram_URL', 'Twitter_URL', 'Youtube_URL', 'TikTok_URL', 'LinkedIn_URL', 'Website_URL', 'Google_Trends', 'Meta_Access', 'Meta_Access_Details', 'Meta_Ads_Access', 'Meta_Ads_Access_Details', 'GA_Access', 'GA_Access_Details', 'GAds_Access', 'GAds_Access_Details', 'LinkedIn_Access', 'LinkedIn_Access_Details', 'TikTok_Access', 'TikTok_Access_Details']
CONST_COMP_HEADERS = ['comp_id', 'brand_id', 'name', 'Facebook_URL', 'Instagram_URL', 'Twitter_URL', 'Youtube_URL', 'TikTok_URL', 'LinkedIn_URL', 'Website_URL']

@st.cache_resource
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets['gcp_service_account'])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open_by_key(SHEET_ID)
    except Exception:
        pass
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        st.error(f'Authentication Error: {e}. Please check permissions, secrets, or co.json.')
        st.stop()

@st.cache_resource
def init_db():
    sheet = get_sheet()
    try:
        ws_org = sheet.worksheet('Organizations')
        if len(ws_org.row_values(1)) < 2:
            ws_org.update('A1:B1', [['org_id', 'name']])
    except gspread.WorksheetNotFound:
        ws_org = sheet.add_worksheet(title='Organizations', rows=100, cols=20)
        ws_org.append_row(['org_id', 'name'])
    try:
        ws_brands = sheet.worksheet('Brands')
        ws_brands.update(range_name='A1:W1', values=[CONST_BRAND_HEADERS])
    except gspread.WorksheetNotFound:
        ws_brands = sheet.add_worksheet(title='Brands', rows=100, cols=26)
        ws_brands.append_row(CONST_BRAND_HEADERS)
    try:
        ws_comps = sheet.worksheet('Competitors')
        ws_comps.update(range_name='A1:J1', values=[CONST_COMP_HEADERS])
    except gspread.WorksheetNotFound:
        ws_comps = sheet.add_worksheet(title='Competitors', rows=100, cols=20)
        ws_comps.append_row(CONST_COMP_HEADERS)

def get_next_id(worksheet):
    try:
        col_values = worksheet.col_values(1)
        if len(col_values) > 1:
            ids = [int(x) for x in col_values[1:] if str(x).isdigit()]
            return max(ids) + 1 if ids else 1
        return 1
    except Exception:
        return 1

def check_org_exists(name):
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records()
    for r in records:
        r_id = r.get('org_id') or r.get('id')
        if str(r.get('name', '')).strip().lower() == name.strip().lower():
            return r_id
    return None

def check_brand_exists(org_id, brand_name):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    records = ws.get_all_records()
    for r in records:
        r_org_id = r.get('org_id')
        r_brand_id = r.get('brand_id') or r.get('id')
        if str(r_org_id) == str(org_id) and str(r.get('name', '')).strip().lower() == brand_name.strip().lower():
            return r_brand_id
    return None

def get_org_brands(org_id):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    records = ws.get_all_records()
    return [r for r in records if str(r.get('org_id')) == str(org_id)]

def get_org_name(org_id):
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records()
    for r in records:
        r_id = r.get('org_id') or r.get('id')
        if str(r_id) == str(org_id):
            return r['name']
    return 'Unknown'

def with_retry(func):

    def wrapper(*args, **kwargs):
        attempts = 3
        for i in range(attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == attempts - 1:
                    raise e
                time.sleep(2 * (i + 1))
    return wrapper

@with_retry
def save_organization(name):
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    new_id = get_next_id(ws)
    ws.append_row([new_id, name])
    return new_id

def transform_brand_row(brand_id, org_id, data):
    soc = data.get('social_links', {})
    acc = data.get('access', {})
    return [brand_id, org_id, data.get('name', ''), soc.get('Facebook', ''), soc.get('Instagram', ''), soc.get('Twitter(X)', ''), soc.get('Youtube', ''), soc.get('TikTok', ''), soc.get('LinkedIn', ''), data.get('website_url', ''), data.get('google_trends', ''), acc.get('Meta_Access', 'No'), acc.get('Meta_Access_Details', ''), acc.get('Meta_Ads_Access', 'No'), acc.get('Meta_Ads_Access_Details', ''), acc.get('GA_Access', 'No'), acc.get('GA_Access_Details', ''), acc.get('GAds_Access', 'No'), acc.get('GAds_Access_Details', ''), acc.get('LinkedIn_Access', 'No'), acc.get('LinkedIn_Access_Details', ''), acc.get('TikTok_Access', 'No'), acc.get('TikTok_Access_Details', '')]

def transform_comp_row(comp_id, brand_id, data):
    soc = data.get('social_links', {})
    return [comp_id, brand_id, data.get('name', ''), soc.get('Facebook', ''), soc.get('Instagram', ''), soc.get('Twitter(X)', ''), soc.get('Youtube', ''), soc.get('TikTok', ''), soc.get('LinkedIn', ''), data.get('website_url', '')]

@with_retry
def save_brand(org_id, brand_data, existing_id=None):
    sheet = get_sheet()
    ws = sheet.worksheet('Brands')
    if existing_id:
        cell = ws.find(str(existing_id), in_column=1)
        if cell:
            row_data = transform_brand_row(existing_id, org_id, brand_data)
            cell_range = f'A{cell.row}:W{cell.row}'
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

@st.cache_data(ttl=60)
def get_all_organizations():
    sheet = get_sheet()
    ws = sheet.worksheet('Organizations')
    records = ws.get_all_records()
    return pd.DataFrame(records)

def row_to_brand_dict(row):

    def g(k):
        return row.get(k, '')
    return {'id': row['brand_id'], 'name': row['name'], 'website_url': g('Website_URL'), 'google_trends': g('Google_Trends'), 'social_links': {'Facebook': g('Facebook_URL'), 'Instagram': g('Instagram_URL'), 'Twitter(X)': g('Twitter_URL'), 'Youtube': g('Youtube_URL'), 'TikTok': g('TikTok_URL'), 'LinkedIn': g('LinkedIn_URL')}, 'access': {'Meta_Access': g('Meta_Access'), 'Meta_Access_Details': g('Meta_Access_Details'), 'Meta_Ads_Access': g('Meta_Ads_Access'), 'Meta_Ads_Access_Details': g('Meta_Ads_Access_Details'), 'GA_Access': g('GA_Access'), 'GA_Access_Details': g('GA_Access_Details'), 'GAds_Access': g('GAds_Access'), 'GAds_Access_Details': g('GAds_Access_Details'), 'LinkedIn_Access': g('LinkedIn_Access'), 'LinkedIn_Access_Details': g('LinkedIn_Access_Details'), 'TikTok_Access': g('TikTok_Access'), 'TikTok_Access_Details': g('TikTok_Access_Details')}}

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

def render_access_inputs(label_prefix, key_prefix, current_data=None):
    if current_data is None:
        current_data = {}
    st.markdown(f'**{label_prefix}**')
    col1, col2 = st.columns([1, 4])
    key_access = f'{label_prefix}_Access'
    key_details = f'{label_prefix}_Access_Details'
    current_val = current_data.get(key_access, 'No')
    current_det = current_data.get(key_details, '')
    with col1:
        idx = 1 if current_val == 'Yes' else 0
        access_val = st.selectbox(f'Access', ['No', 'Yes'], index=idx, key=f'{key_prefix}_bool', label_visibility='collapsed')
    with col2:
        details_val = st.text_input(f'Details', value=current_det, placeholder='Required if Yes...', key=f'{key_prefix}_details', label_visibility='collapsed')
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

def render_entity_form(prefix, default_data=None, is_brand=True):
    name_val = st.text_input(f"{('Brand' if is_brand else 'Competitor')} Name", value=default_data.get('name', '') if default_data else '', key=f'{prefix}_name')
    st.markdown('##### 🔗 Social Media')
    def_soc = default_data.get('social_links') if default_data else None
    socials = render_social_inputs(f'{prefix}_soc', def_soc)
    st.markdown('##### 🌐 Website')
    website = st.text_input('Website URL(s)', value=default_data.get('website_url', '') if default_data else '', key=f'{prefix}_web')
    google_trends = ''
    access_data = {}
    if is_brand:
        st.markdown('##### 📈 Google Trends')
        google_trends = st.text_area('Google Trends URL/Details', value=default_data.get('google_trends', '') if default_data else '', key=f'{prefix}_gt', height=68)
        st.markdown('##### 🔐 Platform Access')
        def_acc = default_data.get('access') if default_data else None
        platforms = ['Meta', 'Meta_Ads', 'GA', 'GAds', 'LinkedIn', 'TikTok']
        for p in platforms:
            label = p.replace('_', ' ')
            if p == 'GA':
                label = 'Google Analytics'
            if p == 'GAds':
                label = 'Google Ads'
            chunk = render_access_inputs(label, f'{prefix}_{p}', def_acc)
            access_data.update(chunk)
    return {'name': name_val, 'social_links': socials, 'website_url': website, 'google_trends': google_trends, 'access': access_data}

def validate_entity(data, is_brand=True):
    errors = []
    if not data['name']:
        errors.append('Name is required.')
    if is_brand:
        acc = data['access']
        for key, val in acc.items():
            if key.endswith('_Access') and val == 'Yes':
                det_key = key + '_Details'
                det_val = acc.get(det_key, '')
                if not det_val.strip():
                    friendly_name = key.replace('_Access', '')
                    errors.append(f'{friendly_name}: Details cannot be blank if Access is Yes.')
    return errors

def set_custom_style():
    st.markdown('\n    <style>\n        /* Force Light Theme overrides */\n        [data-testid="stAppViewContainer"] {\n            background-color: #ffffff;\n        }\n        [data-testid="stSidebar"] {\n            background-color: #f7f9fc;\n        }\n        \n        /* GLOBAL BUTTON OVERRIDE */\n        button, \n        [data-testid="baseButton-secondary"], \n        [data-testid="baseButton-primary"] {\n            background-color: #f2f2f2 !important; \n            color: #000000 !important;\n            border: 1px solid #d9d9d9 !important;\n            border-radius: 6px !important;\n            font-weight: 400 !important;\n            box-shadow: none !important;\n        }\n        \n        button:hover,\n        [data-testid="baseButton-secondary"]:hover, \n        [data-testid="baseButton-primary"]:hover {\n            background-color: #e6e6e6 !important;\n            border-color: #b3b3b3 !important;\n            color: #000000 !important;\n        }\n\n        button:active, button:focus,\n        [data-testid="baseButton-secondary"]:active, \n        [data-testid="baseButton-secondary"]:focus,\n        [data-testid="baseButton-primary"]:active,\n        [data-testid="baseButton-primary"]:focus {\n            background-color: #cccccc !important;\n            color: #000000 !important;\n            border-color: #999999 !important;\n            box-shadow: none !important;\n        }\n    </style>\n    ', unsafe_allow_html=True)

def main():
    try:
        init_db()
    except Exception as e:
        st.error(f'Connection Error: {e}')
        return
    set_custom_style()
    try:
        st.sidebar.image('logo.png')
    except:
        st.sidebar.warning('Logo not found (logo.png)')
    st.sidebar.title('🚀 Onboarding')
    page = st.sidebar.radio('Navigate', ['New Client', 'Manage / Edit', 'Export Data'])
    if page == 'New Client':
        render_new_client_flow()
    elif page == 'Manage / Edit':
        render_manage_edit()
    elif page == 'Export Data':
        render_export()

def render_new_client_flow():
    st.markdown('<h1>New Client Onboarding</h1>', unsafe_allow_html=True)
    org_name_input = st.text_input('🏢 Enter Organization Name', placeholder='e.g. Acme Corp')
    if st.button('Check Organization'):
        if not org_name_input:
            st.error('Please enter an organization name.')
            return
        with st.spinner('Checking organization...'):
            existing_id = check_org_exists(org_name_input)
        if existing_id:
            st.info(f"✅ Organization **'{org_name_input}'** found (ID: {existing_id}).")
            brands = get_org_brands(existing_id)
            if brands:
                st.markdown('### Existing Brands:')
                for b in brands:
                    st.write(f"- {b['name']}")
                st.markdown('---')
            st.subheader(f'➕ Create New Brand for {org_name_input}')
            st.session_state['new_client_mode'] = 'add_brand'
            st.session_state['target_org_id'] = existing_id
            st.session_state['target_org_name'] = org_name_input
        else:
            st.success(f"🆕 Creating New Organization: **'{org_name_input}'**")
            st.subheader(f'➕ Create First Brand')
            st.session_state['new_client_mode'] = 'new_org'
            st.session_state['target_org_name'] = org_name_input
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
    b_data = render_entity_form('new_brand', is_brand=True)
    st.markdown('### Competitors (Optional)')
    num_comps = st.number_input('Number of Competitors', 0, 10, 0)
    comps_payload = []
    for i in range(num_comps):
        st.markdown(f'**Competitor {i + 1}**')
        c_data = render_entity_form(f'new_comp_{i}', is_brand=False)
        comps_payload.append(c_data)
    if st.button('💾 Save Brand & Competitors'):
        errors = validate_entity(b_data, True)
        for c in comps_payload:
            errors.extend(validate_entity(c, False))
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
                b_id = save_brand(target_org_id, b_data)
                for c_data in comps_payload:
                    save_competitor(b_id, c_data)
            st.success(f"Successfully saved Brand '{b_data['name']}' with {len(comps_payload)} competitors.")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f'Error saving: {e}')

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
        with st.expander('➕ Add New Brand', expanded=False):
            render_brand_creation_form(org_id, selected_org_name, is_new_org=False)
        st.markdown('---')
        for b_row in brand_rows:
            brand_dict = row_to_brand_dict(b_row)
            b_id = brand_dict['id']
            b_name = brand_dict['name']
            with st.expander(f'🏷️ Brand: {b_name}', expanded=False):
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
                    errors = validate_entity(edited_brand, True)
                    for ec in edited_comps_list:
                        errors.extend(validate_entity(ec, False))
                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        try:
                            with st.spinner('Updating details...'):
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
                            st.error(f'Update failed: {e}')
                st.markdown('---')
                csv_data = generate_brand_csv(selected_org_name, edited_brand, edited_comps_list)
                st.download_button('📥 Download CSV', csv_data, f'{selected_org_name}_{b_name}.csv', 'text/csv')

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
        socials = b_row.pop('social_links', {})
        access = b_row.pop('access', {})
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
    priority = ['Organization', 'Type', 'Parent Brand', 'name', 'website_url', 'google_trends']
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
    soc = b_row.pop('social_links', {})
    acc = b_row.pop('access', {})
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