import os
import requests
import urllib.parse
import json
import subprocess
import time
import glob
import platform
import shutil
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, redirect, request, session, jsonify
from datetime import datetime, timedelta
from database import (
    init_database, insert_or_update_song, insert_or_update_artist,
    insert_or_update_album, link_song_artist_album, link_album_song,
    get_all_songs, get_all_artists, get_all_albums,
    get_or_create_user, get_user_playlists, insert_or_update_playlist,
    link_playlist_song, get_last_sync_timestamp, save_last_sync_timestamp
)

load_dotenv()

app = Flask(__name__)
app.secret_key = '84g299n6-179k-4228-m245-0r1629562837'

CLIENT_ID = os.getenv('CLIENT_ID', '2a061e08a3f94fd68b36a41fc9922a3b')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', '599323f77f88464fbe768772e4d4c716')

NGROK_DOMAIN = os.getenv('NGROK_DOMAIN', 'easily-crankier-coleman.ngrok-free.dev')
REDIRECT_URI = os.getenv('REDIRECT_URI', f'https://{NGROK_DOMAIN}/callback')
API_BASE_URL = 'https://api.spotify.com/v1'
TOKEN_FILE = 'spotify_token.json'

# Initialize database on startup
init_database()

# Create background scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def save_token_to_file(access_token, refresh_token, expires_at):
    """Save access token info to file for background job"""
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at
            }, f)
    except Exception as e:
        print(f"Error saving token: {e}")

