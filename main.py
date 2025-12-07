import os
import requests
import urllib.parse
import subprocess
import time
import json

from flask import Flask, redirect, request, session, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = '84g299n6-179k-4228-m245-0r1629562837'

CLIENT_ID = os.getenv('CLIENT_ID', '2a061e08a3f94fd68b36a41fc9922a3b')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', '599323f77f88464fbe768772e4d4c716')

# Static ngrok domain for consistent redirect URI
NGROK_DOMAIN = 'easily-crankier-coleman.ngrok-free.dev'
REDIRECT_URI = os.getenv('REDIRECT_URI', f'https://{NGROK_DOMAIN}/callback')

# Start ngrok tunnel automatically
def start_ngrok():
    ngrok_path = os.path.expanduser('~\\AppData\\Local\\Microsoft\\WindowsApps\\ngrok.exe')
    try:
        subprocess.Popen([ngrok_path, 'http', '5000', f'--domain={NGROK_DOMAIN}'], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give ngrok time to start
        print("✓ ngrok tunnel started successfully")
    except Exception as e:
        print(f"Warning: Could not start ngrok: {e}")

start_ngrok()

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1'

@app.route('/')
def index():
    return f"Welcome to Kungungalcorgus.stats " + "<a href='/login'>Login with Spotify</a>"

@app.route('/login')
def login():
    scope = 'user-read-private user-read-email, user-read-playback-position user-top-read user-read-recently-played playlist-read-private'
    
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': scope,
        'show_dialog': True,
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    # If DEBUG_AUTH_URL=1 is set, return the full auth URL for inspection
    if os.getenv('DEBUG_AUTH_URL', '0') == '1':
        return auth_url

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        error_msg = request.args.get('error', 'Unknown error')
        error_desc = request.args.get('error_description', 'No description')
        return jsonify({'error': error_msg, 'description': error_desc})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info.get('refresh_token', session.get('refresh_token'))
        session['expires_at'] = datetime.now().timestamp() + token_info.get('expires_in', 3600)

        return redirect('/menu')

@app.route('/menu')
def menu():
    if 'access_token' not in session:
        return redirect('/login')
    
    html = """
    <h1>Spotify Stats Menu</h1>
    <ul>
        <li><a href='/recent_50_songs'>50 Recent</a></li>
    </ul>
    <a href='/'>Back to home</a>
    """
    return html

@app.route('/recent_50_songs')
def recent_50_songs():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
    recently_played = response.json()
    
    songs = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            if 'track' in item:
                track = item['track']
                song_name = track.get('name', 'Unknown')
                artists = ', '.join([artist['name'] for artist in track.get('artists', []) if 'name' in artist])
                album = track.get('album', {}).get('name', 'Unknown')
                duration_ms = track.get('duration_ms', 0)
                duration_min = duration_ms // 60000
                duration_sec = (duration_ms % 60000) // 1000
                duration = f"{duration_min}:{duration_sec:02d}"
                
                songs.append({
                    'name': song_name,
                    'artists': artists,
                    'album': album,
                    'duration': duration
                })
    
    # Save to txt file
    
    html = """
    <h1>Your 50 Most Recently Listened Songs</h1>
        <p><em>No data saved to file.</em></p>
    <table border="1" style="border-collapse: collapse; width: 100%;">
    <tr>
        <th style="padding: 10px; text-align: left;">Song Name</th>
        <th style="padding: 10px; text-align: left;">Artists</th>
        <th style="padding: 10px; text-align: left;">Album</th>
        <th style="padding: 10px; text-align: center;">Length</th>
    </tr>
    """
    
    for i, song in enumerate(songs, 1):
        html += f"""
        <tr>
            <td style="padding: 10px;">{song['name']}</td>
            <td style="padding: 10px;">{song['artists']}</td>
            <td style="padding: 10px;">{song['album']}</td>
            <td style="padding: 10px; text-align: center;">{song['duration']}</td>
        </tr>
        """
    
    html += """
    </table>
    <br>
    <a href='/menu'>Back to menu</a> | <a href='/'>Back to home</a>
    """
    
    return html

@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()
    
    session['access_token'] = new_token_info['access_token']
    session['refresh_token'] = new_token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
    
    return redirect('/playlists')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug = True)