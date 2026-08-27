from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
import os
import re
import requests

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

def get_official_yt_details(video_id: str):
    yt_key = os.getenv("YOUTUBE_API_KEY")
    if not yt_key:
        return None
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={yt_key}"
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        if "items" in data and len(data["items"]) > 0:
            snippet = data["items"][0]["snippet"]
            return {
                "title": snippet.get("title"),
                "description": snippet.get("description")
            }
    except Exception:
        pass
    return None

@app.get("/")
def read_root():
    return {"status": "Backend Live"}

@app.get("/api/get-transcript")
def get_transcript(video_url: str):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # 1. Fetch Official Title & Description via YouTube API
    official_data = get_official_yt_details(video_id)
    video_title = official_data["title"] if official_data else f"YouTube Video ({video_id})"
    video_desc = official_data["description"] if official_data else ""

    # 2. Fetch Transcript with fallbacks
    transcript_text = ""
    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en', 'en-US', 'hi-IN'])
            transcript_text = " ".join([t['text'] for t in transcript_list])
        except:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id).find_transcript(['hi', 'en']).fetch()
            transcript_text = " ".join([t['text'] for t in transcript_list])
    except Exception:
        # Fallback to description if subtitles are disabled
        transcript_text = video_desc[:2000] if video_desc else f"Topic based on title: {video_title}"

    return {
        "title": video_title,
        "video_id": video_id,
        "transcript": transcript_text[:3000]
    }

@app.post("/api/generate-seo-pack")
def generate_seo_pack(data: dict):
    title = data.get("title", "")
    transcript = data.get("transcript", "")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    You are an expert YouTube SEO consultant. Create a high-converting, viral SEO pack for this video.
    
    Original Video Title: {title}
    Video Context/Transcript/Description: {transcript}
    
    Output requirement:
    1. 5 High CTR Clickworthy Titles (with emojis)
    2. Detailed SEO Optimized Description (with hashtags & timestamps structure)
    3. 15-20 High-Volume Viral Tags (comma separated)
    """
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"seo_pack": response.choices[0].message.content}
