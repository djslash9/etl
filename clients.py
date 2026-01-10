import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
DB_FILE = 'client_data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS organizations (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    name TEXT NOT NULL UNIQUE,\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                )')
    c.execute('CREATE TABLE IF NOT EXISTS brands (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    org_id INTEGER,\n                    name TEXT NOT NULL,\n                    website TEXT,\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    FOREIGN KEY (org_id) REFERENCES organizations (id)\n                )')
    c.execute('CREATE TABLE IF NOT EXISTS competitors (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    brand_id INTEGER,\n                    name TEXT NOT NULL,\n                    website TEXT,\n                    FOREIGN KEY (brand_id) REFERENCES brands (id)\n                )')
    c.execute("CREATE TABLE IF NOT EXISTS social_links (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    entity_type TEXT CHECK(entity_type IN ('brand', 'competitor')),\n                    entity_id INTEGER,\n                    platform TEXT,\n                    url TEXT,\n                    FOREIGN KEY (entity_id) REFERENCES brands (id) ON DELETE CASCADE\n                )")
    c.execute('CREATE TABLE IF NOT EXISTS reports (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    brand_id INTEGER,\n                    report_type TEXT,\n                    is_selected BOOLEAN,\n                    details TEXT, -- JSON blob for extra details if needed\n                    FOREIGN KEY (brand_id) REFERENCES brands (id)\n                )')
    c.execute("CREATE TABLE IF NOT EXISTS keywords (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    brand_id INTEGER,\n                    type TEXT CHECK(type IN ('keyword', 'hashtag')),\n                    text TEXT,\n                    FOREIGN KEY (brand_id) REFERENCES brands (id)\n                )")
    c.execute("CREATE TABLE IF NOT EXISTS meta_data (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    brand_id INTEGER,\n                    platform TEXT, -- 'Meta', 'Google Analytics', 'Google Ads', etc.\n                    page_details TEXT,\n                    access_given_to TEXT,\n                    FOREIGN KEY (brand_id) REFERENCES brands (id)\n                )")
    c.execute("CREATE TABLE IF NOT EXISTS submissions (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    org_id INTEGER,\n                    type TEXT CHECK(type IN ('onboard', 'pitch')),\n                    submission_date DATE,\n                    presentation_date DATE,\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    FOREIGN KEY (org_id) REFERENCES organizations (id)\n                )")
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def get_organizations():
    conn = get_db_connection()
    df = pd.read_sql('SELECT * FROM organizations', conn)
    conn.close()
    return df

def add_organization(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO organizations (name) VALUES (?)', (name,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def add_brand(org_id, name, website=''):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO brands (org_id, name, website) VALUES (?, ?, ?)', (org_id, name, website))
    conn.commit()
    brand_id = c.lastrowid
    conn.close()
    return brand_id

def client_portal_app():
    st.set_page_config(page_title='Client Portal', page_icon='🚀', layout='wide')
    st.markdown('## 🚀 Client Portal')
    init_db()
    menu = ['Onboard Client', 'Pitch Client', 'Data Management', 'Explore & Export']
    choice = st.sidebar.selectbox('Portal Menu', menu)
    if choice == 'Onboard Client':
        render_onboard_flow()
    elif choice == 'Pitch Client':
        render_pitch_flow()
    elif choice == 'Data Management':
        render_data_management()
    elif choice == 'Explore & Export':
        render_explore_export()

