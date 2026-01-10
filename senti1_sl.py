import streamlit as st
import pandas as pd
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import time
from datetime import datetime
import plotly.express as px
st.set_page_config(page_title='Multi-Language Sentiment Analyzer (En/Si/Ta)', layout='wide', page_icon='🧠')
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'competitor_tags' not in st.session_state:
    st.session_state.competitor_tags = []
if 'competitor_analysis_done' not in st.session_state:
    st.session_state.competitor_analysis_done = False
if 'num_tag_rows' not in st.session_state:
    st.session_state.num_tag_rows = 1

def hide_streamlit_ui():
    hide_css = '\n        <style>\n        #MainMenu {display: none;}\n        footer {display: none;}\n        </style>\n    '
    st.markdown(hide_css, unsafe_allow_html=True)
hide_streamlit_ui()

@st.cache_resource
def setup_nltk():
    try:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('omw-1.4')
        return True
    except Exception as e:
        st.error(f'Failed to download NLTK data: {e}')
        return False
if not setup_nltk():
    st.stop()

@st.cache_resource
def load_models():
    models = {}
    try:
        en_model_name = 'cardiffnlp/twitter-roberta-base-sentiment-latest'
        en_tokenizer = AutoTokenizer.from_pretrained(en_model_name)
        en_model = AutoModelForSequenceClassification.from_pretrained(en_model_name)
        models['en'] = (en_tokenizer, en_model)
    except Exception as e:
        st.error(f'Error loading English model: {e}')
        models['en'] = None
    try:
        si_model_name = 'sinhala-nlp/sinhala-sentiment-analysis-sinbert-small'
        si_tokenizer = AutoTokenizer.from_pretrained(si_model_name)
        si_model = AutoModelForSequenceClassification.from_pretrained(si_model_name)
        models['si'] = (si_tokenizer, si_model)
    except Exception as e:
        st.error(f'Error loading Sinhala model: {e}')
        models['si'] = None
    try:
        ta_model_name = 'Vasanth/tamil-sentiment-distilbert'
        ta_tokenizer = AutoTokenizer.from_pretrained(ta_model_name)
        ta_model = AutoModelForSequenceClassification.from_pretrained(ta_model_name)
        models['ta'] = (ta_tokenizer, ta_model)
    except Exception as e:
        st.error(f'Error loading Tamil model: {e}')
        models['ta'] = None
    return models
models = load_models()
try:
    stop_words = set(stopwords.words('english'))
except:
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def detect_language(text):
    text_str = str(text)
    if any(('\u0d80' <= char <= '\u0dff' for char in text_str)):
        return 'si'
    elif any(('\u0b80' <= char <= '\u0bff' for char in text_str)):
        return 'ta'
    else:
        return 'en'

