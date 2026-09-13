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
    current_df = st.session_state.edited_dfs.get(active_tab, pd.DataFrame(columns=["Topic Number", "Malayalam News Text", "Image URLs"]))

    # --------------------------------------------------------------------------
    # 1. BULK TABLE PASTE BOX
    # --------------------------------------------------------------------------
    with st.expander("📋 **Paste Entire Table at Once (Excel / Google Sheets Copy-Paste)**", expanded=False):
        st.write("Copy rows from Excel or Google Sheets and paste them below:")
        paste_text = st.text_area(
            "Paste Table Content Here",
            height=130,
            placeholder="1\tമമ്മൂട്ടിയുടെ പുതിയ ചിത്രം മേള പ്രഖ്യാപിച്ചു...\thttps://example.com/poster1.jpg\n2\tമോഹൻലാൽ ചിത്രം എൽ370 അപ്ഡേറ്റ്...\thttps://example.com/poster2.jpg"
        )
        col_p1, col_p2 = st.columns([1, 4])
        with col_p1:
            if st.button("📥 Import Pasted Table", type="primary"):
                if paste_text.strip():
                    parsed_df = st.session_state.sheet_mgr.parse_pasted_table(paste_text)
                    if not parsed_df.empty:
                        st.session_state.edited_dfs[active_tab] = parsed_df
                        st.session_state.sheet_mgr.update_tab_data(active_tab, parsed_df)
                        st.success(f"Successfully imported {len(parsed_df)} topic rows into {active_tab}!")
                        st.rerun()
                    else:
                        st.error("Could not parse table data. Please check pasted text format.")
                else:
                    st.warning("Please paste some text first.")

    # --------------------------------------------------------------------------
    # 2. INTERACTIVE CELL DATA EDITOR
    # --------------------------------------------------------------------------
    st.markdown("#### ✏️ Interactive Data Grid (Edit Cells, Add or Delete Rows)")
    
    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Topic Number": st.column_config.TextColumn("Topic #", width="small", required=True),
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

        st.markdown("---")

        # Display Live Preview Cards for Each Topic
        for idx, row in current_df.iterrows():
            topic_num = idx + 1
            topic_text = str(row.get("Malayalam News Text", "")).strip()
            img_urls = str(row.get("Image URLs", "")).strip()

            if not topic_text:
                continue

            with st.spinner(f"Rendering slide preview for Topic #{topic_num}..."):
                prev_data = st.session_state.preview_eng.generate_topic_preview(
                    section_name=active_tab,
                    topic_idx=topic_num,
                    topic_text=topic_text,
                    image_urls_str=img_urls
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

