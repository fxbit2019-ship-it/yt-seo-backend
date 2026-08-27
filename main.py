from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
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
    
    official_data = get_official_yt_details(video_id)
    video_title = official_data["title"] if official_data else f"YouTube Video ({video_id})"
    video_desc = official_data["description"] if official_data else ""

    transcript_text = ""
    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en', 'en-US', 'hi-IN'])
            transcript_text = " ".join([t['text'] for t in transcript_list])
        except:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id).find_transcript(['hi', 'en']).fetch()
            transcript_text = " ".join([t['text'] for t in transcript_list])
    except Exception:
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

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY missing in Render environment.")

    prompt_text = f"""
    You are an expert YouTube SEO consultant. Create a high-converting, viral SEO pack for this video.
    
    Original Video Title: {title}
    Video Context/Transcript/Description: {transcript}
    
    Output requirement:
    1. 5 High CTR Clickworthy Titles (with emojis)
    2. Detailed SEO Optimized Description (with hashtags & timestamps structure)
    3. 15-20 High-Volume Viral Tags (comma separated)
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        res_data = res.json()
        
        if res.status_code != 200:
            error_msg = res_data.get("error", {}).get("message", "Gemini API call failed")
            raise HTTPException(status_code=500, detail=f"Gemini Error: {error_msg}")
            
        seo_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return {"seo_pack": seo_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