def render_onboard_flow():
    st.subheader('📝 Onboard New Client')
    if 'onboard_brands' not in st.session_state:
        st.session_state.onboard_brands = ['']
    st.markdown('#### 1. Organization & Brands')
    col1, col2 = st.columns([2, 1])
    with col1:
        org_input = st.text_input('Organization Name', key='onboard_org')
    if 'brand_count' not in st.session_state:
        st.session_state.brand_count = 1

    def add_brand_slot():
        st.session_state.brand_count += 1
    brands_list = []
    for i in range(st.session_state.brand_count):
        b_name = st.text_input(f'Brand {i + 1} Name', key=f'brand_name_{i}')
        if b_name:
            brands_list.append(b_name)
    st.button('➕ Add Another Brand', on_click=add_brand_slot)
    if not org_input or not brands_list:
        st.info('Please enter Organization Name and at least one Brand to proceed.')
        return
    st.markdown('---')
    st.markdown('#### 2. Brand Details & Reports')
    with st.form('client_details_form'):
        all_brands_data = {}
        for brand_name in brands_list:
            st.markdown(f'### 🏷️ Brand: {brand_name}')
            with st.expander(f'Details for {brand_name}', expanded=True):
                b_website = st.text_input(f'Website for {brand_name}', key=f'web_{brand_name}')
                report_options = ['Competitor Analysis', 'Google Trends', 'Web Traffic', 'Social Listening', 'Meta Platform', 'Google Analytics', 'Meta Campaigns', 'Google Ads']
                selected_reports = st.multiselect(f'Select Reports for {brand_name}', report_options, key=f'rep_{brand_name}')
                brand_data = {'website': b_website, 'reports': selected_reports, 'competitors': [], 'social_listening': {}, 'meta_data': []}
                if 'Competitor Analysis' in selected_reports:
                    st.markdown('##### ⚔️ Competitor Analysis')
                    num_comps = st.number_input(f'Number of Competitors for {brand_name}', 1, 10, 1, key=f'num_comp_{brand_name}')
                    for c_i in range(num_comps):
                        st.markdown(f'**Competitor {c_i + 1}**')
                        c_name = st.text_input(f'Name', key=f'c_name_{brand_name}_{c_i}')
                        c_web = st.text_input(f'Website', key=f'c_web_{brand_name}_{c_i}')
                        cols = st.columns(4)
                        c_fb = cols[0].text_input('Facebook', key=f'c_fb_{brand_name}_{c_i}')
                        c_ig = cols[1].text_input('Instagram', key=f'c_ig_{brand_name}_{c_i}')
                        c_tw = cols[2].text_input('Twitter', key=f'c_tw_{brand_name}_{c_i}')
                        c_li = cols[3].text_input('LinkedIn', key=f'c_li_{brand_name}_{c_i}')
                        if c_name:
                            brand_data['competitors'].append({'name': c_name, 'website': c_web, 'socials': {'Facebook': c_fb, 'Instagram': c_ig, 'Twitter': c_tw, 'LinkedIn': c_li}})
                if 'Web Traffic' in selected_reports:
                    st.markdown('##### 🌐 Web Traffic')
                    st.info(f'Will generate report for: {brand_name} ({b_website}) and defined competitors.')
                if 'Social Listening' in selected_reports:
                    st.markdown('##### 👂 Social Listening')
                    sl_needs = st.checkbox(f'Need Social Listening for {brand_name}?', key=f'sl_need_{brand_name}')
                    if sl_needs:
                        sl_types = st.multiselect(f'Listening Type', ['Competitor Keyword Listening', 'Brand Health'], key=f'sl_type_{brand_name}')
                        sl_data = {'types': sl_types, 'keywords': [], 'hashtags': []}
                        if 'Competitor Keyword Listening' in sl_types:
                            st.caption('Will use names from Competitor Analysis section.')
                        if 'Brand Health' in sl_types:
                            st.markdown('Insert Keywords & Hashtags (Max 10 each)')
                            k_input = st.text_area(f'Keywords (comma separated)', key=f'kw_{brand_name}')
                            h_input = st.text_area(f'Hashtags (comma separated)', key=f'ht_{brand_name}')
                            k_count = len(k_input.split(',')) if k_input else 0
                            h_count = len(h_input.split(',')) if h_input else 0
                            if k_count > 10 or h_count > 10:
                                st.warning('⚠️ Limit exceeded! Contact admin for more words.')
                            sl_data['keywords'] = k_input
                            sl_data['hashtags'] = h_input
                        brand_data['social_listening'] = sl_data
                if any((x in selected_reports for x in ['Meta Platform', 'Meta Campaigns', 'Google Analytics', 'Google Ads'])):
                    st.markdown('##### 📊 Platform Access & Data')
                    if 'Meta Platform' in selected_reports or 'Meta Campaigns' in selected_reports:
                        m_pages = st.text_input(f'Meta Page Details', key=f'mp_{brand_name}')
                        m_access = st.text_input(f'Meta Access Given To', key=f'ma_{brand_name}')
                        brand_data['meta_data'].append({'platform': 'Meta', 'details': m_pages, 'access': m_access})
                    if 'Google Analytics' in selected_reports or 'Google Ads' in selected_reports:
                        g_pages = st.text_input(f'Google Details', key=f'gp_{brand_name}')
                        g_access = st.text_input(f'Google Access Given To', key=f'ga_{brand_name}')
                        brand_data['meta_data'].append({'platform': 'Google', 'details': g_pages, 'access': g_access})
                all_brands_data[brand_name] = brand_data
        st.markdown('---')
        onboard_date = st.date_input('Client Onboard Date')
        client_email = st.text_input('Client Email (for notification)')
        submitted = st.form_submit_button('💾 Save & Onboard Client')
        if submitted:
            save_client_data(org_input, all_brands_data, 'onboard', onboard_date, client_email)

