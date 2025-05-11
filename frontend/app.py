import streamlit as st
import requests
from enum import Enum
from typing import Dict

BACKEND_URL = "http://localhost:8000"

# ─── Allowed Languages Enum and Mapping ────────────────────────────────
class AllowedLanguage(str, Enum):
    Afrikaans = "Afrikaans"
    Albanian = "Albanian"
    Arabic = "Arabic"
    Bengali = "Bengali"
    Chinese = "Chinese"
    Dutch = "Dutch"
    English = "English"
    French = "French"
    German = "German"
    Hindi = "Hindi"
    Italian = "Italian"
    Japanese = "Japanese"
    Korean = "Korean"
    Portuguese = "Portuguese"
    Russian = "Russian"
    Spanish = "Spanish"
    Swahili = "Swahili"
    Tamil = "Tamil"
    Turkish = "Turkish"
    Urdu = "Urdu"
    Vietnamese = "Vietnamese"

allowed_languages_codes: Dict[AllowedLanguage, str] = {
    AllowedLanguage.Afrikaans: "af",
    AllowedLanguage.Albanian: "sq",
    AllowedLanguage.Arabic: "ar",
    AllowedLanguage.Bengali: "bn",
    AllowedLanguage.Chinese: "zh",
    AllowedLanguage.Dutch: "nl",
    AllowedLanguage.English: "en",
    AllowedLanguage.French: "fr",
    AllowedLanguage.German: "de",
    AllowedLanguage.Hindi: "hi",
    AllowedLanguage.Italian: "it",
    AllowedLanguage.Japanese: "ja",
    AllowedLanguage.Korean: "ko",
    AllowedLanguage.Portuguese: "pt",
    AllowedLanguage.Russian: "ru",
    AllowedLanguage.Spanish: "es",
    AllowedLanguage.Swahili: "sw",
    AllowedLanguage.Tamil: "ta",
    AllowedLanguage.Turkish: "tr",
    AllowedLanguage.Urdu: "ur",
    AllowedLanguage.Vietnamese: "vi",
}

# Pre-compute list of display names
language_names = [lang.value for lang in AllowedLanguage]

# ─── PAGE CONFIG & TITLE ───────────────────────────────────────────────
st.set_page_config(
    page_title="🎥 Video Subtitle Generator",
    page_icon="🎬",
    layout="centered",
)

st.markdown("<h1 style='text-align: center;'>🎥 Video Subtitle Generator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Powered by Google Gemini AI 🤖</p>", unsafe_allow_html=True)

tab1, tab2 = st.tabs([
    "🎙️ Generate Subtitles", 
    "🌐 Translate SRT"
])

### --- Tab 1: Video → SRT ---
with tab1:
    st.subheader("🎞️ Upload & Generate")
    video_file = st.file_uploader(
        "Select a video file", 
        type=["mp4", "mkv", "mov"], 
        help="Supported formats: mp4, mkv, mov"
    )

    # Display only the names
    target_name = st.selectbox(
        "🌍 Choose output language", 
        options=language_names,
        help="This language will be used for subtitles"
    )
    # Map back to enum and code
    target_enum = AllowedLanguage(target_name)
    target_lang = allowed_languages_codes[target_enum]

    if st.button("🔊 Extract & Subtitle", use_container_width=True) and video_file:
        # 1) Extract audio
        with st.spinner("⏳ Extracting audio..."):
            files = {"file": (video_file.name, video_file.getvalue(), video_file.type)}
            r1 = requests.post(f"{BACKEND_URL}/extract-audio/", files=files)
            r1.raise_for_status()
            data = r1.json()
            wav_bytes = bytes.fromhex(data["data"])

        # 2) Generate subtitles
        with st.spinner("✍️ Generating subtitles..."):
            files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
            payload = {"target_lang": target_lang}
            r2 = requests.post(f"{BACKEND_URL}/generate-subs/", files=files, data=payload)
            r2.raise_for_status()
            srt_text = r2.text

        st.success("✅ Subtitles ready!")
        st.download_button(
            "📥 Download SRT",
            srt_text,
            file_name=f"subtitles_{target_lang}.srt",
            mime="text/plain",
            use_container_width=True
        )

### --- Tab 2: SRT Translation ---
with tab2:
    st.subheader("🔁 Translate Existing SRT")
    srt_file = st.file_uploader(
        "Select an SRT file", 
        type=["srt"], 
        help="Upload your .srt file here"
    )

    if srt_file:
        col1, col2 = st.columns(2)
        with col1:
            from_name = st.selectbox(
                "🔤 From", 
                options=language_names,
                index=language_names.index("English")
            )
            from_lang = allowed_languages_codes[AllowedLanguage(from_name)]
        with col2:
            to_name = st.selectbox(
                "🔤 To", 
                options=language_names,
                index=language_names.index("Spanish")
            )
            to_lang = allowed_languages_codes[AllowedLanguage(to_name)]

        if st.button("🌐 Translate SRT", use_container_width=True):
            with st.spinner("🔄 Translating subtitles..."):
                files = {"file": (srt_file.name, srt_file.getvalue(), "text/plain")}
                data = {"from_lang": from_lang, "to_lang": to_lang}
                r = requests.post(f"{BACKEND_URL}/translate-srt/", files=files, data=data)
                r.raise_for_status()
                translated = r.text

            st.success("✅ Translation ready!")
            st.download_button(
                "📥 Download Translated SRT",
                translated,
                file_name=f"{srt_file.name.rsplit('.',1)[0]}_{to_lang}.srt",
                mime="text/plain",
                use_container_width=True
            )

# ─── FOOTER ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "👨‍💻 Developed by [Sayrikey1](https://github.com/Sayrikey1)",
    unsafe_allow_html=True
)
