import streamlit as st
import pandas as pd
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import time
from datetime import datetime
import plotly.express as px
import sqlite3
import os

# Set page config
st.set_page_config(page_title='Multi-Language Sentiment Analyzer (En/Si/Ta)', layout='wide', page_icon='🧠')

# --- Database Management ---
DB_FILE = 'senti.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER,
            name TEXT,
            UNIQUE(org_id, name),
            FOREIGN KEY(org_id) REFERENCES organizations(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER,
            name TEXT,
            keywords TEXT,
            is_primary BOOLEAN DEFAULT 0,
            FOREIGN KEY(brand_id) REFERENCES brands(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_organizations():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM organizations ORDER BY name", conn)
    conn.close()
    return df

def add_organization(name):
    # Case-insensitive check
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Check duplicate
        c.execute("SELECT id FROM organizations WHERE LOWER(name) = ?", (name.strip().lower(),))
        if c.fetchone():
            return None # Duplicate
            
        c.execute("INSERT INTO organizations (name) VALUES (?)", (name.strip(),))
        conn.commit()
        org_id = c.lastrowid
        conn.close()
        return org_id
    except Exception as e:
        conn.close()
        st.error(f"Error adding organization: {e}")
        return None

def rename_organization(org_id, new_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Check duplicate
        c.execute("SELECT id FROM organizations WHERE LOWER(name) = ? AND id != ?", (new_name.strip().lower(), int(org_id)))
        if c.fetchone():
            return False
            
        c.execute("UPDATE organizations SET name = ? WHERE id = ?", (new_name.strip(), int(org_id)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error renaming: {e}")
        return False

def delete_organization(org_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Cascade delete (Brands -> Competitors)
        # Find all brand IDs
        c.execute("SELECT id FROM brands WHERE org_id = ?", (int(org_id),))
        b_ids = [row[0] for row in c.fetchall()]
        
        for bid in b_ids:
            c.execute("DELETE FROM competitors WHERE brand_id = ?", (bid,))
            
        c.execute("DELETE FROM brands WHERE org_id = ?", (int(org_id),))
        c.execute("DELETE FROM organizations WHERE id = ?", (int(org_id),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error deleting: {e}")
        return False

def get_brands(org_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM brands WHERE org_id = ? ORDER BY name", conn, params=(int(org_id),))
    conn.close()
    return df

def add_brand(org_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Check duplicate in this org
        c.execute("SELECT id FROM brands WHERE org_id = ? AND LOWER(name) = ?", (int(org_id), name.strip().lower()))
        if c.fetchone():
            return None
            
        c.execute("INSERT INTO brands (org_id, name) VALUES (?, ?)", (int(org_id), name.strip()))
        conn.commit()
        brand_id = c.lastrowid
        conn.close()
        return brand_id
    except Exception as e:
        conn.close()
        st.error(f"Error adding brand: {e}")
        return None

def rename_brand(brand_id, new_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        # Get org_id to check duplicate
        c.execute("SELECT org_id FROM brands WHERE id = ?", (int(brand_id),))
        row = c.fetchone()
        if not row: return False
        org_id = row[0]
        
        c.execute("SELECT id FROM brands WHERE org_id = ? AND LOWER(name) = ? AND id != ?", (org_id, new_name.strip().lower(), int(brand_id)))
        if c.fetchone():
            return False
            
        c.execute("UPDATE brands SET name = ? WHERE id = ?", (new_name.strip(), int(brand_id)))
        # Update primary competitor tag name if it matches old name? 
        # Actually user wants "Update the keywords to look up", usually we keep primary tag synced.
        # Let's update the primary competitor record name too.
        c.execute("UPDATE competitors SET name = ? WHERE brand_id = ? AND is_primary = 1", (new_name.strip(), int(brand_id)))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error renaming brand: {e}")
        return False

def delete_brand(brand_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM competitors WHERE brand_id = ?", (int(brand_id),))
        c.execute("DELETE FROM brands WHERE id = ?", (int(brand_id),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error deleting brand: {e}")
        return False

def get_competitors(brand_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM competitors WHERE brand_id = ? ORDER BY is_primary DESC, id ASC", conn, params=(int(brand_id),))
    conn.close()
    return df

def update_competitor_tags(brand_id, brand_keywords, competitors_list):
    # competitors_list is a list of dicts: [{'name': '...', 'keywords': '...'}]
    brand_id = int(brand_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM competitors WHERE brand_id = ?", (brand_id,))
        
        # Insert Primary (Brand itself)
        c.execute("SELECT name FROM brands WHERE id = ?", (brand_id,))
        brand_row = c.fetchone()
        if brand_row:
            brand_name = brand_row[0]
            c.execute("INSERT INTO competitors (brand_id, name, keywords, is_primary) VALUES (?, ?, ?, 1)", 
                      (brand_id, brand_name, brand_keywords,))
        
        # Insert others
        for comp in competitors_list:
            c.execute("INSERT INTO competitors (brand_id, name, keywords, is_primary) VALUES (?, ?, ?, 0)", 
                      (brand_id, comp['name'], comp['keywords'],))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating tags: {e}")
        return False
    finally:
        conn.close()

# Initialize DB on import/run
init_db()

# --- Session State ---
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'competitor_analysis_done' not in st.session_state:
    st.session_state.competitor_analysis_done = False
if 'ui_competitor_rows' not in st.session_state:
    st.session_state.ui_competitor_rows = 1 

def hide_streamlit_ui():
    hide_css = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        </style>
    """
    st.markdown(hide_css, unsafe_allow_html=True)

hide_streamlit_ui()

# --- NLTK & Models ---
@st.cache_resource
def setup_nltk():
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        return True
    except Exception as e:
        st.error(f'Failed to download NLTK data: {e}')
        return False

setup_nltk()

try:
    stop_words = set(stopwords.words('english'))
except:
    stop_words = set() 
lemmatizer = WordNetLemmatizer()

# Lazy Loading Models
@st.cache_resource
def get_model(lang_code):
    model_name = None
    try:
        if lang_code == 'en':
            model_name = 'cardiffnlp/twitter-roberta-base-sentiment-latest'
        elif lang_code == 'si':
            model_name = 'sinhala-nlp/sinhala-sentiment-analysis-sinbert-small'
        elif lang_code == 'ta':
            model_name = 'Vasanth/tamil-sentiment-distilbert'
        
        if model_name:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            return tokenizer, model
    except Exception as e:
        st.error(f"Error loading {lang_code} model: {e}")
    return None

def detect_language(text):
    text_str = str(text)
    if any('\u0d80' <= char <= '\u0dff' for char in text_str):
        return 'si'
    elif any('\u0b80' <= char <= '\u0bff' for char in text_str):
        return 'ta'
    else:
        return 'en'

def get_transformer_sentiment(text, lang_code):
    pair = get_model(lang_code)
    if not pair:
        return 'Neutral', 0.0
    
    tokenizer, model = pair
    try:
        inputs = tokenizer(str(text), return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = F.softmax(logits, dim=1)[0]
        id2label = getattr(model.config, 'id2label', {})
        idx_pos = 2
        idx_neg = 0
        if lang_code == 'en':
            idx_neg = 0
            idx_pos = 2
        elif lang_code == 'si':
            idx_neg = 2
            idx_pos = 1
        elif lang_code == 'ta':
            if len(probs) >= 3:
                 idx_neg, idx_pos = 0, 2
            elif len(probs) == 2:
                 idx_neg, idx_pos = 0, 1
            for i in range(len(probs)):
                lbl = id2label.get(i, str(i)).lower()
                if 'pos' in lbl:
                    idx_pos = i
                elif 'neg' in lbl:
                    idx_neg = i
        p_pos = probs[idx_pos].item()
        p_neg = probs[idx_neg].item()
        score = p_pos - p_neg
        if score < 0:
            sentiment = 'Negative'
        elif score <= 0.1:
            sentiment = 'Neutral'
        else:
            sentiment = 'Positive'
        return sentiment, score
    except Exception as e:
        return 'Neutral', 0.0

def analyze_text(text):
    if pd.isna(text) or text is None or str(text).strip() == '':
        return 'Unknown', 'Undefined', 0.0
    lang = detect_language(text)
    if lang == 'en':
        s, sc = get_transformer_sentiment(text, 'en')
        return 'English', s, sc
    elif lang == 'si':
        s, sc = get_transformer_sentiment(text, 'si')
        return 'Sinhala', s, sc
    elif lang == 'ta':
        s, sc = get_transformer_sentiment(text, 'ta')
        return 'Tamil', s, sc
    return 'Other', 'Neutral', 0.0

# --- Main App ---
st.title('🧩 Brand Sentiment Analyzer (CSV)')

if st.button('🗑️ Clear All Data'):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

st.subheader('1. Organization & Brand Setup')
col_org, col_brand = st.columns(2)

# --- Org Logic ---
current_org_id = None

with col_org:
    orgs_df = get_organizations()
    org_list = orgs_df['name'].tolist() + ['➕ Create New Organization']
    
    selected_org = st.selectbox("Select Organization", org_list, key="sel_org")
    
    # Org MANAGE / CREATE
    if selected_org == '➕ Create New Organization':
        new_org_name = st.text_input("Enter New Organization Name")
        if st.button("Save Organization"):
            if new_org_name:
                if add_organization(new_org_name):
                    st.success(f"Organization '{new_org_name}' created!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to create organization (Duplicate?).")
            else:
                st.warning("Name cannot be empty.")
    elif selected_org:
        # Get ID
        org_row = orgs_df[orgs_df['name'] == selected_org]
        if not org_row.empty:
            current_org_id = int(org_row.iloc[0]['id'])
        
        # Org Management Expander
        with st.expander("⚙️ Manage Organization (Rename/Delete)"):
            ren_org_name = st.text_input("Rename to:", value=selected_org, key=f"ren_org_val_{selected_org}")
            if st.button("Update Name", key="btn_ren_org"):
                if rename_organization(current_org_id, ren_org_name):
                     st.success("Renamed successfully.")
                     time.sleep(1)
                     st.rerun()
                else:
                    st.error("Failed (Name exists?)")
            
            st.markdown("---")
            st.warning("Deleting will delete all brands and data inside!")
            if st.checkbox("Confirm Delete Org", key="chk_del_org"):
                if st.button("Delete Organization", type="primary"):
                    if delete_organization(current_org_id):
                        st.success("Deleted.")
                        time.sleep(1)
                        st.rerun()

# --- Brand Logic ---
current_brand_id = None
current_brand_name = None

with col_brand:
    if current_org_id:
        brands_df = get_brands(current_org_id)
        brand_list = brands_df['name'].tolist() + ['➕ Create New Brand']
        
        def reset_brand_form():
            st.session_state.ui_extra_comp_rows = 1
            # Explicitly clear new brand inputs if they exist
            # Note: We use the exact key string we will define below
            pfx = "➕ Create New Brand"
            keys_to_clear = [f"main_b_name_input_{pfx}", f"main_b_kws_input_{pfx}"]
            # Also clear any dynamic comp keys for the new brand? 
            # It's harder to predict all comp keys, but resetting ui_extra_comp_rows helps.
            # Streamlit might purge unused keys eventually, or we accept they persist per session.
            # But the 'Main' ones are critical.
            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]

        selected_brand = st.selectbox("Select Brand", brand_list, key="sel_brand", on_change=reset_brand_form)
        
        if selected_brand == '➕ Create New Brand':
            # new_brand_name = st.text_input("Enter New Brand Name") 
            # Removed redundant input (User wants form below)
            st.info("Fill Brand Details below & Save.")
        else:
             b_row = brands_df[brands_df['name'] == selected_brand]
             if not b_row.empty:
                 current_brand_id = int(b_row.iloc[0]['id'])
                 current_brand_name = b_row.iloc[0]['name']
                 
             # Brand Management Expander
             with st.expander("⚙️ Manage Brand (Rename/Delete)"):
                 ren_b_name = st.text_input("Rename to:", value=selected_brand, key=f"ren_b_val_{selected_brand}")
                 if st.button("Update Name", key="btn_ren_b"):
                      if rename_brand(current_brand_id, ren_b_name):
                           st.success("Renamed.")
                           time.sleep(1)
                           st.rerun()
                      else:
                           st.error("Failed (Name exists?)")
                 st.markdown("---")
                 if st.checkbox("Confirm Delete Brand", key="chk_del_b"):
                      if st.button("Delete Brand", type="primary"):
                           if delete_brand(current_brand_id):
                                st.success("Deleted.")
                                time.sleep(1)
                                st.rerun()

# --- Brand Setup / Edit Form ---
# LOGIC FIX: Show form if creating new OR if existing brand selected
show_brand_form = False
is_new_brand = False

if selected_org and selected_org != '➕ Create New Organization':
    if selected_brand == '➕ Create New Brand':
        show_brand_form = True
        is_new_brand = True
    elif selected_brand:
        show_brand_form = True
        is_new_brand = False

if show_brand_form:
    st.markdown("---")
    header_text = "New Brand Details" if is_new_brand else f"Editing: {current_brand_name}"
    st.subheader(header_text)
    
    form_brand_name = ""
    form_brand_kws = ""
    form_competitors = [] 
    
    if is_new_brand:
        # if 'new_brand_name' in locals(): form_brand_name = new_brand_name 
        # No longer pulling from above, user enters in form
        pass
    else:
        form_brand_name = current_brand_name
        if current_brand_id:
            comps_df = get_competitors(current_brand_id)
            primary = comps_df[comps_df['is_primary'] == 1]
            others = comps_df[comps_df['is_primary'] == 0]
            if not primary.empty:
                form_brand_kws = primary.iloc[0]['keywords']
            for idx, row in others.iterrows():
                form_competitors.append({'name': row['name'], 'keywords': row['keywords']})

    with st.container():
        # Layout: Name and Keywords side by side
        c_main_1, c_main_2 = st.columns(2)
        
        # Dynamic Key Suffix to ensure uniqueness per brand
        key_sfx = str(selected_brand)
        
        # Brand Name (Read-only if existing, editable if new)
        f_b_name = c_main_1.text_input("Brand Name", value=form_brand_name, disabled=(not is_new_brand), key=f"main_b_name_input_{key_sfx}", placeholder="Enter Brand Name")
        
        # Brand Keywords
        f_b_kws = c_main_2.text_input(f"Keywords for {f_b_name if f_b_name else 'Brand'} (Self)", value=form_brand_kws, placeholder="comma, separated, keywords", key=f"main_b_kws_input_{key_sfx}")
        
        st.markdown("##### Competitors")
        
        updated_comps = []
        
        # Header Row for alignment
        h1, h2, h3 = st.columns([3, 4, 1])
        h1.markdown("**Name**")
        h2.markdown("**Keywords**")
        h3.markdown("**Del**")
        
        # Existing Comp List
        for i, comp in enumerate(form_competitors):
            c1, c2, c3 = st.columns([3, 4, 1])
            c_name = c1.text_input(f"Competitor {i+1} Name", value=comp['name'], key=f"c_name_{i}_{key_sfx}", label_visibility="collapsed")
            c_kws = c2.text_input(f"Competitor {i+1} Keywords", value=comp['keywords'], key=f"c_kw_{i}_{key_sfx}", label_visibility="collapsed")
            # Using label_visibility='collapsed' to avoid labels pushing content down if we used headers
            # Checkbox needs to be centered roughly or just there.
            c_del = c3.checkbox("Delete", key=f"del_c_{i}_{key_sfx}", label_visibility="collapsed")
            
            if not c_del:
                updated_comps.append({'name': c_name, 'keywords': c_kws})
        
        # New Lines
        if 'ui_extra_comp_rows' not in st.session_state:
            st.session_state.ui_extra_comp_rows = 1
            
        for j in range(st.session_state.ui_extra_comp_rows):
            idx = len(form_competitors) + j
            c1, c2, c3 = st.columns([3, 4, 1]) # Add 3rd col for spacing consistency
            new_c_name = c1.text_input(f"New Competitor {j+1} Name", key=f"new_c_name_{idx}_{key_sfx}", placeholder="New Competitor Name", label_visibility="collapsed")
            new_c_kw = c2.text_input(f"New Competitor {j+1} Keywords", key=f"new_c_kw_{idx}_{key_sfx}", placeholder="Keywords", label_visibility="collapsed")
            
            if new_c_name or new_c_kw:
                 updated_comps.append({'name': new_c_name, 'keywords': new_c_kw})
        
        if st.button("➕ Add Another Competitor"):
            st.session_state.ui_extra_comp_rows += 1
            st.rerun()
        
        st.markdown("---")
        btn_label = "Save Brand Details" if is_new_brand else "Update Brand Details"
        
        if st.button(f"💾 {btn_label}", type="primary"):
            if not f_b_name:
                st.error("Brand Name is required.")
            elif not f_b_kws:
                st.error("Brand Keywords are required.")
            else:
                if is_new_brand:
                    # Create
                    b_id = add_brand(current_org_id, f_b_name)
                    if b_id:
                        if update_competitor_tags(b_id, f_b_kws, updated_comps):
                            st.success("Brand created!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Failed to create Brand (Duplicate?).")
                else:
                    # Update
                    if update_competitor_tags(current_brand_id, f_b_kws, updated_comps):
                        st.success("Updated!")
                        time.sleep(1)
                        st.rerun()

# --- Analysis & Result ---
if current_brand_id and not is_new_brand:
    st.header(f"Analysis for: {current_brand_name}")
    st.subheader('2. Upload Data')
    
    def reset_analysis_state():
        st.session_state.raw_data = None
        st.session_state.processed_data = None
        st.session_state.analysis_complete = False
        st.session_state.source_files = []

    uploaded_files = st.file_uploader('Upload CSV file(s)', type=['csv'], accept_multiple_files=True, on_change=reset_analysis_state)
    
    if uploaded_files:
        if st.session_state.raw_data is None:
            dfs = []
            for f in uploaded_files:
                try:
                    try:
                        df_temp = pd.read_csv(f)
                        if len(df_temp.columns) <= 1:
                            f.seek(0)
                            df_temp = pd.read_csv(f, sep=';')
                    except:
                        f.seek(0)
                        df_temp = pd.read_csv(f, sep=None, engine='python')
                    
                    if 'source_files' not in st.session_state: st.session_state.source_files = []
                    st.session_state.source_files.append(f.name)
                    dfs.append(df_temp)
                except Exception as e: st.error(f'Error reading {f.name}: {e}')
            if dfs:
                st.session_state.raw_data = pd.concat(dfs, ignore_index=True)
                st.success(f'Successfully loaded {len(st.session_state.raw_data)} rows.')
                if 'source_files' not in st.session_state: st.session_state.source_files = ["uploaded_data"]

    if st.session_state.raw_data is not None:
        main_df = st.session_state.raw_data.copy()
        st.subheader('3. Data Preview')
        st.dataframe(main_df.head(), use_container_width=True)
        st.subheader('4. Clean Data')
        all_cols = main_df.columns.tolist()
        defaults_to_remove = [c for c in ['Sentiment', 'Sentiment points'] if c in all_cols]
        cols_to_remove = st.multiselect('Select columns to remove:', options=all_cols, default=defaults_to_remove)
        
        st.subheader('5. Analysis Settings')
        available_cols = [c for c in all_cols if c not in cols_to_remove]
        default_idx = 0
        if 'Content of posts' in available_cols: default_idx = available_cols.index('Content of posts')
        content_col = st.selectbox('Select column containing text to analyze:', available_cols, index=default_idx)
        
        if st.button('🚀 Find Sentiment'):
            if cols_to_remove: analysis_df = main_df.drop(columns=cols_to_remove)
            else: analysis_df = main_df.copy()
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_lang, results_sent, results_score = [], [], []
            total = len(analysis_df)
            
            for i, row in analysis_df.iterrows():
                text = row[content_col]
                lang, sentiment, score = analyze_text(text)
                results_lang.append(lang)
                results_sent.append(sentiment)
                results_score.append(score)
                if i % 10 == 0:
                    status_text.text(f'Processing row {i + 1}/{total}...')
                    progress_bar.progress((i + 1) / total)
            
            progress_bar.progress(1.0)
            status_text.text('Analysis Complete!')
            analysis_df['detected_language'] = results_lang
            analysis_df['new_sentiment'] = results_sent
            analysis_df['sentiment_score'] = results_score
            
            # Tagger
            comps_db = get_competitors(current_brand_id)
            valid_tags = []
            for _, r in comps_db.iterrows():
                kws = [k.strip() for k in r['keywords'].split(',')]
                valid_tags.append({'tag': r['name'], 'keywords': kws})
            
            if valid_tags:
                status_text.text('Tagging Competitors...')
                competitor_column = []
                search_col = content_col
                candidates = [c for c in analysis_df.columns if 'keyword' in c.lower()]
                if candidates: search_col = candidates[0]
                if 'Keywords' in analysis_df.columns: search_col = 'Keywords'
                
                for index, row in analysis_df.iterrows():
                    cell_text = str(row[search_col]) if pd.notna(row[search_col]) else ''
                    tokens = [t.strip() for t in cell_text.split(',')]
                    assigned = 'Other'
                    found = False
                    for token in tokens:
                        for tag_obj in valid_tags:
                            for kw in tag_obj['keywords']:
                                if kw.lower() in token.lower():
                                    assigned = tag_obj['tag']
                                    found = True
                                    break
                            if found: break
                        if found: break
                    competitor_column.append(assigned)
                analysis_df['competitor'] = competitor_column
            
            analysis_df.columns = [str(c).strip().replace(' ', '_').lower() for c in analysis_df.columns]
            st.session_state.processed_data = analysis_df
            st.session_state.analysis_complete = True
            st.rerun()

    if st.session_state.analysis_complete and st.session_state.processed_data is not None:
        final_df = st.session_state.processed_data
        st.subheader('6. Result Preview')
        st.dataframe(final_df.head(), use_container_width=True)
        st.subheader('7. Sentiment Distribution')
        if 'new_sentiment' in final_df.columns and 'competitor' in final_df.columns:
             # Use columns for side-by-side charts
             chart_col1, chart_col2 = st.columns(2)
             
             with chart_col1:
                 counts = final_df['new_sentiment'].value_counts().reset_index()
                 counts.columns = ['Sentiment', 'Count']
                 colors = {'Positive': '#2E8B57', 'Negative': '#DC143C', 'Neutral': '#808080', 'Undefined': '#000000'}
                 fig = px.pie(counts, values='Count', names='Sentiment', hole=0.4, color='Sentiment', color_discrete_map=colors, title=f'Sentiment for {current_brand_name}')
                 st.plotly_chart(fig, use_container_width=True)
                 
             with chart_col2:
                 comp_counts = final_df['competitor'].value_counts().reset_index()
                 comp_counts.columns = ['Competitor', 'Count']
                 fig_c = px.pie(comp_counts, values='Count', names='Competitor', hole=0.4, title='Competitor Share')
                 st.plotly_chart(fig_c, use_container_width=True)
        elif 'new_sentiment' in final_df.columns:
            # Fallback if only sentiment
            counts = final_df['new_sentiment'].value_counts().reset_index()
            counts.columns = ['Sentiment', 'Count']
            colors = {'Positive': '#2E8B57', 'Negative': '#DC143C', 'Neutral': '#808080', 'Undefined': '#000000'}
            fig = px.pie(counts, values='Count', names='Sentiment', hole=0.4, color='Sentiment', color_discrete_map=colors, title=f'Sentiment for {current_brand_name}')
            st.plotly_chart(fig, use_container_width=True)


        st.subheader('Download Data')
        base_name = "output"
        if 'source_files' in st.session_state and st.session_state.source_files:
            first_file = st.session_state.source_files[0]
            base_name = os.path.splitext(first_file)[0]
        dl_name = f"analyzed_{base_name}.csv"
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(label='⬇️ Download Output CSV', data=csv, file_name=dl_name, mime='text/csv')

st.markdown("---")
st.markdown("""<div style="text-align: center; color: grey;">Created by @djslash9 - 2026</div>""", unsafe_allow_html=True)