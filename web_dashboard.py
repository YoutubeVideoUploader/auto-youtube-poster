"""
Malayalam Movie News - Web Dashboard & Video Previewer
Connected to Google Sheets (Movie Updates, Release Updates, OTT Updates).
Provides Bulk Table Paste, Interactive Cell Editing, Google Sheet Syncing,
and Live 1080p Video Slide Previews.
"""

import sys
import os
import time
import subprocess
import pandas as pd
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from google_sheet_manager import GoogleSheetManager, SHEET_CONFIGS
from slide_preview_engine import SlidePreviewEngine
from config import OUTPUT_DIR

# Page Configuration
st.set_page_config(
    page_title="Malayalam Movie News - Studio Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #FF2A4B;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #A0A0B0;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .nav-box {
        background-color: #1E1E2E;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .topic-card {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "sheet_mgr" not in st.session_state:
    st.session_state.sheet_mgr = GoogleSheetManager()
if "preview_eng" not in st.session_state:
    st.session_state.preview_eng = SlidePreviewEngine()
if "current_section" not in st.session_state:
    st.session_state.current_section = "📥 Input & Data Editor"
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Movie Updates"
if "edited_dfs" not in st.session_state:
    st.session_state.edited_dfs = {}


# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/color/96/youtube-play.png", width=70)
    st.title("Studio Controls")
    
    st.markdown("---")
    st.subheader("🔗 Google Sheet Connection")
    sheet_url_input = st.text_input(
        "Google Sheet URL",
        value=st.session_state.sheet_mgr.sheet_url,
        help="Edit URL of your Google Sheet document"
    )
    if sheet_url_input != st.session_state.sheet_mgr.sheet_url:
        st.session_state.sheet_mgr.sheet_url = sheet_url_input
        st.success("Updated Google Sheet URL!")

    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    if st.button("🔄 Reload from Google Sheet", use_container_width=True):
        with st.spinner("Fetching latest sheets online..."):
            st.session_state.edited_dfs = st.session_state.sheet_mgr.fetch_all_tabs(force_refresh=True)
            st.success("Sheets reloaded successfully!")
            st.rerun()

    if st.button("💾 Export All to Excel (.xlsx)", use_container_width=True):
        excel_data = st.session_state.sheet_mgr.export_as_excel_bytes()
        st.download_button(
            label="⬇️ Download Excel File",
            data=excel_data,
            file_name="Malayalam_Movie_News_Sheets.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("🤖 Groq AI Settings")
    groq_api_key_input = st.text_input(
        "Groq API Key",
        value=st.session_state.get("groq_api_key", os.getenv("GROQ_API_KEY", "")),
        type="password",
        help="Enter your Groq API Key to auto-fill movie names automatically"
    )
    if groq_api_key_input != st.session_state.get("groq_api_key", ""):
        st.session_state["groq_api_key"] = groq_api_key_input

    st.markdown("---")
    st.info("💡 **Tip**: Select **Input** to paste & edit table rows, then select **Output** to view rendered 1080p slide previews!")


# Fetch initial data if not loaded
if not st.session_state.edited_dfs:
    st.session_state.edited_dfs = st.session_state.sheet_mgr.fetch_all_tabs(force_refresh=False)


# Main Header
st.markdown('<div class="main-header">🎬 Malayalam Movie News Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Google Sheets Editor & Live 1080p Video Slide Previewer</div>', unsafe_allow_html=True)

# Main Section Navigation Buttons
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📥 Input & Data Editor", use_container_width=True, type="primary" if st.session_state.current_section == "📥 Input & Data Editor" else "secondary"):
        st.session_state.current_section = "📥 Input & Data Editor"
        st.rerun()

with col_nav2:
    if st.button("📺 Output & Video Slide Preview", use_container_width=True, type="primary" if st.session_state.current_section == "📺 Output & Video Slide Preview" else "secondary"):
        st.session_state.current_section = "📺 Output & Video Slide Preview"
        st.rerun()

st.markdown("---")


# ==============================================================================
# SECTION 1: 📥 INPUT & DATA EDITOR
# ==============================================================================
if st.session_state.current_section == "📥 Input & Data Editor":
    st.header("📥 Input & Data Editor")
    st.caption("Switch between sheet tabs, paste multi-row tables from Excel/Google Sheets, or edit individual cells.")

    # Category Tab Selection
    tab_cols = st.columns(3)
    tab_names = ["Movie Updates", "Release Updates", "OTT Updates"]
    tab_icons = ["🎬 Movie Updates", "📅 Release Updates", "🍿 OTT Updates"]

    for i, t_name in enumerate(tab_names):
        with tab_cols[i]:
            if st.button(tab_icons[i], use_container_width=True, type="primary" if st.session_state.current_tab == t_name else "secondary"):
                st.session_state.current_tab = t_name
                st.rerun()

    active_tab = st.session_state.current_tab
    st.subheader(f"Editing Worksheet: **{active_tab}**")

    # Current DataFrame
    current_df = st.session_state.edited_dfs.get(active_tab, pd.DataFrame(columns=["Topic Number", "Topic Headline", "Malayalam News Text", "Image URLs"]))
    if "Topic Headline" not in current_df.columns:
        current_df["Topic Headline"] = ""
    # Re-order columns nicely
    cols_order = [c for c in ["Topic Number", "Topic Headline", "Malayalam News Text", "Image URLs"] if c in current_df.columns]
    current_df = current_df[cols_order]

    # --------------------------------------------------------------------------
    # OPTION 1: BULK PASTE (SINGLE COLUMN OR FULL TABLE)
    # --------------------------------------------------------------------------
    with st.expander("📋 **Option 1: Single-Column or Full Table Bulk Paste**", expanded=False):
        st.write("Paste multi-line text into a single specific column or paste a full tab-separated table copied from Excel/Google Sheets.")
        
        target_col_choice = st.selectbox(
            "Select Target Column to Paste Into",
            options=["Malayalam News Text", "Topic Headline", "Image URLs", "Topic Number", "All Columns (Tab-Separated Full Table)"],
            index=0,
            help="Choose 'Malayalam News Text', 'Topic Headline (Movie Name)', or 'Image URLs' to paste line-by-line into that single column only, or 'All Columns' for multi-column table data."
        )
        
        single_paste_text = st.text_area(
            "Paste Bulk Content Here (One item per line)",
            height=140,
            placeholder="Line 1 item...\nLine 2 item...\nLine 3 item...",
            key=f"bulk_paste_area_{active_tab}"
        )
        
        col_sp1, col_sp2 = st.columns([1, 3])
        with col_sp1:
            if st.button("📥 Apply Bulk Paste", type="primary", key=f"btn_bulk_paste_{active_tab}"):
                lines = [line.strip() for line in single_paste_text.splitlines() if line.strip()]
                if not lines:
                    st.warning("Please paste some text first.")
                else:
                    df = current_df.copy()
                    if target_col_choice == "All Columns (Tab-Separated Full Table)":
                        parsed_df = st.session_state.sheet_mgr.parse_pasted_table(single_paste_text)
                        if not parsed_df.empty:
                            st.session_state.edited_dfs[active_tab] = parsed_df
                            st.session_state.sheet_mgr.update_tab_data(active_tab, parsed_df)
                            st.success(f"Imported {len(parsed_df)} full topic rows into {active_tab}!")
                            st.rerun()
                        else:
                            st.error("Could not parse tab-separated table. Check format.")
                    else:
                        # Single-column bulk paste
                        if len(df) < len(lines):
                            extra_rows = len(lines) - len(df)
                            new_rows = []
                            start_topic = len(df) + 1
                            for i in range(extra_rows):
                                new_rows.append({
                                    "Topic Number": str(start_topic + i),
                                    "Topic Headline": "",
                                    "Malayalam News Text": "",
                                    "Image URLs": ""
                                })
                            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                        
                        for i, line_val in enumerate(lines):
                            df.at[i, target_col_choice] = line_val
                        
                        st.session_state.edited_dfs[active_tab] = df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                        st.success(f"Pasted {len(lines)} items directly into column **'{target_col_choice}'**!")
                        st.rerun()

    # --------------------------------------------------------------------------
    # OPTION 2: ADJUST ROW POSITION & RE-ORDERING
    # --------------------------------------------------------------------------
    with st.expander("🔀 **Option 2: Adjust Row Position & Re-order Topics**", expanded=False):
        st.write("Change the position of any topic row (e.g. move Row 3 to Position 2, move Up/Down, or swap rows).")
        df_row_count = len(current_df)
        
        if df_row_count == 0:
            st.info("No rows currently exist in this worksheet to move.")
        else:
            col_r1, col_r2, col_r3 = st.columns([1, 1, 2])
            with col_r1:
                src_pos = st.number_input("Source Row #", min_value=1, max_value=max(1, df_row_count), value=min(3, df_row_count), step=1, key=f"src_pos_{active_tab}")
            with col_r2:
                tgt_pos = st.number_input("Target Position #", min_value=1, max_value=max(1, df_row_count), value=min(2, df_row_count), step=1, key=f"tgt_pos_{active_tab}")
                
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            df = current_df.copy()
            
            with col_btn1:
                if st.button("🔀 Move to Position", use_container_width=True, key=f"btn_move_pos_{active_tab}"):
                    if src_pos != tgt_pos:
                        src_idx = int(src_pos - 1)
                        tgt_idx = int(tgt_pos - 1)
                        row_to_move = df.iloc[src_idx:src_idx+1]
                        df = df.drop(df.index[src_idx]).reset_index(drop=True)
                        
                        df_upper = df.iloc[:tgt_idx]
                        df_lower = df.iloc[tgt_idx:]
                        df = pd.concat([df_upper, row_to_move, df_lower], ignore_index=True)
                        df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                        
                        st.session_state.edited_dfs[active_tab] = df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                        st.success(f"Moved Row {src_pos} to Position {tgt_pos}!")
                        st.rerun()

            with col_btn2:
                if st.button("⬆️ Move Up", use_container_width=True, key=f"btn_move_up_{active_tab}"):
                    if src_pos > 1:
                        src_idx = int(src_pos - 1)
                        tgt_idx = int(src_pos - 2)
                        df.iloc[src_idx], df.iloc[tgt_idx] = df.iloc[tgt_idx].copy(), df.iloc[src_idx].copy()
                        df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                        st.session_state.edited_dfs[active_tab] = df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                        st.success(f"Moved Row {src_pos} Up to Position {src_pos - 1}!")
                        st.rerun()

            with col_btn3:
                if st.button("⬇️ Move Down", use_container_width=True, key=f"btn_move_down_{active_tab}"):
                    if src_pos < df_row_count:
                        src_idx = int(src_pos - 1)
                        tgt_idx = int(src_pos)
                        df.iloc[src_idx], df.iloc[tgt_idx] = df.iloc[tgt_idx].copy(), df.iloc[src_idx].copy()
                        df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                        st.session_state.edited_dfs[active_tab] = df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                        st.success(f"Moved Row {src_pos} Down to Position {src_pos + 1}!")
                        st.rerun()

            with col_btn4:
                if st.button("↔️ Swap Rows", use_container_width=True, key=f"btn_swap_rows_{active_tab}"):
                    if src_pos != tgt_pos:
                        src_idx = int(src_pos - 1)
                        tgt_idx = int(tgt_pos - 1)
                        df.iloc[src_idx], df.iloc[tgt_idx] = df.iloc[tgt_idx].copy(), df.iloc[src_idx].copy()
                        df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                        st.session_state.edited_dfs[active_tab] = df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                        st.success(f"Swapped Row {src_pos} and Row {tgt_pos}!")
                        st.rerun()

    # --------------------------------------------------------------------------
    # OPTION 3: QUICK COLUMN & ROW MANAGEMENT TOOLS
    # --------------------------------------------------------------------------
    with st.expander("🛠️ **Option 3: Quick Column & Row Management Tools**", expanded=False):
        st.write("Perform quick operations on rows and columns in the active table.")
        
        m_col1, m_col2 = st.columns(2)
        df = current_df.copy()
        df_row_count = len(df)
        
        with m_col1:
            st.markdown("##### ➕ / 🗑️ Row Controls")
            ins_pos = st.number_input("Insert Blank Row at Position #", min_value=1, max_value=max(1, df_row_count + 1), value=min(1, df_row_count + 1), step=1, key=f"ins_pos_{active_tab}")
            if st.button("➕ Insert Blank Row", key=f"btn_ins_row_{active_tab}"):
                tgt_idx = int(ins_pos - 1)
                blank_row = pd.DataFrame([{"Topic Number": str(ins_pos), "Topic Headline": "", "Malayalam News Text": "", "Image URLs": ""}])
                df_upper = df.iloc[:tgt_idx]
                df_lower = df.iloc[tgt_idx:]
                df = pd.concat([df_upper, blank_row, df_lower], ignore_index=True)
                df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                st.session_state.edited_dfs[active_tab] = df
                st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                st.success(f"Inserted blank row at position {ins_pos}!")
                st.rerun()
                
            del_pos = st.number_input("Delete Row at Position #", min_value=1, max_value=max(1, df_row_count), value=min(1, df_row_count), step=1, key=f"del_pos_{active_tab}")
            if st.button("🗑️ Delete Specified Row", key=f"btn_del_row_{active_tab}"):
                if df_row_count > 0:
                    tgt_idx = int(del_pos - 1)
                    df = df.drop(df.index[tgt_idx]).reset_index(drop=True)
                    df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                    st.session_state.edited_dfs[active_tab] = df
                    st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                    st.success(f"Deleted row {del_pos}!")
                    st.rerun()

        with m_col2:
            st.markdown("##### 🧹 Column & Renumbering Controls")
            col_to_clear = st.selectbox("Select Column to Clear", options=["Malayalam News Text", "Topic Headline", "Image URLs"], key=f"col_to_clear_{active_tab}")
            if st.button("🧹 Clear Column Content", key=f"btn_clear_col_{active_tab}"):
                df[col_to_clear] = ""
                st.session_state.edited_dfs[active_tab] = df
                st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                st.success(f"Cleared all entries in column '{col_to_clear}'!")
                st.rerun()
                
            st.markdown("---")
            if st.button("🔢 Auto-Renumber Topic Numbers", key=f"btn_renumber_{active_tab}"):
                df["Topic Number"] = [str(i + 1) for i in range(len(df))]
                st.session_state.edited_dfs[active_tab] = df
                st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                st.success("Renumbered all topic numbers sequentially!")
                st.rerun()

    # --------------------------------------------------------------------------
    # OPTION 4: GROQ AI MOVIE NAME AUTO-EXTRACTOR
    # --------------------------------------------------------------------------
    with st.expander("🤖 **Option 4: Auto-Extract Movie Names via Groq AI (GPT-OSS / Llama-3)**", expanded=False):
        st.write("Use Groq AI (GPT-OSS / Llama-3) to read all Malayalam news descriptions in this tab and automatically fill the **Movie Name (Col D)** column!")
        
        groq_key = st.session_state.get("groq_api_key", os.getenv("GROQ_API_KEY", ""))
        if not groq_key:
            st.warning("⚠️ Please enter your Groq API Key in the left sidebar under **🤖 Groq AI Settings** first.")
        
        col_g1, col_g2 = st.columns([2, 3])
        with col_g1:
            if st.button("🤖 Auto-Extract Movie Names Now", type="primary", use_container_width=True, key=f"btn_groq_extract_{active_tab}"):
                if not groq_key:
                    st.error("Please enter your Groq API Key in the sidebar first!")
                else:
                    df = current_df.copy()
                    news_list = df["Malayalam News Text"].tolist()
                    if not any(str(t).strip() for t in news_list):
                        st.warning("No news texts found in this worksheet to extract movie names from.")
                    else:
                        with st.spinner("🤖 Groq AI is analyzing Malayalam news texts and extracting movie titles..."):
                            try:
                                from groq_extractor import extract_movie_titles_with_groq
                                extracted_titles = extract_movie_titles_with_groq(news_list, api_key=groq_key)
                                
                                count_filled = 0
                                for i, title_val in enumerate(extracted_titles):
                                    if title_val:
                                        df.at[i, "Topic Headline"] = title_val
                                        count_filled += 1
                                
                                st.session_state.edited_dfs[active_tab] = df
                                st.session_state.sheet_mgr.update_tab_data(active_tab, df)
                                st.balloons()
                                st.success(f"🎉 Groq AI auto-filled {count_filled} movie names into Column D for **{active_tab}**!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Groq AI Extraction Error: {e}")

    # --------------------------------------------------------------------------
    # INTERACTIVE CELL DATA EDITOR
    # --------------------------------------------------------------------------
    st.markdown("#### ✏️ Interactive Data Grid (Edit Cells, Add or Delete Rows)")
    
    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Topic Number": st.column_config.TextColumn("Topic #", width="small", required=True),
            "Topic Headline": st.column_config.TextColumn("Movie Name / Topic Title (Col D)", width="medium"),
            "Malayalam News Text": st.column_config.TextColumn("Malayalam News Description / Script", width="large", required=True),
            "Image URLs": st.column_config.TextColumn("Image URL(s) [Comma Separated]", width="medium")
        },
        key=f"editor_{active_tab}"
    )

    # Save & Sync Button
    st.markdown(" ")
    btn_col1, btn_col2 = st.columns([2, 5])
    with btn_col1:
        if st.button("⚡ Save & Sync to Google Sheet", type="primary", use_container_width=True):
            st.session_state.edited_dfs[active_tab] = edited_df
            synced = st.session_state.sheet_mgr.update_tab_data(active_tab, edited_df)
            if synced:
                st.success(f"Saved & synced {len(edited_df)} rows for **{active_tab}**!")
            else:
                st.warning(f"Saved locally to cache for **{active_tab}**!")