def render_pitch_flow():
    st.subheader('📢 Pitch Client')
    st.markdown('#### 1. Organization & Brands')
    org_input = st.text_input('Organization Name', key='pitch_org')
    if 'pitch_brand_count' not in st.session_state:
        st.session_state.pitch_brand_count = 1

    def add_pitch_brand_slot():
        st.session_state.pitch_brand_count += 1
    brands_list = []
    for i in range(st.session_state.pitch_brand_count):
        b_name = st.text_input(f'Brand {i + 1} Name', key=f'pitch_brand_{i}')
        if b_name:
            brands_list.append(b_name)
    st.button('➕ Add Another Brand', on_click=add_pitch_brand_slot, key='add_pitch_brand')
    if not org_input or not brands_list:
        st.info('Please enter Organization Name and at least one Brand.')
        return
    st.markdown('---')
    st.markdown('#### 2. Pitch Details')
    with st.form('pitch_details_form'):
        all_brands_data = {}
        for brand_name in brands_list:
            st.markdown(f'### 🏷️ Brand: {brand_name}')
            with st.expander(f'Details for {brand_name}', expanded=True):
                b_website = st.text_input(f'Website', key=f'p_web_{brand_name}')
                report_options = ['Competitor Analysis', 'Google Trends', 'Web Traffic', 'Social Listening']
                selected_reports = st.multiselect(f'Select Reports', report_options, key=f'p_rep_{brand_name}')
                brand_data = {'website': b_website, 'reports': selected_reports, 'competitors': [], 'social_listening': {}, 'meta_data': []}
                if 'Competitor Analysis' in selected_reports:
                    st.markdown('##### ⚔️ Competitor Analysis')
                    num_comps = st.number_input(f'Number of Competitors', 1, 5, 1, key=f'p_num_comp_{brand_name}')
                    for c_i in range(num_comps):
                        c_name = st.text_input(f'Competitor {c_i + 1} Name', key=f'p_c_name_{brand_name}_{c_i}')
                        c_web = st.text_input(f'Website', key=f'p_c_web_{brand_name}_{c_i}')
                        c_socials = st.text_input(f'Social Links (comma sep)', key=f'p_c_soc_{brand_name}_{c_i}')
                        if c_name:
                            brand_data['competitors'].append({'name': c_name, 'website': c_web, 'socials': {'links': c_socials}})
                if 'Social Listening' in selected_reports:
                    st.markdown('##### 👂 Social Listening')
                    sl_needs = st.checkbox(f'Need Social Listening?', key=f'p_sl_need_{brand_name}')
                    if sl_needs:
                        sl_types = st.multiselect(f'Type', ['Competitor Keyword Listening', 'Brand Health'], key=f'p_sl_type_{brand_name}')
                        sl_data = {'types': sl_types, 'keywords': [], 'hashtags': []}
                        if 'Brand Health' in sl_types:
                            k_input = st.text_area(f'Keywords', key=f'p_kw_{brand_name}')
                            h_input = st.text_area(f'Hashtags', key=f'p_ht_{brand_name}')
                            sl_data['keywords'] = k_input
                            sl_data['hashtags'] = h_input
                        brand_data['social_listening'] = sl_data
                all_brands_data[brand_name] = brand_data
        st.markdown('---')
        presentation_date = st.date_input('Client Presentation Date')
        submitted = st.form_submit_button('💾 Save Pitch Data')
        if submitted:
            save_client_data(org_input, all_brands_data, 'pitch', presentation_date, '')

