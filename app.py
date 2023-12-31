from flask import Flask, request, jsonify, send_file
from ytmusicapi import YTMusic
from pytube import YouTube
import tempfile
import requests
import os
from pydub import AudioSegment
import io

app = Flask(__name__)
yt = YTMusic()


@app.route("/suggestions", methods=["POST"])
def suggestions():
    data = request.get_json()
    query = data.get("query")
    suggestions = yt.get_search_suggestions(query)
    return jsonify(suggestions)


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query = data.get("query")
    results = yt.search(query, filter="songs", limit=10)
    songsData = []

    for song in results:
        songData = {
            "id": song["videoId"],
            "title": song["title"],
            "artist": song["artists"][0]["name"],
            "thumbnail_url": song["thumbnails"][-1]["url"],
            "duration": song["duration"],
        }
        songsData.append(songData)
    return jsonify(songsData)


def getLyricsMusixmatch(title, artist):
    try:
        query = title + " " + artist
        res = requests.get(
            f"https://paxsenixofc.my.id/server/getLyricsMusix.php?q={query}&type=default"
        )
        if "fatal error" in res.text.lower():
            return ""
        else:
            return res.text
    except:
        return ""


def getLyricsYtMusic(id):
    data = yt.get_watch_playlist(id)
    lyricsId = data["lyrics"]
    try:
        lyrics = yt.get_lyrics(lyricsId)["lyrics"]
        return lyrics
    except:
        return ""


@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    id = data.get("id")
    title = data.get("title")
    artist = data.get("artist")
    video = YouTube(f"https://music.youtube.com/watch?v={id}")

    with tempfile.TemporaryDirectory() as tempDir:
        video.streams.filter(only_audio=True, abr="128kbps").first().download(
            tempDir, filename="audio.m4a"
        )
        data = {"api_token": "f3GS8yKdgff1ZZfZh64LJFLHE8tHAU", "sep_type": 25}
        filePath = os.path.join(tempDir, "audio.m4a")
        with open(filePath, "rb") as file:
            files = {"audiofile": ("audio.m4a", file, "audio/m4a")}
            response = requests.post(
                "https://mvsep.com/api/separation/create", data=data, files=files
            )

        lyrics = ""
        musixmatchLyrics = getLyricsMusixmatch(title, artist)
        if musixmatchLyrics != "":
            lyrics = musixmatchLyrics
            print("Using Musixmatch Lyrics")
        else:
            ytmusicLyrics = getLyricsYtMusic(id)
            if ytmusicLyrics != "":
                lyrics = ytmusicLyrics
                print("Using Yt Music Lyrics")

        response = response.json()
        if response["success"]:
            return jsonify(
                {
                    "link": response["data"]["link"],
                    "done": True,
                    "lyrics": lyrics,
                }
            )
        else:
            return jsonify(
                {
                    "reason": "Server is busy! Please try after some time.",
                    "done": False,
                }
            )


@app.route("/merge", methods=["POST"])
def merge():
    first_audio = request.files["first"]
    second_audio = request.files["second"]
    sound1 = AudioSegment.from_file(first_audio)
    sound2 = AudioSegment.from_file(second_audio)
    sound1 = sound1 - 6
    byte_arr = io.BytesIO()
    combined = sound1.overlay(sound2)
    combined.export(byte_arr, format="mp3")
    byte_arr.seek(0)
    return send_file(byte_arr, mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run()
