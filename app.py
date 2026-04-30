import os
import time
import json
import re
import urllib.request
import tempfile
from flask import Flask, render_template, jsonify
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

SHEET_ID  = "1SXXwbx9x5OIY0wQrlg2KrNexhqCAoDlKJnHx6EEv1S0"
CACHE_TTL = 60
YT_TTL    = 600

_cache    = {"data": None, "ts": 0}
_yt_cache = {"data": None, "ts": 0}

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    raw = os.environ.get("GOOGLE_CREDENTIALS")
    if raw:
        info = json.loads(raw)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)
    return gspread.service_account(filename="D:/poweriq-bot/credentials.json")


def get_youtube_videos():
    now = time.time()
    if _yt_cache["data"] and now - _yt_cache["ts"] < YT_TTL:
        return _yt_cache["data"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request("https://www.youtube.com/@THEPOWERIQ/videos", headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8")

    video_ids = list(dict.fromkeys(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)))[:8]

    videos = []
    for vid_id in video_ids:
        try:
            oe_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json"
            oe_req = urllib.request.Request(oe_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(oe_req, timeout=5) as r:
                oe = json.loads(r.read())
            videos.append({
                "id":        vid_id,
                "title":     oe.get("title", ""),
                "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                "url":       f"https://www.youtube.com/watch?v={vid_id}",
            })
        except Exception:
            videos.append({
                "id":        vid_id,
                "title":     "",
                "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                "url":       f"https://www.youtube.com/watch?v={vid_id}",
            })

    _yt_cache["data"] = videos
    _yt_cache["ts"]   = now
    return videos


def get_students():
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        return _cache["data"]

    gc = get_gspread_client()
    ws = gc.open_by_key(SHEET_ID).worksheet("Credits")
    rows = ws.get_all_values()

    students = []
    for row in rows[4:]:
        if len(row) >= 5 and row[0].strip().isdigit():
            try:
                credits = int(row[4]) if row[4].strip() else 0
            except ValueError:
                credits = 0
            students.append({
                "num":      row[0],
                "username": row[1],
                "class":    row[3] if len(row) > 3 else "N/A",
                "credits":  credits,
            })

    BANKERS = {"machiavellian", "xqrmn"}
    students = [s for s in students if s["username"].lower() not in BANKERS]
    students.sort(key=lambda x: x["credits"], reverse=True)
    _cache["data"] = students
    _cache["ts"] = now
    return students


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/credits")
def credits():
    return render_template("credits.html")


@app.route("/library")
def library():
    return render_template("library.html")


@app.route("/api/students")
def api_students():
    return jsonify(get_students())


@app.route("/api/youtube")
def api_youtube():
    return jsonify(get_youtube_videos())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
