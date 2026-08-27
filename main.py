from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
import os
import re

app = FastAPI()

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
        return {
            "title": "YouTube Video",
            "video_id": "Unknown",
            "transcript": "YouTube video link provided."
        }
    
    # Try fetching transcript with multiple safe fallbacks
    transcript_text = ""
    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en', 'en-US', 'hi-IN'])
            transcript_text = " ".join([t['text'] for t in transcript_list])
        except:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id).find_transcript(['hi', 'en']).fetch()
            transcript_text = " ".join([t['text'] for t in transcript_list])
    except Exception:
        # Fail-safe: If YouTube blocks IP or CC is disabled, pass video_id gracefully
        transcript_text = f"Video ID: {video_id} - Topic analysis requested for this video link."

    return {
        "title": f"YouTube Video ({video_id})",
        "video_id": video_id,
        "transcript": transcript_text[:3000]
    }

@app.post("/api/generate-seo-pack")
def generate_seo_pack(data: dict):
    transcript = data.get("transcript", "")
    video_id = data.get("video_id", "Unknown")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    You are an expert YouTube SEO consultant. Create a complete viral SEO pack for a video based on this context or Video ID: {video_id}.
    
    Context/Transcript:
    {transcript}
    
    Please provide:
    1. 5 High CTR Clickworthy Titles (with emojis)
    2. Detailed SEO Optimized Description (including hashtag recommendations & timestamp structure)
    3. 15-20 Viral High-Volume Tags (comma separated)
    """
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"seo_pack": response.choices[0].message.content}