def get_transformer_sentiment(text, lang_code):
    if not models.get(lang_code):
        return ('Neutral', 0.0)
    tokenizer, model = models[lang_code]
    try:
        inputs = tokenizer(str(text), return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = F.softmax(logits, dim=1)[0]
        label_idx = torch.argmax(probs).item()
        id2label = getattr(model.config, 'id2label', {})
        predicted_label = id2label.get(label_idx, str(label_idx)).lower()
        idx_pos = 2
        idx_neg = 0
        if lang_code == 'en':
            idx_neg = 0
            idx_pos = 2
        elif lang_code == 'si':
            idx_neg = 2
            idx_pos = 1
        elif lang_code == 'ta':
            if 'positive' in predicted_label:
                idx_pos = label_idx
                pass
            elif 'negative' in predicted_label:
                idx_neg = label_idx
                pass
            if len(probs) == 2:
                idx_neg = 0
                idx_pos = 1
            elif len(probs) >= 3:
                idx_neg = 0
                idx_pos = 2
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
        return (sentiment, score)
    except Exception as e:
        return ('Neutral', 0.0)

def analyze_text(text):
    if pd.isna(text) or text is None or str(text).strip() == '':
        return ('Unknown', 'Undefined', 0.0)
    lang = detect_language(text)
    if lang == 'en':
        return (lang, *get_transformer_sentiment(text, 'en'))
    elif lang == 'si':
        return ('Sinhala', *get_transformer_sentiment(text, 'si'))
    elif lang == 'ta':
        return ('Tamil', *get_transformer_sentiment(text, 'ta'))
    return ('Other', 'Neutral', 0.0)
st.title('🧩 Brand Sentiment Analyzer (CSV)')
if st.button('🗑️ Clear All Data'):
    st.session_state.processed_data = None
    st.session_state.raw_data = None
    st.session_state.analysis_complete = False
    st.rerun()
brand_name = st.text_input('1. Enter Brand Name', placeholder='e.g., Dialog, Mobitel')
st.subheader('2. Upload Data')
uploaded_files = st.file_uploader('Upload CSV file(s)', type=['csv'], accept_multiple_files=True)
if uploaded_files:
    if st.session_state.raw_data is None:
        dfs = []
        for f in uploaded_files:
            try:
                try:
                    df_temp = pd.read_csv(f)
                    if len(df_temp.columns) <= 1:
                        raise ValueError('Likely not comma separated')
                except Exception:
                    f.seek(0)
                    df_temp = pd.read_csv(f, sep=';')
                dfs.append(df_temp)
            except Exception as e:
                try:
                    f.seek(0)
                    df_temp = pd.read_csv(f, sep=None, engine='python')
                    dfs.append(df_temp)
                except Exception as final_e:
                    st.error(f'Error reading {f.name}: {final_e}')
        if dfs:
            st.session_state.raw_data = pd.concat(dfs, ignore_index=True)
            st.success(f'Successfully loaded {len(st.session_state.raw_data)} rows.')
if st.session_state.raw_data is not None:
    main_df = st.session_state.raw_data.copy()
    st.subheader('3. Data Preview')
    st.dataframe(main_df.head())
    st.subheader('4. Clean Data')
    all_cols = main_df.columns.tolist()
    defaults_to_remove = [c for c in ['Sentiment', 'Sentiment points'] if c in all_cols]
    cols_to_remove = st.multiselect('Select columns to remove:', options=all_cols, default=defaults_to_remove)
    st.subheader('5. Analysis Settings')
    available_cols = [c for c in all_cols if c not in cols_to_remove]
    default_idx = 0
    if 'Content of posts' in available_cols:
        default_idx = available_cols.index('Content of posts')
    elif len(available_cols) > 0:
        default_idx = 0
    else:
        st.error('No columns available to analyze. Please uncheck some removed columns.')
        st.stop()
    content_col = st.selectbox('Select column containing text to analyze:', available_cols, index=default_idx)
    if st.button('🚀 Find Sentiment'):
        if not brand_name:
            st.warning('Please enter a Brand Name first.')
        else:
            if cols_to_remove:
                analysis_df = main_df.drop(columns=cols_to_remove)
            else:
                analysis_df = main_df.copy()
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_lang = []
            results_sent = []
            results_score = []
            total = len(analysis_df)
            for i, row in analysis_df.iterrows():
                text = row[content_col]
                lang, sentiment, score = analyze_text(text)
                results_lang.append(lang)
                results_sent.append(sentiment)
                results_score.append(score)
                if i % 10 == 0:
                    progress = (i + 1) / total
                    progress_bar.progress(progress)
                    status_text.text(f'Processing row {i + 1}/{total}...')
            progress_bar.progress(1.0)
            status_text.text('Analysis Complete!')
            analysis_df['Detected_Language'] = results_lang
            analysis_df['New_Sentiment'] = results_sent
            analysis_df['Sentiment_Score'] = results_score
            st.session_state.processed_data = analysis_df
            st.session_state.analysis_complete = True
            st.rerun()
if st.session_state.analysis_complete and st.session_state.processed_data is not None:
    final_df = st.session_state.processed_data
    st.subheader('7. Analysis Results')
    st.dataframe(final_df.head())
    st.subheader('Sentiment Distribution')
    try:
        counts = final_df['New_Sentiment'].value_counts().reset_index()
        counts.columns = ['Sentiment', 'Count']
        colors = {'Positive': '#2E8B57', 'Negative': '#DC143C', 'Neutral': '#808080', 'Undefined': '#000000'}
        title_text = f'Sentiment Analysis for {brand_name}' if brand_name else 'Sentiment Analysis Results'
        fig = px.bar(counts, x='Sentiment', y='Count', color='Sentiment', color_discrete_map=colors, title=title_text)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning('Could not create chart.')
    st.subheader('8. Tag Keywords')
    competitor_tags_list = []
    for i in range(st.session_state.num_tag_rows):
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            kw_val = st.text_area(f'Paste Keywords (comma separated) #{i + 1}', key=f'kw_input_{i}', height=100)
        with col_k2:
            tag_val = st.text_input(f'Tag Name #{i + 1}', key=f'tag_input_{i}')
    if st.button('Add New Keywords'):
        st.session_state.num_tag_rows += 1
        st.rerun()
    if st.button('Assign Tags for Competitors'):
        valid_tags = []
        for i in range(st.session_state.num_tag_rows):
            k_key = f'kw_input_{i}'
            t_key = f'tag_input_{i}'
            if k_key in st.session_state and t_key in st.session_state:
                k_val = st.session_state[k_key]
                t_val = st.session_state[t_key]
                if k_val and t_val:
                    kw_list = [k.strip() for k in k_val.split(',') if k.strip()]
                    if kw_list:
                        valid_tags.append({'tag': t_val, 'keywords': kw_list})
        if not valid_tags:
            st.warning('No valid tags defined. Please enter keywords and tag names.')
        else:
            search_col = None
            if 'Keywords' in final_df.columns:
                search_col = 'Keywords'
            else:
                candidates = [c for c in final_df.columns if 'keyword' in c.lower()]
                if candidates:
                    search_col = candidates[0]
                else:
                    search_col = content_col
            st.info(f'Searching in column: {search_col}')
            competitor_column = []
            for index, row in final_df.iterrows():
                cell_text = str(row[search_col]) if pd.notna(row[search_col]) else ''
                tokens = [t.strip() for t in cell_text.split(',')]
                assigned_competitor = 'Other'
                found_match = False
                for token in tokens:
                    for tag_obj in valid_tags:
                        for kw in tag_obj['keywords']:
                            if kw.lower() in token.lower():
                                assigned_competitor = tag_obj['tag']
                                found_match = True
                                break
                        if found_match:
                            break
                    if found_match:
                        break
                competitor_column.append(assigned_competitor)
            final_df['Competitor'] = competitor_column
            st.session_state.processed_data = final_df
            st.session_state.competitor_analysis_done = True
            st.rerun()
    if st.session_state.competitor_analysis_done and 'Competitor' in final_df.columns:
        st.subheader('Competitor Distribution')
        try:
            comp_counts = final_df['Competitor'].value_counts().reset_index()
            comp_counts.columns = ['Competitor', 'Count']
            fig_comp = px.pie(comp_counts, values='Count', names='Competitor', title='Competitor Share')
            st.plotly_chart(fig_comp, use_container_width=True)
        except Exception as e:
            st.warning(f'Could not create competitor chart: {e}')
    st.subheader('9. Download Data')
    csv = final_df.to_csv(index=False).encode('utf-8')
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_name = f'sent1_sl_{date_str}.csv'
    st.download_button(label='⬇️ Download Output CSV', data=csv, file_name=file_name, mime='text/csv')