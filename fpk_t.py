import os
import sys
import asyncio
import streamlit as st
import pandas as pd
import re
from datetime import datetime
import time
import base64
import zipfile
import tempfile
import shutil
import io
import glob
from pathlib import Path

# --- Streamlit App Configuration ---
def hide_streamlit_ui():
    """
    Hides the default Streamlit "Made with Streamlit" footer, the main menu,
    and the top-right toolbar.
    """
    hide_menu_and_footer_css = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        [data-testid="stToolbar"] {display: none;}
        </style>
    """
    st.markdown(hide_menu_and_footer_css, unsafe_allow_html=True)

# --- Event Loop Policy (for Windows) ---
if sys.platform == "win32":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- Configure logging ---
import logging
logging.getLogger('nltk').setLevel(logging.ERROR)
logging.getLogger('streamlit').setLevel(logging.ERROR)

# --- Page Configuration ---
st.set_page_config(
    page_title="FPK File Processor",
    page_icon="📊",
    layout="wide",
)

hide_streamlit_ui()

# --- Custom CSS (Merged from both apps) ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #6c757d;
    }
    .stButton>button {
        width: 100%;
    }
    /* From Single File App */
    .file-list-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin-bottom: 0.5rem;
    }
    .file-list-item span {
        font-family: monospace;
    }
    /* From Zip File App */
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .zip-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #b8daff;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# --- Global Helper Functions (Combined) ---

def sanitize_sheet_name(sheet_name):
    """Sanitize sheet name for use in folder and file names"""
    sanitized = re.sub(r'[\.…]', '_', sheet_name)
    sanitized = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', sanitized)
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    sanitized = sanitized.strip(' _')
    if not sanitized:
        sanitized = "Sheet"
    return sanitized

def parse_sheet_name_format(sheet_name):
    """Parse sheet name in <Sheet_Type> - <Network_Type> format"""
    pattern = r'^(.+?)\s*-\s*(.+)$'
    match = re.match(pattern, sheet_name.strip())
    if match:
        sheet_type = match.group(1).strip()
        network_type = match.group(2).strip()
        return sheet_type, network_type
    return None, None

def get_zip_download_link(zip_path, filename, text):
    """Generate a download link for a ZIP file"""
    try:
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        b64 = base64.b64encode(zip_data).decode()
        href = f'<a href="data:application/zip;base64,{b64}" download="{filename}">{text}</a>'
        return href
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")
        return ""

def validate_date_folder_name(folder_name):
    """Validate if folder name matches date format"""
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{4}\.\d{2}\.\d{2}$',
        r'^\d{4}_\d{2}_\d{2}$',
        r'^\d{8}$'
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, folder_name):
            try:
                if pattern == r'^\d{8}$':
                    return datetime.strptime(folder_name, '%Y%m%d')
                elif pattern == r'^\d{4}\.\d{2}\.\d{2}$':
                    return datetime.strptime(folder_name, '%Y.%m.%d')
                elif pattern == r'^\d{4}_\d{2}_\d{2}$':
                    return datetime.strptime(folder_name, '%Y_%m_%d')
                else:
                    return datetime.strptime(folder_name, '%Y-%m-%d')
            except ValueError:
                continue
    return None

def extract_zip_file(uploaded_zip_file):
    """Extract uploaded ZIP file to a temporary directory"""
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Save the zip file temporarily
        zip_temp_path = os.path.join(temp_dir, "uploaded.zip")
        with open(zip_temp_path, "wb") as f:
            f.write(uploaded_zip_file.getvalue())
        
        # Extract the zip file
        with zipfile.ZipFile(zip_temp_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Remove the temporary zip file
        os.remove(zip_temp_path)
        
        return temp_dir, None
    except Exception as e:
        # Clean up if extraction fails
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None, str(e)

def safe_cleanup_temp_dir(temp_dir):
    """Safely clean up temporary directory"""
    if not temp_dir or not os.path.exists(temp_dir):
        return True
    
    try:
        shutil.rmtree(temp_dir)
        return True
    except Exception as e:
        st.warning(f"Could not fully clean up temp directory {temp_dir}: {e}")
        return False

def analyze_zip_structure(temp_dir):
    """Analyze the structure of the extracted ZIP file"""
    date_folders = []
    excel_files = []
    total_files = 0
    
    for root, dirs, files in os.walk(temp_dir):
        folder_name = os.path.basename(root)
        Date = validate_date_folder_name(folder_name)
        
        if Date:
            xlsx_files = [os.path.join(root, f) for f in files if f.lower().endswith('.xlsx')]
            xls_files = [os.path.join(root, f) for f in files if f.lower().endswith('.xls')]
            file_count = len(xlsx_files) + len(xls_files)
            total_files += file_count
            
            date_folders.append({
                'name': folder_name,
                'path': root,
                'date': Date,
                'file_count': file_count
            })
            
            for file_path in xlsx_files + xls_files:
                excel_files.append({
                    'path': file_path,
                    'date': Date,
                    'folder_name': folder_name
                })
    
    return {
        'date_folders': date_folders,
        'excel_files': excel_files,
        'total_files': total_files,
        'total_date_folders': len(date_folders),
        'temp_dir': temp_dir
    }

def get_excel_sheet_names(file_path):
    """Get sheet names from Excel file"""
    try:
        with pd.ExcelFile(file_path) as excel_file:
            return excel_file.sheet_names
    except Exception as e:
        return [f"Error reading sheets: {str(e)}"]

def create_client_zip(client_name, source_dir, processed_files_results):
    """
    Creates a ZIP file from the source_dir and generates a folder structure report.
    (This version zips an existing directory structure)
    """
    try:
        folder_structure = {}
        
        # Build folder structure report from results
        for result in processed_files_results:
            if result['status'] == 'success':
                folder_name = result.get('folder_name', 'Unnamed')
                if 'file_path' in result:
                    filename = os.path.basename(result['file_path'])
                    if folder_name not in folder_structure:
                        folder_structure[folder_name] = []
                    folder_structure[folder_name].append(filename)
        
        # Create ZIP file
        zip_filename = f"{client_name}_processed_files.zip"
        zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.csv'):
                        file_path = os.path.join(root, file)
                        # Create an archive name that is relative to the source_dir
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
        
        return zip_path, folder_structure, None
        
    except Exception as e:
        return None, None, str(e)


# --- Core Processing Functions ---

def process_excel_file_single(uploaded_file, file_date, base_output_dir):
    """
    Process a single uploaded Excel file (from memory buffer).
    Reads from the UploadedFile object and saves CSVs to base_output_dir.
    """
    processed_files_report = []
    
    try:
        # Use pd.ExcelFile on the uploaded_file object itself
        with pd.ExcelFile(uploaded_file) as excel_file:
            sheet_names = excel_file.sheet_names
            sheet_type_dataframes = {}
            
            for sheet_name in sheet_names:
                try:
                    # Read the specific sheet from the uploaded_file object
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
                    
                    if df.empty or len(df) < 2:
                        processed_files_report.append({
                            'status': 'skipped',
                            'reason': 'Sheet is empty or has insufficient data',
                            'sheet_name': sheet_name
                        })
                        continue
                    
                    # Delete first column if mostly empty
                    if len(df.columns) > 0:
                        first_col_empty_ratio = df.iloc[:, 0].isna().sum() / len(df)
                        if first_col_empty_ratio > 0.8:
                            df = df.drop(df.columns[0], axis=1)
                    
                    # Use row 5 as headers (index 4)
                    header_row = 4
                    if header_row >= len(df):
                        header_row = min(4, len(df) - 1) if len(df) > 1 else 0
                    
                    if len(df) > header_row:
                        df.columns = df.iloc[header_row]
                        if header_row + 1 < len(df):
                            df = df.iloc[header_row + 1:].reset_index(drop=True)
                        else:
                            df = pd.DataFrame(columns=df.columns)
                    
                    df = df.dropna(how='all')
                    
                    if df.empty:
                        processed_files_report.append({
                            'status': 'skipped',
                            'reason': 'No data rows after processing',
                            'sheet_name': sheet_name
                        })
                        continue
                    
                    # Add Date column
                    if 'Date' not in df.columns:
                        df.insert(0, 'Date', file_date.strftime('%Y-%m-%d'))
                    
                    # Check if sheet name is in <Sheet_Type> - <Network_Type> format
                    sheet_type, network_type = parse_sheet_name_format(sheet_name)
                    
                    if sheet_type and network_type:
                        # Handle Network column - update if exists, add if not
                        if 'Network' in df.columns:
                            df['Network'] = network_type
                        else:
                            df.insert(1, 'Network', network_type)
                        
                        # Store for merging
                        if sheet_type not in sheet_type_dataframes:
                            sheet_type_dataframes[sheet_type] = []
                        sheet_type_dataframes[sheet_type].append(df)
                        
                        processed_files_report.append({
                            'status': 'merged',
                            'sheet_name': sheet_name,
                            'rows_processed': len(df),
                            'sheet_type': sheet_type,
                            'network_type': network_type
                        })
                        
                    else:
                        # Process as normal sheet
                        sanitized_sheet_name = sanitize_sheet_name(sheet_name)
                        output_dir = os.path.join(base_output_dir, sanitized_sheet_name)
                        os.makedirs(output_dir, exist_ok=True)
                        
                        output_filename = f"{sanitized_sheet_name} {file_date.strftime('%Y%m%d')}.csv"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        df.to_csv(output_path, index=False)
                        
                        processed_files_report.append({
                            'status': 'success',
                            'file_path': output_path,
                            'sheet_name': sheet_name,
                            'rows_processed': len(df),
                            'dataframe': df,
                            'folder_name': sanitized_sheet_name
                        })
                
                except Exception as sheet_error:
                    processed_files_report.append({
                        'status': 'error',
                        'reason': f"Sheet processing error: {str(sheet_error)}",
                        'sheet_name': sheet_name
                    })
                    continue
            
            # Process merged dataframes
            for sheet_type, dfs in sheet_type_dataframes.items():
                if len(dfs) > 0:
                    merged_df = pd.concat(dfs, ignore_index=True)
                    sanitized_sheet_type = sanitize_sheet_name(sheet_type)
                    output_dir = os.path.join(base_output_dir, sanitized_sheet_type)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    output_filename = f"{sanitized_sheet_type} {file_date.strftime('%Y%m%d')}.csv"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    merged_df.to_csv(output_path, index=False)
                    
                    processed_files_report.append({
                        'status': 'success',
                        'file_path': output_path,
                        'sheet_name': f"{sheet_type} (merged from {len(dfs)} sheets)",
                        'rows_processed': len(merged_df),
                        'dataframe': merged_df,
                        'merged_count': len(dfs),
                        'folder_name': sanitized_sheet_type
                    })
                    
    except Exception as e:
        # Use .name if available, otherwise default text
        file_name = getattr(uploaded_file, 'name', 'the file')
        processed_files_report.append({
            'status': 'error',
            'reason': f"Failed to read Excel file {file_name}: {str(e)}",
            'sheet_name': 'File Level Error'
        })
    
    return processed_files_report

def process_excel_file_safe(file_path, Date, base_output_dir):
    """
    Process a single Excel file (from disk path).
    Reads from file_path and saves CSVs to base_output_dir.
    """
    processed_files = []
    
    try:
        with pd.ExcelFile(file_path) as excel_file:
            sheet_names = excel_file.sheet_names
            sheet_type_dataframes = {}
            
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                    
                    if df.empty or len(df) < 2:
                        processed_files.append({
                            'status': 'skipped',
                            'reason': 'Sheet is empty or has insufficient data',
                            'sheet_name': sheet_name
                        })
                        continue
                    
                    # Delete first column if mostly empty
                    if len(df.columns) > 0:
                        first_col_empty_ratio = df.iloc[:, 0].isna().sum() / len(df)
                        if first_col_empty_ratio > 0.8:
                            df = df.drop(df.columns[0], axis=1)
                    
                    # Use row 5 as headers
                    header_row = 4
                    if header_row >= len(df):
                        header_row = min(4, len(df) - 1) if len(df) > 1 else 0
                    
                    if len(df) > header_row:
                        df.columns = df.iloc[header_row]
                        if header_row + 1 < len(df):
                            df = df.iloc[header_row + 1:].reset_index(drop=True)
                        else:
                            df = pd.DataFrame(columns=df.columns)
                    
                    df = df.dropna(how='all')
                    
                    if df.empty:
                        processed_files.append({
                            'status': 'skipped',
                            'reason': 'No data rows after processing',
                            'sheet_name': sheet_name
                        })
                        continue
                    
                    # Add Date column
                    if 'Date' not in df.columns:
                        df.insert(0, 'Date', Date.strftime('%Y-%m-%d'))
                    
                    # Check if sheet name is in <Sheet_Type> - <Network_Type> format
                    sheet_type, network_type = parse_sheet_name_format(sheet_name)
                    
                    if sheet_type and network_type:
                        # Handle Network column - update if exists, add if not
                        if 'Network' in df.columns:
                            df['Network'] = network_type
                        else:
                            df.insert(1, 'Network', network_type)
                        
                        # Store for merging
                        if sheet_type not in sheet_type_dataframes:
                            sheet_type_dataframes[sheet_type] = []
                        sheet_type_dataframes[sheet_type].append(df)
                        
                        processed_files.append({
                            'status': 'merged',
                            'sheet_name': sheet_name,
                            'rows_processed': len(df),
                            'sheet_type': sheet_type,
                            'network_type': network_type
                        })
                        
                    else:
                        # Process as normal sheet
                        sanitized_sheet_name = sanitize_sheet_name(sheet_name)
                        output_dir = os.path.join(base_output_dir, sanitized_sheet_name)
                        os.makedirs(output_dir, exist_ok=True)
                        
                        output_filename = f"{sanitized_sheet_name} {Date.strftime('%Y%m%d')}.csv"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        df.to_csv(output_path, index=False)
                        
                        processed_files.append({
                            'status': 'success',
                            'file_path': output_path,
                            'sheet_name': sheet_name,
                            'rows_processed': len(df),
                            'dataframe': df,
                            'folder_name': sanitized_sheet_name
                        })
                
                except Exception as sheet_error:
                    processed_files.append({
                        'status': 'error',
                        'reason': f"Sheet processing error: {str(sheet_error)}",
                        'sheet_name': sheet_name
                    })
                    continue
            
            # Process merged dataframes
            for sheet_type, dfs in sheet_type_dataframes.items():
                if len(dfs) > 0:
                    merged_df = pd.concat(dfs, ignore_index=True)
                    sanitized_sheet_type = sanitize_sheet_name(sheet_type)
                    output_dir = os.path.join(base_output_dir, sanitized_sheet_type)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    output_filename = f"{sanitized_sheet_type} {Date.strftime('%Y%m%d')}.csv"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    merged_df.to_csv(output_path, index=False)
                    
                    processed_files.append({
                        'status': 'success',
                        'file_path': output_path,
                        'sheet_name': f"{sheet_type} (merged from {len(dfs)} sheets)",
                        'rows_processed': len(merged_df),
                        'dataframe': merged_df,
                        'merged_count': len(dfs),
                        'folder_name': sanitized_sheet_type
                    })
                    
    except Exception as e:
        processed_files.append({
            'status': 'error',
            'reason': str(e),
            'sheet_name': 'File Level Error'
        })
    
    return processed_files


# --- Global UI Display Functions ---

def display_processing_report(all_results, show_detailed_progress=True):
    """Display processing report"""
    success_count = len([r for r in all_results if r['status'] == 'success'])
    skipped_count = len([r for r in all_results if r['status'] == 'skipped'])
    error_count = len([r for r in all_results if r['status'] == 'error'])
    merged_count = len([r for r in all_results if r['status'] == 'merged'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("✅ Success (CSVs)", success_count)
    with col2:
        st.metric("🔄 Merged (Sheets)", merged_count)
    with col3:
        st.metric("⏭️ Skipped (Sheets)", skipped_count)
    with col4:
        st.metric("❌ Errors", error_count)
    
    merged_sheets = [r for r in all_results if r['status'] == 'merged']
    if merged_sheets:
        with st.expander("🎯 Merged Sheets Information"):
            st.info("The following sheets were detected in special format and merged:")
            for sheet in merged_sheets:
                st.write(f"• **{sheet['sheet_name']}** → Sheet Type: `{sheet['sheet_type']}`, Network: `{sheet['network_type']}`")
    
    if success_count > 0 and show_detailed_progress:
        with st.expander("🎉 Successfully Processed Files"):
            for result in all_results:
                if result['status'] == 'success':
                    rows_info = f" ({result['rows_processed']} rows)" if 'rows_processed' in result else ""
                    merged_info = f" [merged from {result['merged_count']} sheets]" if 'merged_count' in result else ""
                    folder_info = f" → 📁 {result['folder_name']}" if 'folder_name' in result else ""
                    st.success(f"✅ {result['sheet_name']}{rows_info}{merged_info}{folder_info}")
    
    if error_count > 0:
        with st.expander("❌ Error Log"):
            for result in all_results:
                if result['status'] == 'error':
                    st.error(f"Failed on sheet '{result['sheet_name']}': {result['reason']}")

def display_folder_structure(folder_structure):
    """Display the folder structure of the created ZIP"""
    if folder_structure:
        st.markdown("### 📁 Folder Structure in ZIP")
        st.info("Files have been organized into the following folders:")
        
        for folder_name, files in sorted(folder_structure.items()):
            with st.expander(f"📁 **{folder_name}** ({len(files)} files)"):
                for file in sorted(files):
                    st.write(f"📄 {file}")


# --- Page 1: Single File Processor ---

def page_single_files():
    """Renders the UI for the Single File Processor"""
    
    # Initialize session state for file list
    if 'file_list' not in st.session_state:
        st.session_state.file_list = []

    # --- 1. Client & File Upload ---
    st.markdown("### 1. Client Information")
    client_name = st.text_input(
        "Client Name:",
        placeholder="Enter client name (e.g., Dialog_Axiata, Mobitel, etc.)",
        help="Required if processing more than one file (for the ZIP file name)",
        key="client_name_single"
    )

    st.markdown("### 2. Add Files to Process")
    
    # Form for adding a single file
    with st.form("add_file_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Upload an Excel File (.xlsx)",
                type=['xlsx', 'xls'],
                key="file_uploader"
            )
        with col2:
            file_date = st.date_input("Select File Date", value=datetime.now(), key="file_date")
        
        submitted = st.form_submit_button("➕ Add File to Queue")
        
        if submitted and uploaded_file is not None:
            # Read the file into memory
            file_bytes = io.BytesIO(uploaded_file.getvalue())
            
            st.session_state.file_list.append({
                "file_data": file_bytes,
                "date": file_date,
                "name": uploaded_file.name
            })
            st.success(f"Added {uploaded_file.name} to the queue.")
        elif submitted and uploaded_file is None:
            st.warning("Please select a file to add.")

    # --- 2. Review Queue ---
    st.markdown("### 3. Review Queue")
    
    if not st.session_state.file_list:
        st.info("No files in the queue. Add files using the form above.")
    else:
        st.markdown(f"**{len(st.session_state.file_list)} file(s) in queue:**")
        
        # Display files in queue with remove buttons
        for i, item in enumerate(st.session_state.file_list):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div class="file-list-item">
                    <span>📄 {item['name']} (<b>Date:</b> {item['date'].strftime('%Y-%m-%d')})</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button(f"Remove##{i}", key=f"remove_{i}"):
                    st.session_state.file_list.pop(i)
                    st.rerun()

    st.markdown("---")

    # --- 3. Process ---
    st.markdown("### 4. Process Files")
    
    if st.button("🚀 Process All Files in Queue", type="primary", disabled=not st.session_state.file_list):
        
        file_count = len(st.session_state.file_list)
        
        # Validation
        if file_count > 1 and not client_name:
            st.error("❌ Please enter a Client Name. It's required for creating the ZIP file when processing multiple files.")
            return

        # Create temporary output directory
        temp_output_dir = tempfile.mkdtemp()
        all_results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Process each file
            for i, item in enumerate(st.session_state.file_list):
                file_name = item['name']
                file_data = item['file_data']
                file_date = item['date']
                
                progress = (i + 1) / file_count
                progress_bar.progress(progress)
                status_text.text(f"Processing {i+1}/{file_count}: {file_name}")
                
                # Pass the in-memory BytesIO object to the processing function
                results = process_excel_file_single(file_data, file_date, temp_output_dir)
                
                for result in results:
                    result['source_file'] = file_name
                    all_results.append(result)
            
            status_text.success(f"✅ Processing complete for all {file_count} file(s)!")
            progress_bar.progress(1.0)
            
            # --- Display Report ---
            st.markdown("---")
            st.markdown("### 📈 Processing Report")
            display_processing_report(all_results, show_detailed_progress=True) # Always show details for this mode
            
            # --- Handle Output ---
            st.markdown("---")
            st.markdown("### 📦 Download Processed Files")
            
            success_files = [r for r in all_results if r['status'] == 'success']
            
            if not success_files:
                st.warning("No files were successfully processed.")
            
            # > 1 file: Create a ZIP
            elif file_count > 1:
                with st.spinner(f"Creating organized ZIP file for {client_name}..."):
                    zip_path, folder_structure, error = create_client_zip(client_name, temp_output_dir, all_results)
                    
                    if error:
                        st.error(f"❌ Error creating ZIP file: {error}")
                    else:
                        st.success(f"✅ ZIP file created!")
                        display_folder_structure(folder_structure)
                        
                        zip_filename = f"{client_name}_processed_files.zip"
                        download_link = get_zip_download_link(zip_path, zip_filename, f"📥 Download {zip_filename}")
                        st.markdown(download_link, unsafe_allow_html=True)
                        
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
            
            # == 1 file: Provide individual CSV downloads
            elif file_count == 1 and success_files:
                st.info("Download each processed file individually:")
                for result in success_files:
                    try:
                        file_path = result['file_path']
                        filename = os.path.basename(file_path)
                        sheet_name = result['sheet_name']
                        
                        with open(file_path, 'rb') as f:
                            csv_data = f.read()
                        
                        st.download_button(
                            label=f"📥 Download {filename} (from sheet: {sheet_name})",
                            data=csv_data,
                            file_name=filename,
                            mime='text/csv',
                            key=f"download_{filename}"
                        )
                    except Exception as e:
                        st.error(f"Could not create download for {filename}: {e}")

        finally:
            # Clean up temporary output directory
            safe_cleanup_temp_dir(temp_output_dir)


# --- Page 2: ZIP File Processor ---

def page_zip_processor():
    """Renders the UI for the ZIP File Processor"""
    
    # --- 1. Client Information ---
    st.markdown("### 👤 Client Information")
    client_name = st.text_input(
        "Client Name:",
        placeholder="Enter client name (e.g., Dialog_Axiata, Mobitel, etc.)",
        help="This name will be used for the output ZIP file",
        key="client_name_zip"
    )
    
    # --- 2. ZIP File Upload ---
    st.markdown("### 📦 ZIP File Upload")
    uploaded_zip = st.file_uploader(
        "Upload ZIP File with Dated Folders",
        type=['zip'],
        help="Upload a ZIP file containing dated folders with Excel files"
    )
    
    if uploaded_zip:
        st.success(f"✅ ZIP file uploaded: {uploaded_zip.name}")
        
        # Analyze ZIP structure
        if 'zip_analysis' not in st.session_state or st.session_state.get('current_zip') != uploaded_zip.name:
            with st.spinner("Analyzing ZIP file structure..."):
                # Clean up old temp dir if it exists
                if 'temp_dir' in st.session_state:
                    safe_cleanup_temp_dir(st.session_state.temp_dir)
                    
                temp_dir, error = extract_zip_file(uploaded_zip)
                if error:
                    st.error(f"❌ Error extracting ZIP: {error}")
                    if 'zip_analysis' in st.session_state:
                        del st.session_state.zip_analysis
                else:
                    zip_analysis = analyze_zip_structure(temp_dir)
                    st.session_state.zip_analysis = zip_analysis
                    st.session_state.current_zip = uploaded_zip.name
                    st.session_state.temp_dir = temp_dir # This is the *extracted zip* dir

    # --- 3. ZIP File Processing ---
    if 'zip_analysis' in st.session_state:
        zip_analysis = st.session_state.zip_analysis
        
        st.markdown("### 📦 ZIP File Analysis")
        
        if zip_analysis['total_date_folders'] == 0:
            st.error("❌ No valid date folders (e.g., '2024-01-15') found in the ZIP file!")
            st.markdown("""
            <div class="warning-box">
            <h4>Required ZIP Structure:</h4>
            <pre>
            your_zip_file.zip
            ├── 2024-01-15/
            │   └── datafile1.xlsx
            ├── 2024-01-16/
            │   └── datafile2.xlsx
            └── 2024.01.17/
                └── datafile3.xlsx
            </pre>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Display ZIP statistics
        st.markdown("### 📊 ZIP File Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{zip_analysis['total_date_folders']}</div>
                <div class="metric-label">📁 Date Folders Found</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{zip_analysis['total_files']}</div>
                <div class="metric-label">📄 Excel Files Found</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Show Sheet Names analysis (from first file)
        if zip_analysis['excel_files']:
            st.markdown("### 📋 Sheet Names Analysis (from first file)")
            sample_file = zip_analysis['excel_files'][0]
            try:
                sheet_names = get_excel_sheet_names(sample_file['path'])
                
                special_format_sheets = []
                regular_sheets = []
                
                for sheet_name in sheet_names:
                    sheet_type, network_type = parse_sheet_name_format(sheet_name)
                    if sheet_type and network_type:
                        special_format_sheets.append((sheet_name, sheet_type, network_type))
                    else:
                        regular_sheets.append(sheet_name)
                
                if special_format_sheets:
                    st.success("🎯 **Sheets in special format detected:**")
                    for sheet_name, sheet_type, network_type in special_format_sheets:
                        st.write(f"• **{sheet_name}** → Will be merged into: `{sheet_type}.csv`, Network: `{network_type}`")
                
                if regular_sheets:
                    st.info("**Regular sheets detected:**")
                    for sheet_name in regular_sheets:
                        sanitized_name = sanitize_sheet_name(sheet_name)
                        st.write(f"• **{sheet_name}** → Will be saved in folder: `{sanitized_name}`")
                        
            except Exception as e:
                st.error(f"Error reading sheet names from {sample_file['path']}: {e}")
        
        # Processing options
        st.markdown("### ⚙️ Processing Options")
        show_detailed_progress = st.checkbox("Show detailed processing log", value=True, key="zip_show_details")
        
        # Process ZIP button
        st.markdown("---")
        if st.button("🚀 Process ZIP File", type="primary"):
            if not client_name:
                st.error("❌ Please enter a client name first!")
                return
            
            # Create temporary *output* directory
            temp_output_dir = tempfile.mkdtemp()
            st.session_state.temp_output_dir = temp_output_dir
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            all_results = []
            total_files = len(zip_analysis['excel_files'])
            
            try:
                # Process files from ZIP
                for i, file_info in enumerate(zip_analysis['excel_files']):
                    file_path = file_info['path']
                    Date = file_info['date']
                    
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {i+1}/{total_files}: {os.path.basename(file_path)}")
                    
                    # Use process_excel_file_safe (takes a file path)
                    results = process_excel_file_safe(file_path, Date, temp_output_dir)
                    
                    for result in results:
                        result['source_file'] = file_path
                        result['date_folder'] = file_info['folder_name']
                        all_results.append(result)
                
                progress_bar.progress(1.0)
                status_text.success("✅ Processing complete!")
                
                st.session_state.processing_results = all_results
                
                # --- Display Report ---
                st.markdown("---")
                st.markdown("### 📈 Processing Report")
                display_processing_report(all_results, show_detailed_progress)
                
                # --- Create ZIP download ---
                st.markdown("---")
                st.markdown("### 📦 Download Processed Files")
                
                if not any(r['status'] == 'success' for r in all_results):
                    st.warning("No files were successfully processed.")
                    return

                with st.spinner(f"Creating organized ZIP file for {client_name}..."):
                    # Use the efficient create_client_zip that zips the temp_output_dir
                    zip_path, folder_structure, error = create_client_zip(
                        client_name, 
                        temp_output_dir, # The directory where CSVs were saved
                        all_results        # The report to build folder structure
                    )
                    
                    if error:
                        st.error(f"❌ Error creating ZIP file: {error}")
                    else:
                        st.session_state.client_zip_path = zip_path
                        st.success(f"✅ ZIP file created with organized folder structure!")
                        
                        display_folder_structure(folder_structure)
                        
                        zip_filename = f"{client_name}_processed_files.zip"
                        download_link = get_zip_download_link(zip_path, zip_filename, f"📥 Download {zip_filename}")
                        st.markdown(download_link, unsafe_allow_html=True)
                        
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
            
            finally:
                # Clean up the *output* directory
                if 'temp_output_dir' in st.session_state:
                    safe_cleanup_temp_dir(st.session_state.temp_output_dir)
                    del st.session_state.temp_output_dir
                # Clean up the *extracted zip* directory
                if 'temp_dir' in st.session_state:
                    safe_cleanup_temp_dir(st.session_state.temp_dir)
                    del st.session_state.temp_dir
                if 'zip_analysis' in st.session_state:
                    del st.session_state.zip_analysis
                if 'current_zip' in st.session_state:
                    del st.session_state.current_zip
                
                st.info("Processing finished. Upload a new ZIP to start again.")


# --- Main Application Navigator ---

def main():
    """Main Streamlit application"""
    
    st.sidebar.title("Processor Mode")
    mode = st.sidebar.radio(
        "Select processor:",
        ["📁 Single Files", "📦 ZIP File"],
        help="Choose how you want to upload and process files."
    )
    
    st.markdown('<div class="main-header">📊 FPK File Processor</div>', unsafe_allow_html=True)
    
    if mode == "📁 Single Files":
        page_single_files()
    else:
        page_zip_processor()

# Run the app
if __name__ == "__main__":
    main()