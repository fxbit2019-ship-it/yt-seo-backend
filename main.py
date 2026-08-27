import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from groq import Groq

app = FastAPI()

# WordPress से API जोड़ने के लिए CORS Permission
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_video_id(url):
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url

@app.get("/api/get-transcript")
def get_transcript(video_url: str):
    video_id = extract_video_id(video_url)
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        title = info.get('title', '')

    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
    full_text = " ".join([entry['text'] for entry in transcript_list])
    
    return {
        "title": title,
        "transcript": full_text[:6000]
    }

@app.post("/api/generate-seo-pack")
def generate_seo_pack(data: dict):
    transcript = data.get("transcript")
    prompt = f"Act as a YouTube SEO Expert. Generate 5 Titles, 300-word SEO Description, Chapters, and 20 Viral Tags for this transcript: {transcript}"

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
    )
    return {"seo_pack": response.choices[0].message.content}
