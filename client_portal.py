import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os

# --- Database Setup ---
DB_FILE = 'client_data.db'

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Organizations
    c.execute('''CREATE TABLE IF NOT EXISTS organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

    # Brands
    c.execute('''CREATE TABLE IF NOT EXISTS brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER,
                    name TEXT NOT NULL,
                    website TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (org_id) REFERENCES organizations (id)
                )''')

    # Competitors
    c.execute('''CREATE TABLE IF NOT EXISTS competitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER,
                    name TEXT NOT NULL,
                    website TEXT,
                    FOREIGN KEY (brand_id) REFERENCES brands (id)
                )''')

    # Social Links (for Brands and Competitors)
    c.execute('''CREATE TABLE IF NOT EXISTS social_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT CHECK(entity_type IN ('brand', 'competitor')),
                    entity_id INTEGER,
                    platform TEXT,
                    url TEXT,
                    FOREIGN KEY (entity_id) REFERENCES brands (id) ON DELETE CASCADE
                )''')
    
    # Reports Selection
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER,
                    report_type TEXT,
                    is_selected BOOLEAN,
                    details TEXT, -- JSON blob for extra details if needed
                    FOREIGN KEY (brand_id) REFERENCES brands (id)
                )''')

    # Keywords / Hashtags
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER,
                    type TEXT CHECK(type IN ('keyword', 'hashtag')),
                    text TEXT,
                    FOREIGN KEY (brand_id) REFERENCES brands (id)
                )''')

    # Meta / Google Data
    c.execute('''CREATE TABLE IF NOT EXISTS meta_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER,
                    platform TEXT, -- 'Meta', 'Google Analytics', 'Google Ads', etc.
                    page_details TEXT,
                    access_given_to TEXT,
                    FOREIGN KEY (brand_id) REFERENCES brands (id)
                )''')

    # Submissions (to track Onboard vs Pitch)
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER,
                    type TEXT CHECK(type IN ('onboard', 'pitch')),
                    submission_date DATE,
                    presentation_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (org_id) REFERENCES organizations (id)
                )''')

    conn.commit()
    conn.close()

# --- Database Helpers ---

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def get_organizations():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM organizations", conn)
    conn.close()
    return df