def load_token_from_file():
    """Load access token info from file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading token: {e}")
    return None

def refresh_token_in_background():
    """Refresh the access token using the refresh token"""
    token_data = load_token_from_file()
    if not token_data:
        return None
    
    try:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': token_data['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post('https://accounts.spotify.com/api/token', data=req_body)
        if response.status_code == 200:
            new_token_info = response.json()
            new_expires_at = datetime.now().timestamp() + new_token_info['expires_in']
            save_token_to_file(
                new_token_info['access_token'],
                new_token_info.get('refresh_token', token_data['refresh_token']),
                new_expires_at
            )
            return new_token_info['access_token']
    except Exception as e:
        print(f"Error refreshing token: {e}")
    return None

def start_ngrok():
    system = platform.system()
    
    if system == 'Windows':
        ngrok_path = os.path.expanduser('~\\AppData\\Local\\Microsoft\\WindowsApps\\ngrok.exe')
    elif system == 'Darwin':
        ngrok_path = shutil.which('ngrok') or os.path.expanduser('~/.ngrok2/ngrok')
    else:
        ngrok_path = shutil.which('ngrok') or '/usr/local/bin/ngrok'
    
    try:
        subprocess.Popen([ngrok_path, 'http', '5000', f'--domain={NGROK_DOMAIN}'], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        print("✓ ngrok tunnel started successfully")
        print(f"   App available at: https://{NGROK_DOMAIN}")
        print(f"\n   IMPORTANT: You must configure ngrok authtoken on their machine:")
        print(f"   ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz")
        print(f"\n   See SETUP.md for full instructions.\n")
    except Exception as e:
        print(f"Warning: Could not start ngrok: {e}")
        print(f"   Make sure ngrok is installed. See SETUP.md for instructions.")

start_ngrok()

def sync_recent_plays_background():
    """Background job to sync recent plays - runs every 2 minutes"""
    try:
        token_data = load_token_from_file()
        if not token_data:
            return
        
        # Check if token expired and refresh if needed
        if datetime.now().timestamp() > token_data['expires_at']:
            access_token = refresh_token_in_background()
            if not access_token:
                print("Failed to refresh token in background")
                return
        else:
            access_token = token_data['access_token']
        
        # Get the last sync timestamp to avoid reprocessing old plays
        last_sync = get_last_sync_timestamp()
        
        headers = {'Authorization': f"Bearer {access_token}"}
        response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
        
        if response.status_code == 200:
            recent_data = response.json()
            items = recent_data.get('items', [])
            
            # Process items in reverse order (oldest first) to track timestamp correctly
            new_plays = []
            latest_timestamp = last_sync
            
            for item in reversed(items):
                played_at = item['played_at']
                
                # Only process plays newer than our last sync
                if last_sync is None or played_at > last_sync:
                    new_plays.append(item)
                    # Track the latest timestamp
                    if latest_timestamp is None or played_at > latest_timestamp:
                        latest_timestamp = played_at
            
            # Process new plays
            if new_plays:
                for item in new_plays:
                    track = item['track']
                    played_at = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
                    process_and_store_track(track, played_at, access_token)
                
                # Save the latest timestamp
                save_last_sync_timestamp(latest_timestamp)
                print(f"✓ Background sync: Processed {len(new_plays)} new track(s)")
            else:
                print("✓ Background sync: No new plays to process")
    except Exception as e:
        print(f"Background sync error: {e}")

# Schedule background sync every 2 minutes
scheduler.add_job(func=sync_recent_plays_background, trigger="interval", minutes=2, id='sync_job')

def process_and_store_track(track, played_at, access_token):
    """Process a track and store it in the database with all related data"""
    try:
        # Prepare song data
        song_data = {
            'id': track['id'],
            'title': track['name'],
            'length_ms': track['duration_ms']
        }
        
        # Insert/update song
        insert_or_update_song(song_data)
        
        # Get album info
        album_id = track['album']['id']
        album_title = track['album']['name']
        
        # Process each artist and create Creates relationship
        for artist in track['artists']:
            artist_id = artist['id']
            artist_name = artist['name']
            
            # Insert/update artist
            insert_or_update_artist(artist_id, artist_name, track['duration_ms'])
            
            # Link artist, song, and album in Creates table
            link_song_artist_album(track['id'], artist_id, album_id)
        
        # Link album and song in Album_Song table
        link_album_song(album_id, track['id'])
        
        # Get full album details for accurate data
        headers = {'Authorization': f"Bearer {access_token}"}
        album_response = requests.get(f"{API_BASE_URL}/albums/{album_id}", headers=headers)
        
        if album_response.status_code == 200:
            album_full = album_response.json()
            total_tracks = album_full.get('total_tracks', 0)
            album_length_ms = sum(t['duration_ms'] for t in album_full.get('tracks', {}).get('items', []))
            
            insert_or_update_album(
                album_id,
                album_title,
                total_tracks,
                album_length_ms,
                track['duration_ms']
            )
    except Exception as e:
        print(f"Error processing track: {e}")

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
    if os.getenv('DEBUG_AUTH_URL', '0') == '1':
        return auth_url

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        error_msg = request.args.get('error', 'Unknown error')
        error_desc = request.args.get('error_description', 'No description')
        return jsonify({'error': error_msg, 'description': error_desc})
    
    code = request.args.get('code')
    req_body = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    response = requests.post(TOKEN_URL, data=req_body)
    token_info = response.json()
    
    # Check if we got an error from Spotify
    if 'error' in token_info:
        return f"<h1>Spotify Error</h1><p>{token_info.get('error')}: {token_info.get('error_description', 'No description')}</p>"
    
    # Ensure we have required fields
    if 'access_token' not in token_info:
        return f"<h1>Token Error</h1><p>Did not receive access token. Response: {token_info}</p>"
    
    expires_at = datetime.now().timestamp() + token_info.get('expires_in', 3600)
    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info.get('refresh_token', '')
    session['expires_at'] = expires_at
    
    # Save token to file for background job
    save_token_to_file(token_info['access_token'], token_info.get('refresh_token', ''), expires_at)
    
    return redirect('/menu')

@app.route('/menu')
def menu():
    if 'error' in request.args:
        error_msg = request.args.get('error', 'Unknown error')
        error_desc = request.args.get('error_description', 'No description')
        return jsonify({'error': error_msg, 'description': error_desc})

    html = """
    <h1>Spotify Stats Menu</h1>
    <ul>
        <li><a href='/database_values'>Database Values</a></li>
    </ul>
    <a href='/'>Back to home</a>
    """
    
    return html

@app.route('/database_values')
def database_values():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    # Sync recent songs from Spotify API (only new plays)
    try:
        last_sync = get_last_sync_timestamp()
        recent_response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
        
        if recent_response.status_code == 200:
            recent_data = recent_response.json()
            items = recent_data.get('items', [])
            
            # Process items in reverse order (oldest first)
            new_plays = []
            latest_timestamp = last_sync
            
            for item in reversed(items):
                played_at = item['played_at']
                
                # Only process plays newer than our last sync
                if last_sync is None or played_at > last_sync:
                    new_plays.append(item)
                    if latest_timestamp is None or played_at > latest_timestamp:
                        latest_timestamp = played_at
            
            # Process new plays
            if new_plays:
                for item in new_plays:
                    track = item['track']
                    played_at_dt = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
                    process_and_store_track(track, played_at_dt, session['access_token'])
                
                save_last_sync_timestamp(latest_timestamp)
                print(f"✓ Page load sync: Processed {len(new_plays)} new track(s)")
            else:
                print("✓ Page load sync: No new plays to process")
    except Exception as e:
        print(f"Error syncing recent plays: {e}")
    
    # Get user profile for display
    try:
        profile_response = requests.get(API_BASE_URL + '/me', headers=headers)
        profile_response.raise_for_status()
        user_profile = profile_response.json()
        user_id = user_profile.get('id', 'N/A')
        user_username = user_profile.get('display_name', 'N/A')
    except requests.exceptions.RequestException as e:
        extra_note = ""
        if profile_response is not None and profile_response.status_code == 403:
            extra_note = "<p><strong>Tip:</strong> Make sure this Spotify account is added as a user/tester in developer.spotify.com &gt; Dashboard &gt; Users and Access for this app.</p>"
        return f"""
        <h1>Error Fetching User Profile</h1>
        <p>Status Code: {profile_response.status_code}</p>
        <p>Response: {profile_response.text}</p>
        <p>Error: {str(e)}</p>
        {extra_note}
        <p><a href='/login'>Try logging in again</a></p>
        """
    except ValueError as e:
        return f"""
        <h1>Error Parsing User Profile Response</h1>
        <p>The API response was not valid JSON.</p>
        <p>Response: {profile_response.text}</p>
        <p>Error: {str(e)}</p>
        <p><a href='/login'>Try logging in again</a></p>
        """
    
    # Get playlists for display
    all_playlists = []
    try:
        playlists_response = requests.get(API_BASE_URL + '/me/playlists?limit=50', headers=headers)
        playlists_response.raise_for_status()
        playlists = playlists_response.json()
        if 'items' in playlists:
            for playlist in playlists['items']:
                all_playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name']
                })
    except Exception as e:
        print(f"Error fetching playlists: {e}")
    
    # Retrieve data from MySQL database
    db_songs = get_all_songs()
    db_artists = get_all_artists()
    db_albums = get_all_albums()
    
    # Format song data for display
    song_list = []
    for song in db_songs:
        song_list.append({
            'id': song['id'],
            'title': song['title'],
            'artists': song['artists'],
            'album_title': song['album_title'],
            'length_formatted': f"{song['length_ms'] // 60000}:{(song['length_ms'] % 60000) // 1000:02d}",
            'listen_count': song['listen_count'],
            'listen_time_formatted': f"{song['listen_time_ms'] // 60000}:{(song['listen_time_ms'] % 60000) // 1000:02d}"
        })
    
    # Format artist data for display
    artist_list = []
    for artist in db_artists:
        artist_list.append({
            'id': artist['id'],
            'name': artist['name'],
            'listens': artist['listens'],
            'listen_time_formatted': f"{artist['listen_time_ms'] // 60000}:{(artist['listen_time_ms'] % 60000) // 1000:02d}"
        })
    
    # Format album data for display
    album_list = []
    for album in db_albums:
        album_list.append({
            'id': album['id'],
            'title': album['title'],
            'listen_time_formatted': f"{album['listen_time_ms'] // 60000}:{(album['listen_time_ms'] % 60000) // 1000:02d}",
            'listens': album['listens'],
            'length_formatted': f"{album['length_ms'] // 60000}:{(album['length_ms'] % 60000) // 1000:02d}"
        })
    
    # Delete old database_values txt files
    old_files = glob.glob('database_values_*.txt')
    for old_file in old_files:
        try:
            os.remove(old_file)
        except:
            pass
    
    # Save to txt file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'database_values_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("SPOTIFY STATS - DATABASE VALUES (FROM MYSQL DATABASE)\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("SONG STATISTICS\n")
        f.write("-" * 80 + "\n\n")
        
        for song in song_list:
            f.write(f"Song ID: {song['id']}\n")
            f.write(f"Title: {song['title']}\n")
            f.write(f"Artist(s): {song['artists']}\n")
            f.write(f"Album: {song['album_title']}\n")
            f.write(f"Length: {song['length_formatted']}\n")
            f.write(f"Listen Count: {song['listen_count']}\n")
            f.write(f"Total Listen Time: {song['listen_time_formatted']}\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n\nARTIST STATISTICS\n")
        f.write("-" * 80 + "\n\n")
        
        for artist in artist_list:
            f.write(f"Artist ID: {artist['id']}\n")
            f.write(f"Artist Name: {artist['name']}\n")
            f.write(f"Total Listens: {artist['listens']}\n")
            f.write(f"Total Listen Time: {artist['listen_time_formatted']}\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n\nALBUM STATISTICS\n")
        f.write("-" * 80 + "\n\n")
        
        for album in album_list:
            f.write(f"Album ID: {album['id']}\n")
            f.write(f"Album Title: {album['title']}\n")
            f.write(f"Album Listen Time: {album['listen_time_formatted']}\n")
            f.write(f"Album Listens: {album['listens']}\n")
            f.write(f"Album Length: {album['length_formatted']}\n")
            f.write("-" * 80 + "\n")
    
    # Build HTML response
    html = f"""
    <h1>Database Values - Song, Artist & Album Statistics</h1>
    <p><em>Data saved to: {filename}</em></p>
    <p><em>Data retrieved from MySQL database (auto-syncs every 2 minutes in background)</em></p>
    
    <h2>User Information</h2>
    <p><strong>Username:</strong> {user_username}</p>
    <p><strong>User ID:</strong> {user_id}</p>
    
    <h2>Song Statistics</h2>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th style="padding: 10px;">Song ID</th>
            <th style="padding: 10px;">Title</th>
            <th style="padding: 10px;">Artist(s)</th>
            <th style="padding: 10px;">Album</th>
            <th style="padding: 10px;">Length</th>
            <th style="padding: 10px;">Listen Count</th>
            <th style="padding: 10px;">Total Listen Time</th>
        </tr>
    """
    
    for song in song_list:
        html += f"""
        <tr>
            <td style="padding: 10px;">{song['id']}</td>
            <td style="padding: 10px;">{song['title']}</td>
            <td style="padding: 10px;">{song['artists']}</td>
            <td style="padding: 10px;">{song['album_title']}</td>
            <td style="padding: 10px;">{song['length_formatted']}</td>
            <td style="padding: 10px;">{song['listen_count']}</td>
            <td style="padding: 10px;">{song['listen_time_formatted']}</td>
        </tr>
        """
    
    html += """
    </table>
    
    <h2>Artist Statistics</h2>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th style="padding: 10px;">Artist ID</th>
            <th style="padding: 10px;">Artist Name</th>
            <th style="padding: 10px;">Total Listens</th>
            <th style="padding: 10px;">Total Listen Time</th>
        </tr>
    """
    
    for artist in artist_list:
        html += f"""
        <tr>
            <td style="padding: 10px;">{artist['id']}</td>
            <td style="padding: 10px;">{artist['name']}</td>
            <td style="padding: 10px;">{artist['listens']}</td>
            <td style="padding: 10px;">{artist['listen_time_formatted']}</td>
        </tr>
        """
    
    html += """
    </table>
    
    <h2>Album Statistics</h2>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th style="padding: 10px;">Album ID</th>
            <th style="padding: 10px;">Album Title</th>
            <th style="padding: 10px;">Total Listen Time</th>
            <th style="padding: 10px;">Album Listens</th>
            <th style="padding: 10px;">Album Length</th>
        </tr>
    """
    
    for album in album_list:
        html += f"""
        <tr>
            <td style="padding: 10px;">{album['id']}</td>
            <td style="padding: 10px;">{album['title']}</td>
            <td style="padding: 10px;">{album['listen_time_formatted']}</td>
            <td style="padding: 10px;">{album['listens']}</td>
            <td style="padding: 10px;">{album['length_formatted']}</td>
        </tr>
        """
    
    html += """
    </table>
    
    <h2>Your Playlists</h2>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th style="padding: 10px;">Playlist ID</th>
            <th style="padding: 10px;">Playlist Name</th>
        </tr>
    """
    
    for playlist in all_playlists:
        html += f"""
        <tr>
            <td style="padding: 10px;">{playlist['id']}</td>
            <td style="padding: 10px;">{playlist['name']}</td>
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
    
    expires_at = datetime.now().timestamp() + new_token_info['expires_in']
    session['access_token'] = new_token_info['access_token']
    # Spotify doesn't always return a new refresh_token, keep the old one if not provided
    session['refresh_token'] = new_token_info.get('refresh_token', session['refresh_token'])
    session['expires_at'] = expires_at
    
    # Save token to file for background job
    save_token_to_file(new_token_info['access_token'], session['refresh_token'], expires_at)
    
    return redirect('/menu')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)