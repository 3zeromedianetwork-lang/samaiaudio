import os
import re
import tempfile
import streamlit as st
import yt_dlp
import requests
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Audio Transcriber", page_icon="🎙️", layout="wide")

# Hide Streamlit header, footer, and menu (including Deploy button)
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Load API key directly from environment
api_key = os.getenv("GROQ_API_KEY", "")

st.title("🎙️ AI Audio Transcriber")
st.markdown("Transcribe audio from a YouTube video or an uploaded file using **Groq (Whisper-Large-V3)**.")
st.markdown("*Note: Groq supports ultra-fast transcription for audio files up to 25MB.*")

tab1, tab2 = st.tabs(["🎥 YouTube URL", "📁 Upload Audio File"])

def transcribe_with_groq(audio_file_path, key):
    file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
    if file_size_mb > 25:
        raise Exception(f"File size is {file_size_mb:.1f}MB. Groq API limits uploads to 25MB. Please use a shorter audio file.")
        
    with open(audio_file_path, "rb") as f:
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": f},
            data={"model": "whisper-large-v3"}
        )
        
    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        raise Exception(f"Groq API Error {response.status_code}: {response.text}")

with tab1:
    st.markdown("**Instructions**")
    st.markdown("1. Paste a YouTube URL")
    st.markdown("2. Click **Transcribe**")

    youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

    col1, col2 = st.columns(2)
    with col1:
        yt_transcribe_btn = st.button("🎬 Transcribe Audio", type="primary", use_container_width=True, key="yt_btn")
    with col2:
        yt_clear_btn = st.button("🗑️ Clear", use_container_width=True, key="yt_clear")

    if yt_clear_btn:
        st.rerun()

    if yt_transcribe_btn:
        if not api_key:
            st.error("Groq API key not found in .env file.")
        elif not youtube_url.strip():
            st.error("Please enter a valid YouTube URL.")
        elif not re.match(r"^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$", youtube_url.strip()):
            st.error("Invalid YouTube URL format.")
        else:
            temp_dir = tempfile.mkdtemp(prefix="yt_audio_")
            audio_path = None

            try:
                with st.spinner("📥 Downloading audio from YouTube..."):
                    audio_path = os.path.join(temp_dir, "audio.%(ext)s")
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "64", # Use lower quality to stay under 25MB
                            }
                        ],
                        
                        "outtmpl": audio_path,
                        "quiet": True,
                        "no_warnings": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(youtube_url.strip(), download=True)
                        video_title = info.get("title", "Unknown Title")
                        duration = info.get("duration", 0)

                    audio_path = os.path.join(temp_dir, "audio.mp3")
                    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

                    st.success(f"✅ Downloaded: **{video_title}**")
                    st.caption(f"Duration: {duration // 60}m {duration % 60}s | File size: {file_size_mb:.2f} MB")

                with st.spinner("🤖 Transcribing audio with Groq (Whisper-Large-V3)..."):
                    transcript_text = transcribe_with_groq(audio_path, api_key)

                if transcript_text:
                    st.subheader("📝 Transcription")
                    st.text_area("Transcript", transcript_text, height=400, key="yt_text")
                    st.download_button(
                        "💾 Download Transcript",
                        transcript_text,
                        file_name=f"{video_title.replace(' ', '_').replace('/', '_')}_transcript.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="yt_download"
                    )

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir(temp_dir)

with tab2:
    st.markdown("**Instructions**")
    st.markdown("1. Upload an audio file (mp3, wav, m4a)")
    st.markdown("2. Click **Transcribe File**")

    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a"])

    col3, col4 = st.columns(2)
    with col3:
        file_transcribe_btn = st.button("🎬 Transcribe File", type="primary", use_container_width=True, key="file_btn")
    with col4:
        file_clear_btn = st.button("🗑️ Clear", use_container_width=True, key="file_clear")

    if file_clear_btn:
        st.rerun()

    if file_transcribe_btn:
        if not api_key:
            st.error("Groq API key not found in .env file.")
        elif uploaded_file is None:
            st.error("Please upload an audio file.")
        else:
            try:
                with st.spinner("🤖 Transcribing uploaded audio with Groq (Whisper-Large-V3)..."):
                    temp_dir = tempfile.mkdtemp(prefix="uploaded_audio_")
                    temp_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    try:
                        transcript_text = transcribe_with_groq(temp_path, api_key)
                    finally:
                        os.remove(temp_path)
                        os.rmdir(temp_dir)

                if transcript_text:
                    st.subheader("📝 Transcription")
                    st.text_area("Transcript", transcript_text, height=400, key="file_text")
                    file_name_without_ext = os.path.splitext(uploaded_file.name)[0]
                    st.download_button(
                        "💾 Download Transcript",
                        transcript_text,
                        file_name=f"{file_name_without_ext}_transcript.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="file_download"
                    )
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
