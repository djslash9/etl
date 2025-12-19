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

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="Multi-Language Sentiment Analyzer (En/Si/Ta)",
    layout="wide",
    page_icon="🧠"
)

# --- Session State Initialization ---
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# --- Hide Default Streamlit Elements ---
def hide_streamlit_ui():
    """Hides the default Streamlit footer and menu."""
    hide_css = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        </style>
    """
    st.markdown(hide_css, unsafe_allow_html=True)

hide_streamlit_ui()

# --- Setup and NLTK Downloads ---
# --- Setup and NLTK Downloads ---
@st.cache_resource
def setup_nltk():
    """Downloads necessary NLTK data."""
    try:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('omw-1.4')
        return True
    except Exception as e:
        st.error(f"Failed to download NLTK data: {e}")
        return False

if not setup_nltk():
    st.stop()

# --- Model Loading ---
@st.cache_resource
def load_models():
    """Loads English, Sinhala, and Tamil sentiment models."""
    models = {}
    
    # 1. English Model (RoBERTa)
    try:
        # Using a model specific for Tweet sentiment for better accuracy on social media
        en_model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        en_tokenizer = AutoTokenizer.from_pretrained(en_model_name)
        en_model = AutoModelForSequenceClassification.from_pretrained(en_model_name)
        models['en'] = (en_tokenizer, en_model)
    except Exception as e:
        st.error(f"Error loading English model: {e}")
        models['en'] = None
    
    # 2. Sinhala Model
    try:
        si_model_name = "sinhala-nlp/sinhala-sentiment-analysis-sinbert-small"
        si_tokenizer = AutoTokenizer.from_pretrained(si_model_name)
        si_model = AutoModelForSequenceClassification.from_pretrained(si_model_name)
        models['si'] = (si_tokenizer, si_model)
    except Exception as e:
        st.error(f"Error loading Sinhala model: {e}")
        models['si'] = None

    # 3. Tamil Model
    try:
        # Switching to a valid public model
        ta_model_name = "Vasanth/tamil-sentiment-distilbert"
        ta_tokenizer = AutoTokenizer.from_pretrained(ta_model_name)
        ta_model = AutoModelForSequenceClassification.from_pretrained(ta_model_name)
        models['ta'] = (ta_tokenizer, ta_model)
    except Exception as e:
        st.error(f"Error loading Tamil model: {e}")
        models['ta'] = None
        
    return models

models = load_models()

# --- Helpers ---
try:
    stop_words = set(stopwords.words("english"))
except:
    nltk.download('stopwords')
    stop_words = set(stopwords.words("english"))
    
lemmatizer = WordNetLemmatizer()

def detect_language(text):
    """
    Detects language based on Unicode ranges.
    Returns: 'si' (Sinhala), 'ta' (Tamil), or 'en' (English/Other).
    """
    text_str = str(text)
    # Check for Sinhala Unicode Block (0D80–0DFF)
    if any('\u0d80' <= char <= '\u0dff' for char in text_str):
        return 'si'
    # Check for Tamil Unicode Block (0B80–0BFF)
    elif any('\u0b80' <= char <= '\u0bff' for char in text_str):
        return 'ta'
    else:
        return 'en'

def get_transformer_sentiment(text, lang_code):
    """Returns (Sentiment Label, Score) using Hugging Face models."""
    if not models.get(lang_code):
        return "Neutral", 0.0
    
    tokenizer, model = models[lang_code]
    try:
        inputs = tokenizer(str(text), return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
        
        probs = F.softmax(logits, dim=1)[0]
        label_idx = torch.argmax(probs).item()
        
        # Get label from model config if available
        id2label = getattr(model.config, 'id2label', {})
        predicted_label = id2label.get(label_idx, str(label_idx)).lower()
        
        # Identify Positive and Negative prob indices
        # default to common 3-class indices if not found: 0=Neg, 1=Neu, 2=Pos (RoBERTa style)
        idx_pos = 2
        idx_neg = 0
        
        # Determine indices based on language/model knowledge
        if lang_code == 'en':
            # RoBERTa: 0=Neg, 1=Neu, 2=Pos
            idx_neg = 0
            idx_pos = 2
        elif lang_code == 'si':
            # SinBERT: 0=Neu, 1=Pos, 2=Neg
            idx_neg = 2
            idx_pos = 1
        elif lang_code == 'ta':
             # Vasanth/tamil-sentiment-distilbert
             # Inspect labels to find pos/neg
             # If binary or ternary, we need dynamic finding or hardcoded if known
             # Based on previous robust logic:
             if 'positive' in predicted_label:
                 idx_pos = label_idx
                 # Find negative simple way: index != label_idx
                 # This is risky if simpler logic worked before.
                 # Let's use the explicit checks I wrote before for safety.
                 pass
             elif 'negative' in predicted_label:
                 idx_neg = label_idx
                 pass

             # Fallback for Tamil if dynamic fails (assuming 3 class 0=Neg, 1=Neu, 2=Pos)
             # But if it's binary...
             if len(probs) == 2:
                 idx_neg = 0
                 idx_pos = 1
             elif len(probs) >= 3: 
                # Assuming standard 0=Neg, 1=Neu, 2=Pos if labels not clear
                idx_neg = 0
                idx_pos = 2
                
             # Refine via string search on id2label keys if possible
             # Iterate all labels to find indices
             for i in range(len(probs)):
                 lbl = id2label.get(i, str(i)).lower()
                 if 'pos' in lbl: idx_pos = i
                 elif 'neg' in lbl: idx_neg = i
        
        # Calculate Score: P(Pos) - P(Neg)
        p_pos = probs[idx_pos].item()
        p_neg = probs[idx_neg].item()
        score = p_pos - p_neg
        
        # Apply User Defined Thresholds for ALL languages
        # (-) Negative (even if -0.01) -> Negative
        # (+) positive but <0.1 -> Neutral
        # > 0.01 (assumed > 0.1 based on context) -> Positive
        
        if score < 0:
            sentiment = "Negative"
        elif score <= 0.1:
            sentiment = "Neutral"
        else:
            sentiment = "Positive"
            
        return sentiment, score
        
    except Exception as e:
        return "Neutral", 0.0

def analyze_text(text):
    """Main wrapper to dispatch analysis."""
    # Check for empty/None text
    if pd.isna(text) or text is None or str(text).strip() == "":
        return 'Unknown', "Undefined", 0.0
        
    lang = detect_language(text)
    
    if lang == 'en':
        return lang, *get_transformer_sentiment(text, 'en')
    elif lang == 'si':
        return 'Sinhala', *get_transformer_sentiment(text, 'si')
    elif lang == 'ta':
        return 'Tamil', *get_transformer_sentiment(text, 'ta')
    return 'Other', "Neutral", 0.0


# --- Main UI ---
st.title("🧩 Brand Sentiment Analyzer (CSV)")

# Clear Data Button (Top Right-ish logic or sidebar, putting in main for visibility)
if st.button("🗑️ Clear All Data"):
    st.session_state.processed_data = None
    st.session_state.raw_data = None
    st.session_state.analysis_complete = False
    st.rerun()

# 1. Brand Name
brand_name = st.text_input("1. Enter Brand Name", placeholder="e.g., Dialog, Mobitel")

# 2. File Upload
st.subheader("2. Upload Data")
uploaded_files = st.file_uploader("Upload CSV file(s)", type=['csv'], accept_multiple_files=True)

# Process Uploads
if uploaded_files:
    if st.session_state.raw_data is None:
        dfs = []
        for f in uploaded_files:
            try:
                # Attempt 1: Comma
                try:
                    df_temp = pd.read_csv(f)
                    if len(df_temp.columns) <= 1:
                        raise ValueError("Likely not comma separated")
                except Exception:
                    # Attempt 2: Semicolon
                    f.seek(0)
                    df_temp = pd.read_csv(f, sep=';')
                
                dfs.append(df_temp)
                
            except Exception as e:
                # Attempt 3: Python engine
                try:
                     f.seek(0)
                     df_temp = pd.read_csv(f, sep=None, engine='python')
                     dfs.append(df_temp)
                except Exception as final_e:
                     st.error(f"Error reading {f.name}: {final_e}")

        if dfs:
            st.session_state.raw_data = pd.concat(dfs, ignore_index=True)
            st.success(f"Successfully loaded {len(st.session_state.raw_data)} rows.")

# Data Preview & Config (Only if we have raw data)
if st.session_state.raw_data is not None:
    main_df = st.session_state.raw_data.copy()

    # 3. Preview
    st.subheader("3. Data Preview")
    st.dataframe(main_df.head())
    
    # 4. Remove Columns
    st.subheader("4. Clean Data")
    all_cols = main_df.columns.tolist()
    defaults_to_remove = [c for c in ["Sentiment", "Sentiment points"] if c in all_cols]
    
    cols_to_remove = st.multiselect(
        "Select columns to remove:", 
        options=all_cols, 
        default=defaults_to_remove
    )
    
    # 5. Analysis Configuration
    st.subheader("5. Analysis Settings")
    available_cols = [c for c in all_cols if c not in cols_to_remove]
    
    default_idx = 0
    if "Content of posts" in available_cols:
        default_idx = available_cols.index("Content of posts")
    elif len(available_cols) > 0:
        default_idx = 0
    else: 
         st.error("No columns available to analyze. Please uncheck some removed columns.")
         st.stop()
         
    content_col = st.selectbox("Select column containing text to analyze:", available_cols, index=default_idx)
    
    # 6. Run Analysis
    if st.button("🚀 Find Sentiment"):
        if not brand_name:
            st.warning("Please enter a Brand Name first.")
        else:
            # Prepare data
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
            
            # Processing Loop
            for i, row in analysis_df.iterrows():
                text = row[content_col]
                lang, sentiment, score = analyze_text(text)
                
                results_lang.append(lang)
                results_sent.append(sentiment)
                results_score.append(score)
                
                if i % 10 == 0:
                    progress = (i + 1) / total
                    progress_bar.progress(progress)
                    status_text.text(f"Processing row {i+1}/{total}...")
            
            progress_bar.progress(1.0)
            status_text.text("Analysis Complete!")
            
            # Add columns
            analysis_df['Detected_Language'] = results_lang
            analysis_df['New_Sentiment'] = results_sent
            analysis_df['Sentiment_Score'] = results_score
            
            # Save to session
            st.session_state.processed_data = analysis_df
            st.session_state.analysis_complete = True
            # Force rerun to show results immediately without requiring another interaction
            st.rerun()

# 7. Display Results (Persistent State)
if st.session_state.analysis_complete and st.session_state.processed_data is not None:
    final_df = st.session_state.processed_data
    
    st.subheader("7. Analysis Results")
    st.dataframe(final_df.head())
    
    # Visualize
    st.subheader("Sentiment Distribution")
    try:
        counts = final_df['New_Sentiment'].value_counts().reset_index()
        counts.columns = ['Sentiment', 'Count']
        
        colors = {
            "Positive": "#2E8B57", 
            "Negative": "#DC143C", 
            "Neutral": "#808080",
            "Undefined": "#000000"
        }
        
        # Ensure brand name is available, might be empty if page refreshed?
        # Ideally we'd store brand name in session too, but strictly not required if input is persistent.
        title_text = f"Sentiment Analysis for {brand_name}" if brand_name else "Sentiment Analysis Results"

        fig = px.bar(
            counts, 
            x='Sentiment', 
            y='Count', 
            color='Sentiment',
            color_discrete_map=colors,
            title=title_text
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning("Could not create chart.")

    # 8. Download
    st.subheader("8. Download Data")
    
    csv = final_df.to_csv(index=False).encode('utf-8')
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_name = f"sent1_sl_{date_str}.csv"
    
    st.download_button(
        label="⬇️ Download Output CSV",
        data=csv,
        file_name=file_name,
        mime='text/csv'
    )
