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

def hide_streamlit_ui():
    hide_menu_and_footer_css = '\n        <style>\n        #MainMenu {display: none;}\n        footer {display: none;}\n        /* [data-testid="stToolbar"] {display: none;} */ /* Temporarily unhide toolbar to see if it helps, though specific control is targeted below */\n        \n        [data-testid="stSidebarCollapsedControl"] {\n            display: block !important;\n            visibility: visible !important;\n            color: #000000 !important;\n            fill: #000000 !important;\n            background-color: rgba(255, 255, 255, 0.5) !important;\n            z-index: 1000002 !important;\n            position: fixed !important;\n            top: 2rem !important;\n            left: 1rem !important;\n        }\n        \n        /* Specific targeting for the button inside if needed, or SVG */\n        [data-testid="stSidebarCollapsedControl"] svg {\n            fill: #000000 !important;\n            stroke: #000000 !important;\n        }\n        \n        [data-testid="stHeader"] {\n            z-index: 999999 !important;\n        }\n        </style>\n    '
    st.markdown(hide_menu_and_footer_css, unsafe_allow_html=True)
hide_streamlit_ui()

@st.cache_resource
def download_nltk_data():
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        return True
    except Exception as e:
        st.error(f'Failed to download NLTK data: {e}')
        return False
if not download_nltk_data():
    st.stop()

@st.cache_resource
def load_sinhala_model():
    try:
        model_name = 'sinhala-nlp/sinhala-sentiment-analysis-sinbert-small'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        return (tokenizer, model)
    except Exception as e:
        st.error(f'Failed to load Sinhala model: {e}. Please check connection/model name.')
        return (None, None)
tokenizer, model = load_sinhala_model()
if not tokenizer or not model:
    st.error('Application cannot start without the Sinhala model.')
    st.stop()
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
sia = SentimentIntensityAnalyzer()
label_map = {0: 'Neutral', 1: 'Positive', 2: 'Negative'}
if 'log' not in st.session_state:
    st.session_state.log = []
if 'main_df' not in st.session_state:
    st.session_state.main_df = None
if 'analyzed_df' not in st.session_state:
    st.session_state.analyzed_df = None

