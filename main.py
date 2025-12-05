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

# Set up ngrok tunnel for HTTPS redirect URI
def setup_ngrok_tunnel():
    ngrok_path = os.path.expanduser('~\\AppData\\Local\\Microsoft\\WindowsApps\\ngrok.exe')
    try:
        # Start ngrok tunnel on port 5000
        subprocess.Popen([ngrok_path, 'http', '5000', '--log', 'stdout'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)  # Give ngrok time to start and connect
        
        # Get ngrok public URL from the API
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            tunnels = response.json()
            if tunnels.get('tunnels'):
                public_url = tunnels['tunnels'][0]['public_url']
                return f"{public_url}/callback"
        except Exception as e:
            print(f"Could not retrieve ngrok tunnel URL: {e}")
    except Exception as e:
        print(f"Error starting ngrok: {e}")
    return None

ngrok_redirect = setup_ngrok_tunnel()
REDIRECT_URI = os.getenv('REDIRECT_URI', ngrok_redirect or 'http://localhost:5000/callback')

if ngrok_redirect:
    print(f"\n{'='*70}")
    print(f"NGROK TUNNEL ACTIVE!")
    print(f"Register this redirect URI in Spotify Developer Dashboard:")
    print(f"  {REDIRECT_URI}")
    print(f"{'='*70}\n")

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
        return jsonify({'error': request.args['error']})
    
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
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        
        return redirect('/menu')

@app.route('/menu')
def menu():
    if 'access_token' not in session:
        return redirect('/login')
    
    html = """
    <h1>Spotify Stats Menu</h1>
    <h2>Top 5</h2>
    <ul>
        <li><a href='/top_tracks'>Top 5 Tracks</a></li>
        <li><a href='/top_artists'>Top 5 Artists</a></li>
        <li><a href='/top_albums'>Top 5 Albums</a></li>
    </ul>
    <h2>Most Recent 5</h2>
    <ul>
        <li><a href='/recent_tracks'>Recent 5 Tracks</a></li>
        <li><a href='/recent_artists'>Recent 5 Artists</a></li>
        <li><a href='/recent_albums'>Recent 5 Albums</a></li>
    </ul>
    <h2>Other</h2>
    <ul>
        <li><a href='/playlists'>All Playlists</a></li>
    </ul>
    <a href='/'>Back to home</a>
    """
    return html

@app.route('/top_tracks')
def get_top_tracks():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/top/tracks?limit=5', headers=headers)
    top_tracks = response.json()
    
    track_titles = []
    if 'items' in top_tracks:
        for item in top_tracks['items']:
            if 'name' in item:
                track_titles.append(item['name'])
    
    html = "<h1>Your Top 5 Tracks</h1><ol>"
    for title in track_titles:
        html += f"<li>{title}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/top_artists')
def get_top_artists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/top/artists?limit=5', headers=headers)
    top_artists = response.json()
    
    artist_names = []
    if 'items' in top_artists:
        for item in top_artists['items']:
            if 'name' in item:
                artist_names.append(item['name'])
    
    html = "<h1>Your Top 5 Artists</h1><ol>"
    for name in artist_names:
        html += f"<li>{name}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/top_albums')
def get_top_albums():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
    recently_played = response.json()
    
    # Extract unique album names from recently played (top albums derived from recent tracks)
    albums_seen = set()
    album_names = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            if 'track' in item and 'album' in item['track']:
                album = item['track']['album']['name']
                if album not in albums_seen:
                    albums_seen.add(album)
                    album_names.append(album)
                    if len(album_names) >= 5:
                        break
    
    html = "<h1>Your Top 5 Albums (from Recently Played)</h1><ol>"
    for name in album_names:
        html += f"<li>{name}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/recent_tracks')
def get_recent_tracks():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=5', headers=headers)
    recently_played = response.json()
    
    track_titles = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            if 'track' in item and 'name' in item['track']:
                track_titles.append(item['track']['name'])
    
    html = "<h1>Your Most Recent 5 Tracks</h1><ol>"
    for title in track_titles:
        html += f"<li>{title}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/recent_artists')
def get_recent_artists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
    recently_played = response.json()
    
    tracks_seen = set()
    artist_groups = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            if 'track' in item and 'id' in item['track']:
                track_id = item['track']['id']
                # Only process each track once
                if track_id not in tracks_seen:
                    tracks_seen.add(track_id)
                    if 'artists' in item['track']:
                        artists = [artist['name'] for artist in item['track']['artists'] if 'name' in artist]
                        if artists:
                            artist_groups.append(', '.join(artists))
                            if len(artist_groups) >= 5:
                                break
    
    html = "<h1>Your Most Recent 5 Artists</h1><ol>"
    for artist_group in artist_groups:
        html += f"<li>{artist_group}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/recent_albums')
def get_recent_albums():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
    recently_played = response.json()
    
    albums_seen = set()
    album_names = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            if 'track' in item and 'album' in item['track']:
                album = item['track']['album']['name']
                if album not in albums_seen:
                    albums_seen.add(album)
                    album_names.append(album)
                    if len(album_names) >= 5:
                        break
    
    html = "<h1>Your Most Recent 5 Albums</h1><ol>"
    for name in album_names:
        html += f"<li>{name}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
    return html

@app.route('/playlists')
def get_playlists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + '/me/playlists', headers=headers)
    playlists_data = response.json()
    
    playlist_names = []
    if 'items' in playlists_data:
        for item in playlists_data['items']:
            if 'name' in item:
                playlist_names.append(item['name'])
    
    html = "<h1>Your Playlists</h1><ol>"
    for name in playlist_names:
        html += f"<li>{name}</li>"
    html += "</ol><a href='/menu'>Back to menu</a>"
    
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