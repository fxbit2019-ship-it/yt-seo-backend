from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
import os
import re

app = FastAPI()

# CORS Allowed Links
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_video_id(url: str):
    regex = r"(?:v=|\/([0-9A-Za-z_-]{11})|youtu\.be\/)([0-9A-Za-z_-]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1) or match.group(2)
    return None

@app.get("/")
def read_root():
    return {"status": "Backend Live"}

@app.get("/api/get-transcript")
def get_transcript(video_url: str):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
        full_text = " ".join([t['text'] for t in transcript_list])
        return {
            "title": f"YouTube Video ({video_id})",
            "transcript": full_text[:4000]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-seo-pack")
def generate_seo_pack(data: dict):
    transcript = data.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript missing")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    You are an expert YouTube SEO consultant. Analyze this transcript and create:
    1. 5 High CTR Clickworthy Titles
    2. SEO Optimized Description (with Timestamps placeholders)
    3. 15-20 Viral Tags (comma separated)
    
    Transcript: {transcript}
    """
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"seo_pack": response.choices[0].message.content}