def log_message(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    st.session_state.log.append(f'[{timestamp}] {message}')

def detect_language(text):
    sinhala_unicode_range = any(('\u0d80' <= c <= '\u0dff' for c in str(text)))
    return 'si' if sinhala_unicode_range else 'en'

def clean_text(text):
    try:
        text = str(text).lower()
        text = re.sub('http\\S+|www\\S+', '', text)
        text = re.sub('<.*?>', '', text)
        text = text.translate(str.maketrans('', '', string.punctuation))
        tokens = nltk.word_tokenize(text)
        tokens = [lemmatizer.lemmatize(w) for w in tokens if w.isalpha() and w not in stop_words]
        cleaned = ' '.join(tokens)
        return cleaned if cleaned.strip() else str(text)
    except Exception:
        return str(text)

def get_english_sentiment(text):
    cleaned_text = clean_text(text)
    score = sia.polarity_scores(cleaned_text)['compound']
    if score >= 0.05:
        return 'Positive'
    elif score <= -0.05:
        return 'Negative'
    else:
        return 'Neutral'

def predict_sinhala_sentiment(text):
    try:
        inputs = tokenizer(str(text), return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = F.softmax(logits, dim=1)[0]
        idx = torch.argmax(probs).item()
        return label_map[idx]
    except Exception:
        return 'Neutral'

def get_final_sentiment(text):
    lang = detect_language(text)
    if lang == 'en':
        return get_english_sentiment(text)
    elif lang == 'si':
        return predict_sinhala_sentiment(text)
    else:
        return 'Neutral'

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def app():
    st.markdown('<h1 style="text-align: center; color: #002b5c;">🧠 Sprout Social Sentiment Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('Upload one or more CSV files to perform sentiment analysis. All files will be merged and analyzed as one.')
    uploaded_files = st.file_uploader('📂 Choose CSV files', type='csv', accept_multiple_files=True)
    if uploaded_files:
        log_message('New file(s) detected. Loading and merging...')
        dfs = []
        try:
            for file in uploaded_files:
                log_message(f'Loading {file.name}...')
                dfs.append(pd.read_csv(file))
            if dfs:
                st.session_state.main_df = pd.concat(dfs, ignore_index=True)
                st.session_state.analyzed_df = None
                log_message(f'All {len(dfs)} file(s) merged successfully into {len(st.session_state.main_df)} rows.')
                st.success(f'🎉 {len(dfs)} file(s) loaded and merged into {len(st.session_state.main_df)} rows.')
            else:
                st.session_state.main_df = None
        except Exception as e:
            log_message(f'Error loading files: {e}')
            st.error(f'An error occurred during file loading: {e}')
            st.session_state.main_df = None
    if st.session_state.main_df is not None:
        df = st.session_state.main_df
        st.subheader('📝 Merged Data Preview')
        st.dataframe(df.head())
        st.subheader('⚙️ Analysis Configuration')
        col1, col2 = st.columns(2)
        with col1:
            all_cols = list(df.columns)
            default_remove = ['Sentiment'] if 'Sentiment' in all_cols else []
            columns_to_remove = st.multiselect('🗑️ Select columns to remove', options=all_cols, default=default_remove)
        with col2:
            columns_to_analyze = [col for col in df.columns if df[col].dtype in ['object', 'string']]
            default_analyze_index = 0
            if 'Message' in columns_to_analyze:
                default_analyze_index = columns_to_analyze.index('Message')
            selected_column = st.selectbox('✍️ Select the column to analyze', options=columns_to_analyze, index=default_analyze_index, help='This is the column containing the text you want to analyze.')
        if st.button('🚀 Analyze Sentiment', use_container_width=True, type='primary'):
            if selected_column:
                log_message(f"Starting analysis on column '{selected_column}'.")
                analysis_df = df.copy()
                if columns_to_remove:
                    analysis_df = analysis_df.drop(columns=columns_to_remove, errors='ignore')
                    log_message(f"Removed columns: {', '.join(columns_to_remove)}")
                if selected_column not in analysis_df.columns:
                    st.error(f"The selected column '{selected_column}' was removed. Please re-select.")
                    log_message(f"Error: Analysis column '{selected_column}' was in the removal list.")
                else:
                    with st.status('Analyzing sentiments... (This may take a moment)', expanded=True) as status:
                        total_rows = len(analysis_df)
                        analysis_df['Sentiment'] = None
                        start_time = time.time()
                        for i, row in analysis_df.iterrows():
                            text = row[selected_column]
                            sentiment = get_final_sentiment(text)
                            analysis_df.at[i, 'Sentiment'] = sentiment
                            if (i + 1) % 100 == 0 or i == total_rows - 1:
                                status.update(label=f'Processing row {i + 1}/{total_rows}...')
                        end_time = time.time()
                        duration = end_time - start_time
                        log_message(f'Analysis complete! (Took {duration:.2f} seconds)')
                        status.update(label=f'✅ Analysis complete! (Took {duration:.2f} seconds)', state='complete')
                    st.session_state.analyzed_df = analysis_df
            else:
                st.warning('Please select a column to analyze.')
                log_message('Analysis button clicked but no column selected.')
    if st.session_state.analyzed_df is not None:
        st.subheader('✅ Analyzed Data')
        st.data_editor(st.session_state.analyzed_df, use_container_width=True, height=350, num_rows='dynamic')
        st.subheader('📈 Sentiment Distribution')
        sentiment_counts = st.session_state.analyzed_df['Sentiment'].value_counts()
        col1, col2 = st.columns([0.6, 0.4])
        with col1:
            st.bar_chart(sentiment_counts, use_container_width=True)
        with col2:
            if not sentiment_counts.empty:
                fig = px.pie(sentiment_counts, values=sentiment_counts.values, names=sentiment_counts.index, title='Sentiment Breakdown', color_discrete_map={'Positive': '#2ca02c', 'Negative': '#d62728', 'Neutral': '#1f77b4'})
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write('No sentiment data to display in chart.')
        csv_data = convert_df_to_csv(st.session_state.analyzed_df)
        today_date = datetime.now().strftime('%Y-%m-%d')
        download_file_name = f'analyzed_sentiments_{today_date}.csv'
        st.download_button(label='⬇️ Download Analyzed CSV', data=csv_data, file_name=download_file_name, mime='text/csv', use_container_width=True, key='download_button')
    if st.session_state.log:
        with st.expander('Show Process Log', expanded=False):
            st.text_area('Log', value='\\n'.join(st.session_state.log), height=300, disabled=True, key='log_area')
    elif not uploaded_files:
        st.info('Please upload one or more CSV files to begin analysis.')
    st.markdown('---')
    st.markdown("\n        <div style='text-align: center; color: #666; margin-top: 2rem; margin-bottom: 2rem;'>\n            <p>Created by @djslash9 | 2025</p>\n        </div>\n        ", unsafe_allow_html=True)