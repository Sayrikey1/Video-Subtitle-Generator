import os
import tempfile
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import ffmpeg

from google import genai
from google.genai import types

# ─── Load env & init Gemini ────────────────────────────────────────────
load_dotenv(".env")
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY environment variable is not set")
genai_client = genai.Client(api_key=api_key)

# ─── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI()


@app.post("/extract-audio/")
async def extract_audio(file: UploadFile = File(...)):
    """
    - Receives: video file (mp4, mkv, etc.)
    - Returns: audio in WAV format (hex-encoded)
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(400, "Must upload a video file")

    # Save upload
    suffix = os.path.splitext(file.filename)[1]
    tmp_video = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_video.write(await file.read())
    tmp_video.flush()
    tmp_video.close()

    # Prepare audio output
    tmp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_audio.close()

    # Extract audio with ffmpeg
    try:
        (
            ffmpeg
            .input(tmp_video.name)
            .output(tmp_audio.name, format="wav", acodec="pcm_s16le", ac=1, ar="16k")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        os.remove(tmp_video.name)
        os.remove(tmp_audio.name)
        raise HTTPException(500, f"FFmpeg error: {e.stderr.decode()}")

    # Read & cleanup
    audio_bytes = open(tmp_audio.name, "rb").read()
    os.remove(tmp_video.name)
    os.remove(tmp_audio.name)

    return {
        "filename": os.path.basename(tmp_audio.name),
        "content_type": "audio/wav",
        "data": audio_bytes.hex()
    }


@app.post(
    "/generate-subs/",
    response_class=PlainTextResponse,
    summary="Generate strict numbered SRT subtitles from WAV audio",
)
async def generate_subs(
    file: UploadFile = File(..., description="16kHz mono WAV audio"),
    target_lang: str = Form(..., description="e.g. 'en', 'fr', 'es'")
):
    """
    - Receives: WAV audio file + target language code
    - Returns: a strictly numbered SRT file (text/plain)
    """
    if file.content_type != "audio/wav":
        raise HTTPException(400, "Audio must be WAV (16kHz mono)")

    audio_bytes = await file.read()
    part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")

    prompt = f"""
You must output a valid, strictly numbered SRT file with these rules:
1) Each block begins with its sequence number.
2) Next line is the exact timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm).
3) A blank line.
4) The subtitle text, in {target_lang}.
Do NOT include any extra text, comments, code fences, or headings—only the SRT blocks.

Example:

1
00:00:00,000 --> 00:00:07,000

This could be the most important minute of your day.

2
00:00:07,000 --> 00:00:11,000

We have been through difficult times and faced big problems ahead.

Now, detect the language, transcribe the audio, translate into {target_lang}, and output the full SRT.
""".strip()

    resp = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[part, prompt]
    )

    return PlainTextResponse(
        resp.text.strip(),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=subtitles_{target_lang}.srt"
        }
    )


@app.post(
    "/translate-srt/",
    response_class=PlainTextResponse,
    summary="Translate an existing SRT to another language (strict numbered SRT)",
)
async def translate_srt(
    file: UploadFile = File(..., description="Original .srt file"),
    from_lang: str = Form(..., description="Source language code, e.g. 'en'"),
    to_lang: str = Form(..., description="Target language code, e.g. 'es'")
):
    """
    - Receives: SRT file + from_lang + to_lang
    - Returns: translated, strictly numbered SRT file (text/plain)
    """
    if file.content_type not in ("application/x-subrip", "text/plain"):
        raise HTTPException(400, "Upload must be an .srt file")

    srt_text = (await file.read()).decode("utf-8", errors="ignore")

    prompt = f"""
Translate the following SRT subtitles from {from_lang} to {to_lang}.  
Output must be a strictly numbered SRT file with:
1) The original sequence numbers.
2) The exact original timestamps (HH:MM:SS,mmm --> HH:MM:SS,mmm).
3) A blank line.
4) The translated text.

Do NOT add, remove, or reorder blocks, and do NOT include any additional commentary.

Example:

1
00:00:00,000 --> 00:00:07,000

This could be the most important minute of your day.

2
00:00:07,000 --> 00:00:11,000

We have been through difficult times and faced big problems ahead.

Now translate each block into {to_lang} and output the complete SRT.
""".strip()

    resp = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[srt_text, prompt]
    )

    return PlainTextResponse(
        resp.text.strip(),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=translated_{to_lang}.srt"
        }
    )
