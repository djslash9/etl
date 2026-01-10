import streamlit as st
import sqlite3
import pandas as pd
import json
import base64
import time
st.set_page_config(page_title='Client Onboarding Portal', page_icon='✨', layout='wide')
st.markdown('\n<style>\n    @import url(\'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap\');\n\n    html, body, [class*="css"] {\n        font-family: \'Plus Jakarta Sans\', sans-serif;\n        color: #1a1a1a;\n    }\n\n    /* Main Container Styling */\n    .block-container {\n        padding-top: 2rem;\n        padding-bottom: 5rem;\n    }\n\n    /* Headers */\n    h1, h2, h3 {\n        font-weight: 700;\n        letter-spacing: -0.5px;\n    }\n    \n    h1 {\n        background: linear-gradient(120deg, #2563eb, #7c3aed);\n        -webkit-background-clip: text;\n        -webkit-text-fill-color: transparent;\n        font-size: 3rem !important;\n        padding-bottom: 1rem;\n    }\n\n    /* Cards */\n    .stCard {\n        background-color: #ffffff;\n        padding: 2rem;\n        border-radius: 16px;\n        box-shadow: 0 4px 20px rgba(0,0,0,0.05);\n        border: 1px solid #f0f0f0;\n        margin-bottom: 20px;\n        transition: transform 0.2s ease;\n    }\n    .stCard:hover {\n        transform: translateY(-2px);\n        box-shadow: 0 8px 30px rgba(0,0,0,0.08);\n    }\n\n    /* Inputs */\n    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {\n        border-radius: 12px;\n        border: 1px solid #e2e8f0;\n        padding: 12px;\n        font-size: 1rem;\n    }\n    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus {\n        border-color: #6366f1;\n        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);\n    }\n\n    /* Buttons */\n    .stButton button {\n        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);\n        color: white;\n        border: none;\n        padding: 0.75rem 2rem;\n        border-radius: 12px;\n        font-weight: 600;\n        letter-spacing: 0.5px;\n        transition: all 0.3s ease;\n        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);\n        width: 100%;\n    }\n    .stButton button:hover {\n        opacity: 0.9;\n        transform: translateY(-1px);\n        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.3);\n    }\n    \n    /* Expander */\n    .streamlit-expanderHeader {\n        background-color: #f8fafc;\n        border-radius: 12px;\n        padding: 1rem;\n        font-weight: 600;\n        border: 1px solid #e2e8f0;\n    }\n\n    /* Sidebar */\n    [data-testid="stSidebar"] {\n        background-color: #f8fafc;\n        border-right: 1px solid #e2e8f0;\n    }\n    \n    /* Metrics/Info */\n    .info-box {\n        background: #eff6ff;\n        border: 1px solid #dbeafe;\n        color: #1e40af;\n        padding: 1rem;\n        border-radius: 12px;\n        margin-bottom: 1rem;\n    }\n\n    /* Animation classes */\n    .fade-in {\n        animation: fadeIn 0.5s ease-in;\n    }\n    @keyframes fadeIn {\n        0% { opacity: 0; transform: translateY(10px); }\n        100% { opacity: 1; transform: translateY(0); }\n    }\n\n</style>\n', unsafe_allow_html=True)
DB_FILE = 'onboard_data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS organizations (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    name TEXT UNIQUE NOT NULL\n                )')
    c.execute('CREATE TABLE IF NOT EXISTS brands (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    org_id INTEGER,\n                    name TEXT NOT NULL,\n                    social_links TEXT,     -- JSON: {platform: url}\n                    meta_access TEXT,      -- JSON: {has_access: bool, details: str}\n                    meta_ads_access TEXT,  -- JSON\n                    ga_access TEXT,        -- JSON\n                    gads_access TEXT,      -- JSON\n                    FOREIGN KEY (org_id) REFERENCES organizations(id)\n                )')
    c.execute('CREATE TABLE IF NOT EXISTS competitors (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    brand_id INTEGER,\n                    name TEXT,\n                    social_links TEXT,     -- JSON\n                    meta_access TEXT,      -- JSON\n                    meta_ads_access TEXT,  -- JSON\n                    ga_access TEXT,        -- JSON\n                    gads_access TEXT,      -- JSON\n                    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE\n                )')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def save_organization(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO organizations (name) VALUES (?)', (name,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        c.execute('SELECT id FROM organizations WHERE name=?', (name,))
        return c.fetchone()[0]
    finally:
        conn.close()

def update_organization(id, name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE organizations SET name=? WHERE id=?', (name, id))
    conn.commit()
    conn.close()

def save_brand(org_id, brand_data, existing_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    cols = ['org_id', 'name', 'social_links', 'meta_access', 'meta_ads_access', 'ga_access', 'gads_access']
    vals = [org_id, brand_data['name'], json.dumps(brand_data['social_links']), json.dumps(brand_data['meta_access']), json.dumps(brand_data['meta_ads_access']), json.dumps(brand_data['ga_access']), json.dumps(brand_data['gads_access'])]
    if existing_id:
        c.execute('UPDATE brands SET name=?, social_links=?, meta_access=?, meta_ads_access=?, ga_access=?, gads_access=? \n                     WHERE id=?', vals[1:] + [existing_id])
        brand_id = existing_id
    else:
        c.execute(f"INSERT INTO brands ({','.join(cols)}) VALUES ({','.join(['?'] * 7)})", vals)
        brand_id = c.lastrowid
    conn.commit()
    conn.close()
    return brand_id

def save_competitor(brand_id, comp_data, existing_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    cols = ['brand_id', 'name', 'social_links', 'meta_access', 'meta_ads_access', 'ga_access', 'gads_access']
    vals = [brand_id, comp_data['name'], json.dumps(comp_data['social_links']), json.dumps(comp_data['meta_access']), json.dumps(comp_data['meta_ads_access']), json.dumps(comp_data['ga_access']), json.dumps(comp_data['gads_access'])]
    if existing_id:
        c.execute('UPDATE competitors SET name=?, social_links=?, meta_access=?, meta_ads_access=?, ga_access=?, gads_access=? \n                     WHERE id=?', vals[1:] + [existing_id])
    else:
        c.execute(f"INSERT INTO competitors ({','.join(cols)}) VALUES ({','.join(['?'] * 7)})", vals)
    conn.commit()
    conn.close()

def get_all_organizations():
    conn = get_db_connection()
    df = pd.read_sql('SELECT * FROM organizations', conn)
    conn.close()
    return df

def get_org_details(org_id):
    conn = get_db_connection()
    brands = pd.read_sql('SELECT * FROM brands WHERE org_id=?', conn, params=(org_id,))
    data = {'brands': []}
    for _, b_row in brands.iterrows():
        b_data = {'id': b_row['id'], 'name': b_row['name'], 'social_links': json.loads(b_row['social_links']), 'meta_access': json.loads(b_row['meta_access']), 'meta_ads_access': json.loads(b_row['meta_ads_access']), 'ga_access': json.loads(b_row['ga_access']), 'gads_access': json.loads(b_row['gads_access']), 'competitors': []}
        comps = pd.read_sql('SELECT * FROM competitors WHERE brand_id=?', conn, params=(b_row['id'],))
        for _, c_row in comps.iterrows():
            c_data = {'id': c_row['id'], 'name': c_row['name'], 'social_links': json.loads(c_row['social_links']), 'meta_access': json.loads(c_row['meta_access']), 'meta_ads_access': json.loads(c_row['meta_ads_access']), 'ga_access': json.loads(c_row['ga_access']), 'gads_access': json.loads(c_row['gads_access'])}
            b_data['competitors'].append(c_data)
        data['brands'].append(b_data)
    conn.close()
    return data

def render_access_inputs(label_prefix, key_prefix):
    col1, col2 = st.columns([1, 2])
    with col1:
        has_access = st.selectbox(f'{label_prefix} Access?', ['No', 'Yes'], key=f'{key_prefix}_bool')
    with col2:
        details = ''
        if has_access == 'Yes':
            details = st.text_input(f'Details for {label_prefix}', placeholder='Enter access details...', key=f'{key_prefix}_details')
    return {'has_access': has_access == 'Yes', 'details': details}

def render_social_inputs(key_prefix):
    platforms = ['Facebook', 'Instagram', 'Twitter(X)', 'Youtube', 'TikTok', 'Website']
    links = {}
    cols = st.columns(3)
    for i, p in enumerate(platforms):
        col_idx = i % 3
        with cols[col_idx]:
            links[p] = st.text_input(p, placeholder=f'{p} URL', key=f'{key_prefix}_{p}')
    return links

def render_entity_form(prefix, default_data=None, include_access=True):
    if not default_data:
        default_data = {}
    st.markdown('##### 🔗 Social Media')
    socials = render_social_inputs(f'{prefix}_soc')
    if include_access:
        st.markdown('##### 🔐 Platform Access')
        meta_acc = render_access_inputs('Meta Pages', f'{prefix}_mp')
        meta_ads_acc = render_access_inputs('Meta Ads', f'{prefix}_ma')
        ga_acc = render_access_inputs('Google Analytics', f'{prefix}_ga')
        gads_acc = render_access_inputs('Google Ads', f'{prefix}_gad')
        return {'social_links': socials, 'meta_access': meta_acc, 'meta_ads_access': meta_ads_acc, 'ga_access': ga_acc, 'gads_access': gads_acc}
    else:
        empty_access = {'has_access': False, 'details': ''}
        return {'social_links': socials, 'meta_access': empty_access, 'meta_ads_access': empty_access, 'ga_access': empty_access, 'gads_access': empty_access}

def main():
    init_db()
    st.sidebar.title('🚀 Onboarding')
    page = st.sidebar.radio('Navigate', ['New Client', 'Manage / Edit', 'Export Data'])
    if page == 'New Client':
        render_new_client()
    elif page == 'Manage / Edit':
        render_manage_edit()
    elif page == 'Export Data':
        render_export()

def render_new_client():
    st.markdown('<h1>New Client Onboarding</h1>', unsafe_allow_html=True)
    st.markdown("<div class='info-box'>Fill in the details below to onboard a new organization, their brands, and competitors.</div>", unsafe_allow_html=True)
    with st.container():
        org_name = st.text_input('🏢 Organization Name', placeholder='e.g. Acme Corp')
        num_brands = st.number_input('Number of Brands', min_value=1, max_value=10, value=1)
    if org_name:
        with st.form('onboard_form'):
            all_brands_data = []
            for i in range(int(num_brands)):
                st.markdown(f'### Brand {i + 1}')
                with st.container():
                    b_name = st.text_input(f'Brand Name', key=f'b_name_{i}')
                    with st.expander(f"Brand Details: {(b_name if b_name else 'Enter Name')}", expanded=True):
                        brand_info = render_entity_form(f'b_{i}', include_access=True)
                    st.markdown('#### ⚔️ Competitors')
                    num_comps = st.number_input(f'Competitors for this brand', 0, 10, 0, key=f'b_num_comp_{i}')
                    brand_competitors = []
                    for j in range(int(num_comps)):
                        st.markdown(f'**Competitor {j + 1}**')
                        c_name = st.text_input('Competitor Name', key=f'c_name_{i}_{j}')
                        with st.expander(f'Competitor Details', expanded=False):
                            comp_info = render_entity_form(f'c_{i}_{j}', include_access=False)
                            comp_info['name'] = c_name
                            brand_competitors.append(comp_info)
                    st.markdown('---')
                    brand_info['name'] = b_name
                    brand_info['competitors'] = brand_competitors
                    all_brands_data.append(brand_info)
            submitted = st.form_submit_button('💾 Save Client & Onboard')
            if submitted:
                if not org_name:
                    st.error('Organization Name is required.')
                else:
                    try:
                        org_id = save_organization(org_name)
                        for b_data in all_brands_data:
                            if b_data['name']:
                                b_id = save_brand(org_id, b_data)
                                for c_data in b_data['competitors']:
                                    if c_data['name']:
                                        save_competitor(b_id, c_data)
                        st.success('✅ Client onboarded successfully!')
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f'Error saving data: {str(e)}')

def render_manage_edit():
    st.markdown('<h1>Manage Clients</h1>', unsafe_allow_html=True)
    df_orgs = get_all_organizations()
    if df_orgs.empty:
        st.info("No clients found. Go to 'New Client' to add one.")
        return
    selected_org_name = st.selectbox('Select Organization to Edit', df_orgs['name'].tolist())
    if selected_org_name:
        org_row = df_orgs[df_orgs['name'] == selected_org_name].iloc[0]
        org_id = int(org_row['id'])
        org_data = get_org_details(org_id)
        with st.container():
            new_org_name = st.text_input('Edit Organization Name', value=selected_org_name)
            if st.button('Update Organization Name'):
                update_organization(org_id, new_org_name)
                st.success('Updated!')
                st.rerun()
        st.markdown('### Edit Brands & Competitors')
        for b_idx, brand in enumerate(org_data['brands']):
            with st.expander(f"Brand: {brand['name']}", expanded=False):
                with st.form(key=f"edit_brand_{brand['id']}"):
                    st.caption('Update details below and click Save.')
                    e_b_name = st.text_input('Brand Name', value=brand['name'], key=f"e_bn_{brand['id']}")
                    st.markdown('#### Socials')
                    e_soc = {}
                    platforms = ['Facebook', 'Instagram', 'Twitter(X)', 'Youtube', 'TikTok', 'Website']
                    cols = st.columns(3)
                    for i, p in enumerate(platforms):
                        with cols[i % 3]:
                            val = brand['social_links'].get(p, '')
                            e_soc[p] = st.text_input(p, value=val, key=f"e_s_{brand['id']}_{p}")
                    st.markdown('#### Access')

                    def access_edit_ui(label, key_base, data_dict):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            idx = 1 if data_dict.get('has_access') else 0
                            has = st.selectbox(f'{label} Access?', ['No', 'Yes'], index=idx, key=f'{key_base}_b')
                        with col2:
                            det = st.text_input(f'Details', value=data_dict.get('details', ''), key=f'{key_base}_d')
                        return {'has_access': has == 'Yes', 'details': det}
                    e_ma = access_edit_ui('Meta', f"e_ma_{brand['id']}", brand['meta_access'])
                    e_maa = access_edit_ui('Meta Ads', f"e_maa_{brand['id']}", brand['meta_ads_access'])
                    e_ga = access_edit_ui('GA', f"e_ga_{brand['id']}", brand['ga_access'])
                    e_gad = access_edit_ui('GAds', f"e_gad_{brand['id']}", brand['gads_access'])
                    if st.form_submit_button('Save Changes to Brand'):
                        b_update_data = {'name': e_b_name, 'social_links': e_soc, 'meta_access': e_ma, 'meta_ads_access': e_maa, 'ga_access': e_ga, 'gads_access': e_gad}
                        save_brand(org_id, b_update_data, existing_id=brand['id'])
                        st.success('Brand updated!')
                        time.sleep(1)
                        st.rerun()
                st.markdown('#### Competitors (Edit separately)')
                for comp in brand['competitors']:
                    with st.form(key=f"edit_comp_{comp['id']}"):
                        st.markdown(f"**Competitor**: {comp['name']}")
                        e_c_name = st.text_input('Name', value=comp['name'], key=f"ec_n_{comp['id']}")
                        e_c_soc = {}
                        cols = st.columns(3)
                        for i, p in enumerate(platforms):
                            with cols[i % 3]:
                                val = comp['social_links'].get(p, '')
                                e_c_soc[p] = st.text_input(p, value=val, key=f"ec_s_{comp['id']}_{p}")
                        if st.form_submit_button('Save Competitor'):
                            c_ma = access_edit_ui('Meta', f"ec_ma_{comp['id']}", comp['meta_access'])
                            c_update_data = {'name': e_c_name, 'social_links': e_c_soc, 'meta_access': c_ma, 'meta_ads_access': comp['meta_ads_access'], 'ga_access': comp['ga_access'], 'gads_access': comp['gads_access']}
                            save_competitor(brand['id'], c_update_data, existing_id=comp['id'])
                            st.success('Competitor updated!')
                            st.rerun()

def render_export():
    st.markdown('<h1>Export Data</h1>', unsafe_allow_html=True)
    conn = get_db_connection()

    def clean(val):
        return val if val else ''

    def parse_access(json_str):
        try:
            d = json.loads(json_str)
            if d.get('has_access'):
                det = d.get('details', '').strip()
                return f'Yes - {det}' if det else 'Yes'
            return 'No'
        except:
            return 'No'
    orgs_df = pd.read_sql('SELECT * FROM organizations', conn)
    if orgs_df.empty:
        st.warning('No data found.')
        conn.close()
        return
    selected_org_name = st.selectbox('Select Organization to Export', orgs_df['name'].tolist())
    org_id = orgs_df[orgs_df['name'] == selected_org_name].iloc[0]['id']
    brands = pd.read_sql('SELECT * FROM brands WHERE org_id=?', conn, params=(int(org_id),))
    conn.close()
    if brands.empty:
        st.info('No brands found for this organization.')
        return
    flattened_data = []
    for _, brand in brands.iterrows():
        try:
            b_soc = json.loads(brand['social_links'])
        except:
            b_soc = {}
        b_row = {'Organization': selected_org_name, 'Type': 'Brand', 'Names': brand['name'], 'Parent Brand': brand['name'], 'Facebook': b_soc.get('Facebook', ''), 'Instagram': b_soc.get('Instagram', ''), 'Twitter (X)': b_soc.get('Twitter(X)', ''), 'Youtube': b_soc.get('Youtube', ''), 'TikTok': b_soc.get('TikTok', ''), 'Website': b_soc.get('Website', ''), 'Meta Access': parse_access(brand['meta_access']), 'Meta Ad Access': parse_access(brand['meta_ads_access']), 'GA Access': parse_access(brand['ga_access']), 'G Ads Access': parse_access(brand['gads_access'])}
        flattened_data.append(b_row)
        conn = get_db_connection()
        comps = pd.read_sql('SELECT * FROM competitors WHERE brand_id=?', conn, params=(int(brand['id']),))
        conn.close()
        for _, comp in comps.iterrows():
            try:
                c_soc = json.loads(comp['social_links'])
            except:
                c_soc = {}
            c_row = {'Organization': selected_org_name, 'Type': 'Competitor', 'Names': comp['name'], 'Parent Brand': brand['name'], 'Facebook': c_soc.get('Facebook', ''), 'Instagram': c_soc.get('Instagram', ''), 'Twitter (X)': c_soc.get('Twitter(X)', ''), 'Youtube': c_soc.get('Youtube', ''), 'TikTok': c_soc.get('TikTok', ''), 'Website': c_soc.get('Website', ''), 'Meta Access': 'N/A', 'Meta Ad Access': 'N/A', 'GA Access': 'N/A', 'G Ads Access': 'N/A'}
            flattened_data.append(c_row)
    df_export = pd.DataFrame(flattened_data)
    cols = ['Organization', 'Type', 'Names', 'Parent Brand', 'Facebook', 'Instagram', 'Twitter (X)', 'Youtube', 'TikTok', 'Website', 'Meta Access', 'Meta Ad Access', 'GA Access', 'G Ads Access']
    for c in cols:
        if c not in df_export.columns:
            df_export[c] = ''
    df_export = df_export[cols]
    st.dataframe(df_export, use_container_width=True)
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(label=f'📥 Download CSV for {selected_org_name}', data=csv, file_name=f'{selected_org_name}_export.csv', mime='text/csv')
if __name__ == '__main__':
    main()