# ==============================================================================
# SECTION 2: 📺 OUTPUT & VIDEO SLIDE PREVIEW
# ==============================================================================
elif st.session_state.current_section == "📺 Output & Video Slide Preview":
    st.header("📺 Output & Video Slide Preview")
    st.caption("Visual preview of each topic formatted as 1080p HD presentation slides with poster images and Malayalam typography.")

    # Category Tab Selection
    tab_cols = st.columns(3)
    tab_names = ["Movie Updates", "Release Updates", "OTT Updates"]
    tab_icons = ["🎬 Movie Updates", "📅 Release Updates", "🍿 OTT Updates"]

    for i, t_name in enumerate(tab_names):
        with tab_cols[i]:
            if st.button(tab_icons[i], use_container_width=True, type="primary" if st.session_state.current_tab == t_name else "secondary"):
                st.session_state.current_tab = t_name
                st.rerun()

    active_tab = st.session_state.current_tab
    current_df = st.session_state.edited_dfs.get(active_tab, pd.DataFrame())

    if current_df.empty:
        st.warning(f"No topics found for **{active_tab}**. Go to Input section to add topics.")
    else:
        st.subheader(f"Topic Slide Previews: **{active_tab}** ({len(current_df)} topics)")

        # Full Video Render Trigger Button at Top
        with st.expander("🎬 **1. Render Full Video MP4 from Current Sheets**", expanded=True):
            st.write("Triggers complete broadcast audio synthesis and 1080p MP4 rendering pipeline.")
            if st.button("🚀 Render Full Video Now", type="primary"):
                with st.spinner("Rendering full video... (This generates audio voice & combines 1080p video clips)"):
                    try:
                        for t_name, df_item in st.session_state.edited_dfs.items():
                            st.session_state.sheet_mgr.update_tab_data(t_name, df_item)
                        
                        cmd1 = ["python", "generate_from_google_sheet.py", "edge_female"]
                        res1 = subprocess.run(cmd1, cwd=str(BASE_DIR), capture_output=True, text=True)

                        cmd2 = ["python", "generate_video_from_audio_and_images.py"]
                        res2 = subprocess.run(cmd2, cwd=str(BASE_DIR), capture_output=True, text=True)

                        video_path = OUTPUT_DIR / "Malayalam_Movie_News_Presenter_1080p.mp4"
                        if video_path.exists():
                            st.success("🎉 Video Rendered Successfully!")
                            st.video(str(video_path))
                        else:
                            st.error(f"Render failed:\n{res2.stderr}")
                    except Exception as e:
                        st.error(f"Error executing video render pipeline: {e}")

        # YouTube Auto Uploader Section
        with st.expander("🔴 **2. Upload Video to YouTube (Auto Metadata & Google Drive Thumbnail)**", expanded=True):
            st.write("Upload rendered MP4 video directly to YouTube with English SEO title, timestamp chapters, hashtags, and custom Google Drive thumbnail.")

            from metadata_generator import generate_english_title, generate_youtube_description, generate_youtube_tags, download_thumbnail_from_drive
            from youtube_uploader import YouTubeUploader

            drive_url = st.text_input("📁 Google Drive Thumbnail Link (Optional)", value="", help="Paste shareable link to custom thumbnail image on Google Drive")
            privacy_choice = st.selectbox("🔒 YouTube Privacy Status", options=["unlisted", "private", "public"], index=0)

            # Auto Preview Metadata
            english_title = generate_english_title()
            desc_preview = generate_youtube_description(st.session_state.edited_dfs)

            st.markdown(f"**Generated English Title**: `{english_title}`")
            with st.expander("📝 View Generated Description & Chapters"):
                st.code(desc_preview)

            if st.button("🔴 Upload Video to YouTube Now", type="primary", use_container_width=True):
                video_file = OUTPUT_DIR / "Malayalam_Movie_News_Presenter_1080p.mp4"
                if not video_file.exists():
                    st.error("Please render the video first by clicking 'Render Full Video Now' above.")
                else:
                    with st.spinner("Uploading video to YouTube... Please complete Google login if prompted."):
                        try:
                            # 1. Download thumbnail from Drive if provided
                            thumb_path = None
                            if drive_url.strip():
                                thumb_path = download_thumbnail_from_drive(drive_url)
                                if thumb_path:
                                    st.success("✓ Downloaded thumbnail from Google Drive!")

                            # 2. Upload to YouTube
                            uploader = YouTubeUploader()
                            result = uploader.upload_video(
                                video_path=str(video_file),
                                title=english_title,
                                description=desc_preview,
                                tags=generate_youtube_tags(),
                                privacy_status=privacy_choice,
                                thumbnail_path=thumb_path
                            )

                            if result.get("status") == "success":
                                st.balloons()
                                st.success(f"🎉 **Video Uploaded Successfully to YouTube!**")
                                st.markdown(f"### 🔗 YouTube Video Link: [{result['video_url']}]({result['video_url']})")
                                st.markdown(f"- **Privacy Status**: `{result['privacy_status']}`")
                                if result.get("thumbnail_uploaded"):
                                    st.markdown(" - **Thumbnail Status**: Custom Thumbnail Uploaded ✓")
                        except Exception as e:
                            st.error(f"YouTube Upload Error: {e}")

        # GitHub Actions 24/7 Cloud Render & YouTube Uploader Section
        with st.expander("⚡ **3. 24/7 Cloud Render & YouTube Upload (GitHub Actions)**", expanded=True):
            st.write("Trigger cloud-based 24/7 video rendering and YouTube upload pipeline directly on GitHub Actions runners.")

            from github_trigger import trigger_github_workflow

            col_cloud1, col_cloud2 = st.columns([2, 1])
            with col_cloud1:
                cloud_drive_url = st.text_input(
                    "📁 Custom Google Drive Thumbnail URL (Optional)",
                    value="",
                    help="Paste shareable link to thumbnail image stored on Google Drive",
                    key="cloud_thumb_input"
                )
            with col_cloud2:
                cloud_privacy_choice = st.selectbox(
                    "🔒 YouTube Privacy Status",
                    options=["unlisted", "private", "public"],
                    index=0,
                    help="Choose visibility mode for uploaded YouTube video",
                    key="cloud_privacy_select"
                )

            if st.button("🚀 Trigger 24/7 Cloud Render & Upload Now", type="primary", use_container_width=True, key="btn_trigger_cloud"):
                with st.spinner("Syncing latest sheet data & dispatching GitHub Action runner..."):
                    try:
                        # 1. Sync latest edited tables to Google Sheets online
                        for t_name, df_item in st.session_state.edited_dfs.items():
                            st.session_state.sheet_mgr.update_tab_data(t_name, df_item)

                        # 2. Trigger GitHub Action Workflow
                        res = trigger_github_workflow(
                            privacy_status=cloud_privacy_choice,
                            drive_thumbnail_url=cloud_drive_url
                        )

                        if res.get("status") == "success":
                            st.balloons()
                            st.success(f"🎉 **Cloud Pipeline Triggered Successfully!**")
                            st.markdown(f"### 🔗 View Workflow Run Status: [{res['actions_url']}]({res['actions_url']})")
                            st.markdown(f"- **YouTube Privacy Status**: `{res['privacy_status']}`")
                            if res.get("drive_thumbnail_url"):
                                st.markdown(f"- **Thumbnail URL Attached**: `{res['drive_thumbnail_url']}`")
                        else:
                            st.error(f"❌ {res.get('message')}")
                    except Exception as e:
                        st.error(f"Cloud Dispatch Error: {e}")

        st.markdown("---")

        # Display Live Preview Cards for Each Topic
        for idx, row in current_df.iterrows():
            topic_num = idx + 1
            topic_text = str(row.get("Malayalam News Text", "")).strip()
            img_urls = str(row.get("Image URLs", "")).strip()
            topic_headline = str(row.get("Topic Headline", row.get("Headline", ""))).strip()

            if not topic_text:
                continue

            with st.spinner(f"Rendering slide preview for Topic #{topic_num}..."):
                prev_data = st.session_state.preview_eng.generate_topic_preview(
                    section_name=active_tab,
                    topic_idx=topic_num,
                    topic_text=topic_text,
                    image_urls_str=img_urls,
                    topic_headline=topic_headline
                )

            # Topic Card UI
            with st.container():
                st.markdown(f"### 📌 Topic #{topic_num}: **{prev_data['title_en']}**")
                
                col_img1, col_img2 = st.columns([3, 2])

                with col_img1:
                    st.markdown("**📺 1080p Video Slide Visual**")
                    if prev_data["preview_slide_path"] and Path(prev_data["preview_slide_path"]).exists():
                        st.image(prev_data["preview_slide_path"], use_container_width=True)

                with col_img2:
                    st.markdown("**🖼️ Details & Poster**")
                    st.markdown(f"- **Movie Title**: `{prev_data['title_en']}`")
                    if prev_data["plat_en"] and prev_data["plat_en"] != "OTT":
                        st.markdown(f"- **OTT Platform**: `{prev_data['plat_en']}`")
                    st.markdown(f"- **Release Date**: `{prev_data['date_en']}`")
                    
                    if prev_data["poster_path"] and Path(prev_data["poster_path"]).exists():
                        st.image(prev_data["poster_path"], width=180, caption="Poster Image")
                    else:
                        st.info("No poster image loaded.")

                with st.expander("🗣️ View Malayalam Voiceover Narration Script"):
                    st.write(prev_data["topic_text"])

                st.markdown("---")