def save_client_data(org_name, all_brands_data, submission_type, date_val, email):
    try:
        org_id = add_organization(org_name)
        if not org_id:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT id FROM organizations WHERE name=?', (org_name,))
            res = c.fetchone()
            if res:
                org_id = res[0]
            conn.close()
        conn = get_db_connection()
        c = conn.cursor()
        if submission_type == 'onboard':
            c.execute('INSERT INTO submissions (org_id, type, submission_date) VALUES (?, ?, ?)', (org_id, submission_type, date_val))
        else:
            c.execute('INSERT INTO submissions (org_id, type, presentation_date) VALUES (?, ?, ?)', (org_id, submission_type, date_val))
        conn.commit()
        conn.close()
        for brand_name, data in all_brands_data.items():
            brand_id = add_brand(org_id, brand_name, data.get('website', ''))
            conn = get_db_connection()
            c = conn.cursor()
            for r in data.get('reports', []):
                c.execute('INSERT INTO reports (brand_id, report_type, is_selected) VALUES (?, ?, ?)', (brand_id, r, True))
            for comp in data.get('competitors', []):
                c.execute('INSERT INTO competitors (brand_id, name, website) VALUES (?, ?, ?)', (brand_id, comp['name'], comp['website']))
                comp_id = c.lastrowid
                socials = comp.get('socials', {})
                for platform, url in socials.items():
                    if url:
                        c.execute('INSERT INTO social_links (entity_type, entity_id, platform, url) VALUES (?, ?, ?, ?)', ('competitor', comp_id, platform, url))
            sl = data.get('social_listening', {})
            if sl:
                kws = sl.get('keywords', '')
                if kws:
                    for k in kws.split(','):
                        if k.strip():
                            c.execute('INSERT INTO keywords (brand_id, type, text) VALUES (?, ?, ?)', (brand_id, 'keyword', k.strip()))
                hts = sl.get('hashtags', '')
                if hts:
                    for h in hts.split(','):
                        if h.strip():
                            c.execute('INSERT INTO keywords (brand_id, type, text) VALUES (?, ?, ?)', (brand_id, 'hashtag', h.strip()))
            for md in data.get('meta_data', []):
                c.execute('INSERT INTO meta_data (brand_id, platform, page_details, access_given_to) VALUES (?, ?, ?, ?)', (brand_id, md['platform'], md['details'], md['access']))
            conn.commit()
            conn.close()
        st.success(f'✅ {submission_type.title()} data saved successfully!')
        if email:
            st.info(f'📧 Notification sent to {email} (Simulated)')
    except Exception as e:
        st.error(f'Error saving data: {e}')

def render_data_management():
    st.subheader('🛠️ Data Management')
    df_orgs = get_organizations()
    if df_orgs.empty:
        st.info('No organizations found.')
        return
    org_names = df_orgs['name'].tolist()
    selected_org = st.selectbox('Select Organization', org_names)
    if selected_org:
        conn = get_db_connection()
        org_id = df_orgs[df_orgs['name'] == selected_org]['id'].values[0]
        df_brands = pd.read_sql('SELECT * FROM brands WHERE org_id=?', conn, params=(org_id,))
        if not df_brands.empty:
            brand_names = df_brands['name'].tolist()
            selected_brand = st.selectbox('Select Brand', brand_names)
            if selected_brand:
                brand_row = df_brands[df_brands['name'] == selected_brand].iloc[0]
                st.markdown(f'#### Edit Brand: {selected_brand}')
                new_name = st.text_input('Brand Name', value=selected_brand)
                new_web = st.text_input('Website', value=brand_row['website'])
                if st.button('Update Brand Details'):
                    c = conn.cursor()
                    c.execute('UPDATE brands SET name=?, website=? WHERE id=?', (new_name, new_web, int(brand_row['id'])))
                    conn.commit()
                    st.success('Updated!')
                    st.rerun()
                if st.button('🗑️ Delete Brand', type='primary'):
                    c = conn.cursor()
                    c.execute('DELETE FROM brands WHERE id=?', (int(brand_row['id']),))
                    conn.commit()
                    st.warning('Brand deleted.')
                    st.rerun()
        else:
            st.info('No brands for this organization.')
        conn.close()

def render_explore_export():
    st.subheader('🔍 Explore & Export')
    conn = get_db_connection()
    query = '\n    SELECT \n        o.name as Organization,\n        b.name as Brand,\n        b.website as Website,\n        GROUP_CONCAT(DISTINCT r.report_type) as Reports,\n        s.type as Submission_Type,\n        s.submission_date,\n        s.presentation_date\n    FROM organizations o\n    JOIN brands b ON b.org_id = o.id\n    LEFT JOIN reports r ON r.brand_id = b.id\n    LEFT JOIN submissions s ON s.org_id = o.id\n    GROUP BY b.id\n    '
    df = pd.read_sql(query, conn)
    conn.close()
    st.dataframe(df)
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button('📥 Download All Data as CSV', csv, 'client_data_export.csv', 'text/csv', key='download-csv')
if __name__ == '__main__':
    client_portal_app()