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

_cache      = {"data": None, "ts": 0}
_yt_cache   = {"data": None, "ts": 0}
_jobs_cache = {"data": None, "ts": 0}

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

    HIDDEN_USERNAMES = {"machiavellian", "xqrmn"}
    HIDDEN_IDS = {"1496246092965347358", "295295355883487235"}

    students = []
    for row in rows[4:]:
        if len(row) >= 5 and row[0].strip().isdigit():
            discord_id = str(row[2]).strip().split(".")[0]
            if row[1].lower() in HIDDEN_USERNAMES or discord_id in HIDDEN_IDS:
                continue
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
    students.sort(key=lambda x: x["credits"], reverse=True)
    _cache["data"] = students
    _cache["ts"] = now
    return students


def get_jobs():
    now = time.time()
    if _jobs_cache["data"] is not None and now - _jobs_cache["ts"] < CACHE_TTL:
        return _jobs_cache["data"]

    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID).worksheet("Jobs")
        rows = ws.get_all_values()
    except Exception:
        return _jobs_cache["data"] or []

    jobs = []
    for row in rows[1:]:  # skip header
        if len(row) >= 9 and row[8] in ("active", "completed"):
            try:
                reward = int(row[5]) if row[5].strip() else 0
            except ValueError:
                reward = 0
            jobs.append({
                "id":      row[0],
                "poster":  row[1],
                "title":   row[3],
                "desc":    row[4],
                "reward":  reward,
                "posted":  row[6],
                "expires": row[7],
                "status":  row[8],
                "claimer": row[9] if len(row) > 9 else "",
            })

    _jobs_cache["data"] = jobs
    _jobs_cache["ts"] = now
    return jobs


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


@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


@app.route("/api/jobs")
def api_jobs():
    return jsonify(get_jobs())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