def add_organization(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO organizations (name) VALUES (?)", (name,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None # Already exists
    finally:
        conn.close()

def add_brand(org_id, name, website=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO brands (org_id, name, website) VALUES (?, ?, ?)", (org_id, name, website))
    conn.commit()
    brand_id = c.lastrowid
    conn.close()
    return brand_id

# --- Main App ---

def client_portal_app():
    st.markdown("## 🚀 Client Portal")
    
    # Initialize DB
    init_db()

    menu = ["Onboard Client", "Pitch Client", "Data Management", "Explore & Export"]
    choice = st.sidebar.selectbox("Portal Menu", menu)

    if choice == "Onboard Client":
        render_onboard_flow()
    elif choice == "Pitch Client":
        render_pitch_flow()
    elif choice == "Data Management":
        render_data_management()
    elif choice == "Explore & Export":
        render_explore_export()

def render_onboard_flow():
    st.subheader("📝 Onboard New Client")
    
    # Initialize session state for brands if not exists
    if 'onboard_brands' not in st.session_state:
        st.session_state.onboard_brands = [""]

    with st.form("onboard_form"):
        # 1. Organization
        org_name = st.text_input("Organization Name")
        
        # 2. Brands (Dynamic)
        st.markdown("### Brands")
        
        # We can't easily add buttons inside a form that update the form structure dynamically without rerun.
        # So we use a number input or manage it outside the form. 
        # For better UX inside a form, let's use a text area for bulk entry or just a fixed number of slots that can be increased.
        # OR, we do the "Add Brand" part outside the main form.
        # Let's try a cleaner approach: First define Org & Brands, THEN fill details.
        pass
    
    # Re-structuring for better Streamlit flow:
    # Step 1: Org & Brands
    st.markdown("#### 1. Organization & Brands")
    col1, col2 = st.columns([2, 1])
    with col1:
        org_input = st.text_input("Organization Name", key="onboard_org")
    
    # Dynamic Brand Management
    if 'brand_count' not in st.session_state:
        st.session_state.brand_count = 1

    def add_brand_slot():
        st.session_state.brand_count += 1

    brands_list = []
    for i in range(st.session_state.brand_count):
        b_name = st.text_input(f"Brand {i+1} Name", key=f"brand_name_{i}")
        if b_name:
            brands_list.append(b_name)
    
    st.button("➕ Add Another Brand", on_click=add_brand_slot)

    if not org_input or not brands_list:
        st.info("Please enter Organization Name and at least one Brand to proceed.")
        return

    st.markdown("---")
    st.markdown("#### 2. Brand Details & Reports")
    
    # Master Form for all details
    with st.form("client_details_form"):
        all_brands_data = {}
        
        for brand_name in brands_list:
            st.markdown(f"### 🏷️ Brand: {brand_name}")
            with st.expander(f"Details for {brand_name}", expanded=True):
                # Brand Website
                b_website = st.text_input(f"Website for {brand_name}", key=f"web_{brand_name}")
                
                # Report Selection
                report_options = [
                    "Competitor Analysis", "Google Trends", "Web Traffic", 
                    "Social Listening", "Meta Platform", "Google Analytics", 
                    "Meta Campaigns", "Google Ads"
                ]
                selected_reports = st.multiselect(f"Select Reports for {brand_name}", report_options, key=f"rep_{brand_name}")
                
                brand_data = {
                    "website": b_website,
                    "reports": selected_reports,
                    "competitors": [],
                    "social_listening": {},
                    "meta_data": []
                }

                # --- Competitor Analysis ---
                if "Competitor Analysis" in selected_reports:
                    st.markdown("##### ⚔️ Competitor Analysis")
                    # Dynamic competitors for this brand? 
                    # Hard to do dynamic add inside this nested form. Let's provide fixed slots or text area.
                    # Requirement: "Give a button to insert competitors name"
                    # In Streamlit forms, buttons trigger submit. We'll use a slider or number input for count.
                    num_comps = st.number_input(f"Number of Competitors for {brand_name}", 1, 10, 1, key=f"num_comp_{brand_name}")
                    
                    for c_i in range(num_comps):
                        st.markdown(f"**Competitor {c_i+1}**")
                        c_name = st.text_input(f"Name", key=f"c_name_{brand_name}_{c_i}")
                        c_web = st.text_input(f"Website", key=f"c_web_{brand_name}_{c_i}")
                        
                        # Social Links
                        cols = st.columns(4)
                        c_fb = cols[0].text_input("Facebook", key=f"c_fb_{brand_name}_{c_i}")
                        c_ig = cols[1].text_input("Instagram", key=f"c_ig_{brand_name}_{c_i}")
                        c_tw = cols[2].text_input("Twitter", key=f"c_tw_{brand_name}_{c_i}")
                        c_li = cols[3].text_input("LinkedIn", key=f"c_li_{brand_name}_{c_i}")
                        # Add others if needed
                        
                        if c_name:
                            brand_data["competitors"].append({
                                "name": c_name, "website": c_web,
                                "socials": {"Facebook": c_fb, "Instagram": c_ig, "Twitter": c_tw, "LinkedIn": c_li}
                            })

                # --- Web Traffic ---
                if "Web Traffic" in selected_reports:
                    st.markdown("##### 🌐 Web Traffic")
                    st.info(f"Will generate report for: {brand_name} ({b_website}) and defined competitors.")

                # --- Social Listening ---
                if "Social Listening" in selected_reports:
                    st.markdown("##### 👂 Social Listening")
                    sl_needs = st.checkbox(f"Need Social Listening for {brand_name}?", key=f"sl_need_{brand_name}")
                    if sl_needs:
                        sl_types = st.multiselect(f"Listening Type", ["Competitor Keyword Listening", "Brand Health"], key=f"sl_type_{brand_name}")
                        
                        sl_data = {"types": sl_types, "keywords": [], "hashtags": []}
                        
                        if "Competitor Keyword Listening" in sl_types:
                            st.caption("Will use names from Competitor Analysis section.")
                            
                        if "Brand Health" in sl_types:
                            st.markdown("Insert Keywords & Hashtags (Max 10 each)")
                            k_input = st.text_area(f"Keywords (comma separated)", key=f"kw_{brand_name}")
                            h_input = st.text_area(f"Hashtags (comma separated)", key=f"ht_{brand_name}")
                            
                            # Simple validation display
                            k_count = len(k_input.split(",")) if k_input else 0
                            h_count = len(h_input.split(",")) if h_input else 0
                            if k_count > 10 or h_count > 10:
                                st.warning("⚠️ Limit exceeded! Contact admin for more words.")
                            
                            sl_data["keywords"] = k_input
                            sl_data["hashtags"] = h_input
                        
                        brand_data["social_listening"] = sl_data

                # --- Meta / Google Data ---
                if any(x in selected_reports for x in ["Meta Platform", "Meta Campaigns", "Google Analytics", "Google Ads"]):
                    st.markdown("##### 📊 Platform Access & Data")
                    
                    if "Meta Platform" in selected_reports or "Meta Campaigns" in selected_reports:
                        m_pages = st.text_input(f"Meta Page Details", key=f"mp_{brand_name}")
                        m_access = st.text_input(f"Meta Access Given To", key=f"ma_{brand_name}")
                        brand_data["meta_data"].append({"platform": "Meta", "details": m_pages, "access": m_access})

                    if "Google Analytics" in selected_reports or "Google Ads" in selected_reports:
                        g_pages = st.text_input(f"Google Details", key=f"gp_{brand_name}")
                        g_access = st.text_input(f"Google Access Given To", key=f"ga_{brand_name}")
                        brand_data["meta_data"].append({"platform": "Google", "details": g_pages, "access": g_access})

                all_brands_data[brand_name] = brand_data

        # Submission details
        st.markdown("---")
        onboard_date = st.date_input("Client Onboard Date")
        client_email = st.text_input("Client Email (for notification)")
        
        submitted = st.form_submit_button("💾 Save & Onboard Client")
        
        if submitted:
            save_client_data(org_input, all_brands_data, "onboard", onboard_date, client_email)


def render_pitch_flow():
    st.subheader("📢 Pitch Client")
    
    # Step 1: Org & Brands
    st.markdown("#### 1. Organization & Brands")
    org_input = st.text_input("Organization Name", key="pitch_org")
    
    if 'pitch_brand_count' not in st.session_state:
        st.session_state.pitch_brand_count = 1

    def add_pitch_brand_slot():
        st.session_state.pitch_brand_count += 1

    brands_list = []
    for i in range(st.session_state.pitch_brand_count):
        b_name = st.text_input(f"Brand {i+1} Name", key=f"pitch_brand_{i}")
        if b_name:
            brands_list.append(b_name)
    
    st.button("➕ Add Another Brand", on_click=add_pitch_brand_slot, key="add_pitch_brand")

    if not org_input or not brands_list:
        st.info("Please enter Organization Name and at least one Brand.")
        return

    st.markdown("---")
    st.markdown("#### 2. Pitch Details")
    
    with st.form("pitch_details_form"):
        all_brands_data = {}
        
        for brand_name in brands_list:
            st.markdown(f"### 🏷️ Brand: {brand_name}")
            with st.expander(f"Details for {brand_name}", expanded=True):
                b_website = st.text_input(f"Website", key=f"p_web_{brand_name}")
                
                # Limited Reports for Pitch
                report_options = ["Competitor Analysis", "Google Trends", "Web Traffic", "Social Listening"]
                selected_reports = st.multiselect(f"Select Reports", report_options, key=f"p_rep_{brand_name}")
                
                brand_data = {
                    "website": b_website,
                    "reports": selected_reports,
                    "competitors": [],
                    "social_listening": {},
                    "meta_data": [] # Not needed for pitch usually, but structure kept consistent
                }

                # Competitor Analysis
                if "Competitor Analysis" in selected_reports:
                    st.markdown("##### ⚔️ Competitor Analysis")
                    num_comps = st.number_input(f"Number of Competitors", 1, 5, 1, key=f"p_num_comp_{brand_name}")
                    for c_i in range(num_comps):
                        c_name = st.text_input(f"Competitor {c_i+1} Name", key=f"p_c_name_{brand_name}_{c_i}")
                        c_web = st.text_input(f"Website", key=f"p_c_web_{brand_name}_{c_i}")
                        # Simplified socials for pitch
                        c_socials = st.text_input(f"Social Links (comma sep)", key=f"p_c_soc_{brand_name}_{c_i}")
                        
                        if c_name:
                            brand_data["competitors"].append({
                                "name": c_name, "website": c_web,
                                "socials": {"links": c_socials}
                            })

                # Social Listening
                if "Social Listening" in selected_reports:
                    st.markdown("##### 👂 Social Listening")
                    sl_needs = st.checkbox(f"Need Social Listening?", key=f"p_sl_need_{brand_name}")
                    if sl_needs:
                        sl_types = st.multiselect(f"Type", ["Competitor Keyword Listening", "Brand Health"], key=f"p_sl_type_{brand_name}")
                        sl_data = {"types": sl_types, "keywords": [], "hashtags": []}
                        
                        if "Brand Health" in sl_types:
                            k_input = st.text_area(f"Keywords", key=f"p_kw_{brand_name}")
                            h_input = st.text_area(f"Hashtags", key=f"p_ht_{brand_name}")
                            sl_data["keywords"] = k_input
                            sl_data["hashtags"] = h_input
                        
                        brand_data["social_listening"] = sl_data

                all_brands_data[brand_name] = brand_data

        st.markdown("---")
        presentation_date = st.date_input("Client Presentation Date")
        
        submitted = st.form_submit_button("💾 Save Pitch Data")
        
        if submitted:
            save_client_data(org_input, all_brands_data, "pitch", presentation_date, "")

def save_client_data(org_name, all_brands_data, submission_type, date_val, email):
    try:
        # 1. Save Org
        org_id = add_organization(org_name)
        if not org_id:
             # Fetch existing
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM organizations WHERE name=?", (org_name,))
            res = c.fetchone()
            if res:
                org_id = res[0]
            conn.close()

        # 2. Save Submission Record
        conn = get_db_connection()
        c = conn.cursor()
        if submission_type == 'onboard':
            c.execute("INSERT INTO submissions (org_id, type, submission_date) VALUES (?, ?, ?)", 
                      (org_id, submission_type, date_val))
        else:
            c.execute("INSERT INTO submissions (org_id, type, presentation_date) VALUES (?, ?, ?)", 
                      (org_id, submission_type, date_val))
        conn.commit()
        conn.close()

        # 3. Save Brands & Details
        for brand_name, data in all_brands_data.items():
            brand_id = add_brand(org_id, brand_name, data.get("website", ""))
            
            # Reports
            conn = get_db_connection()
            c = conn.cursor()
            for r in data.get("reports", []):
                c.execute("INSERT INTO reports (brand_id, report_type, is_selected) VALUES (?, ?, ?)", 
                          (brand_id, r, True))
            
            # Competitors
            for comp in data.get("competitors", []):
                c.execute("INSERT INTO competitors (brand_id, name, website) VALUES (?, ?, ?)",
                          (brand_id, comp["name"], comp["website"]))
                comp_id = c.lastrowid
                
                # Socials
                socials = comp.get("socials", {})
                for platform, url in socials.items():
                    if url:
                        c.execute("INSERT INTO social_links (entity_type, entity_id, platform, url) VALUES (?, ?, ?, ?)",
                                  ('competitor', comp_id, platform, url))
            
            # Social Listening
            sl = data.get("social_listening", {})
            if sl:
                # Save keywords/hashtags
                kws = sl.get("keywords", "")
                if kws:
                    for k in kws.split(","):
                        if k.strip():
                            c.execute("INSERT INTO keywords (brand_id, type, text) VALUES (?, ?, ?)",
                                      (brand_id, 'keyword', k.strip()))
                hts = sl.get("hashtags", "")
                if hts:
                    for h in hts.split(","):
                        if h.strip():
                            c.execute("INSERT INTO keywords (brand_id, type, text) VALUES (?, ?, ?)",
                                      (brand_id, 'hashtag', h.strip()))

            # Meta Data
            for md in data.get("meta_data", []):
                c.execute("INSERT INTO meta_data (brand_id, platform, page_details, access_given_to) VALUES (?, ?, ?, ?)",
                          (brand_id, md["platform"], md["details"], md["access"]))

            conn.commit()
            conn.close()

        st.success(f"✅ {submission_type.title()} data saved successfully!")
        if email:
            st.info(f"📧 Notification sent to {email} (Simulated)")
            
    except Exception as e:
        st.error(f"Error saving data: {e}")

def render_data_management():
    st.subheader("🛠️ Data Management")
    
    # Select Org
    df_orgs = get_organizations()
    if df_orgs.empty:
        st.info("No organizations found.")
        return
        
    org_names = df_orgs['name'].tolist()
    selected_org = st.selectbox("Select Organization", org_names)
    
    if selected_org:
        conn = get_db_connection()
        # Get Brands for Org
        org_id = df_orgs[df_orgs['name'] == selected_org]['id'].values[0]
        df_brands = pd.read_sql("SELECT * FROM brands WHERE org_id=?", conn, params=(org_id,))
        
        if not df_brands.empty:
            brand_names = df_brands['name'].tolist()
            selected_brand = st.selectbox("Select Brand", brand_names)
            
            if selected_brand:
                brand_row = df_brands[df_brands['name'] == selected_brand].iloc[0]
                
                st.markdown(f"#### Edit Brand: {selected_brand}")
                new_name = st.text_input("Brand Name", value=selected_brand)
                new_web = st.text_input("Website", value=brand_row['website'])
                
                if st.button("Update Brand Details"):
                    c = conn.cursor()
                    c.execute("UPDATE brands SET name=?, website=? WHERE id=?", (new_name, new_web, int(brand_row['id'])))
                    conn.commit()
                    st.success("Updated!")
                    st.rerun()
                
                if st.button("🗑️ Delete Brand", type="primary"):
                    c = conn.cursor()
                    # Cascade delete handled by DB constraints if set, else manual
                    # For now just delete brand, assume simple schema
                    c.execute("DELETE FROM brands WHERE id=?", (int(brand_row['id']),))
                    conn.commit()
                    st.warning("Brand deleted.")
                    st.rerun()
        else:
            st.info("No brands for this organization.")
        
        conn.close()

def render_explore_export():
    st.subheader("🔍 Explore & Export")
    
    conn = get_db_connection()
    
    # Master View Query
    query = """
    SELECT 
        o.name as Organization,
        b.name as Brand,
        b.website as Website,
        GROUP_CONCAT(DISTINCT r.report_type) as Reports,
        s.type as Submission_Type,
        s.submission_date,
        s.presentation_date
    FROM organizations o
    JOIN brands b ON b.org_id = o.id
    LEFT JOIN reports r ON r.brand_id = b.id
    LEFT JOIN submissions s ON s.org_id = o.id
    GROUP BY b.id
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    st.dataframe(df)
    
    # Export
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download All Data as CSV",
            csv,
            "client_data_export.csv",
            "text/csv",
            key='download-csv'
        )

if __name__ == "__main__":
    client_portal_app()
