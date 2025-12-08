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

from flask import Flask, redirect, request, session, jsonify, url_for
from datetime import datetime, timedelta
from database import (
    init_database, insert_or_update_song, insert_or_update_artist,
    insert_or_update_album, link_song_artist_album, link_album_song,
    get_all_songs, get_all_artists, get_all_albums,
    get_or_create_user, get_user_playlists, insert_or_update_playlist,
    link_playlist_song, get_last_sync_timestamp, save_last_sync_timestamp,
    get_blacklist, add_to_blacklist, remove_from_blacklist
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

# Initialize database
init_database()

# Create background scheduler
scheduler = BackgroundScheduler()
scheduler.start()
#Save access token info to file 
def save_token_to_file(access_token, refresh_token, expires_at):
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at
            }, f)
    except Exception as e:
        print(f"Error saving token: {e}")
#Load access token info from file
def load_token_from_file():
    
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading token: {e}")
    return None
#Refresh the access token using the refresh token
def refresh_token_in_background():
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
        print("ngrok tunnel started successfully")
        print(f"   App available at: https://{NGROK_DOMAIN}")
        print(f"\n   IMPORTANT: You must configure ngrok authtoken on your machine:")
        print(f"   ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz")
        print(f"\n   See SETUP.md for full instructions.\n")
    except Exception as e:
        print(f"Warning: Could not start ngrok: {e}")
        print(f"   Make sure ngrok is installed. See SETUP.md for instructions.")

start_ngrok()
#Background job to sync recent plays
def sync_recent_plays_background():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Background sync job started...")
    try:
        token_data = load_token_from_file()
        if not token_data:
            print("!!! No token file found - please log in through the web interface first")
            return
        
        # Check if token expired and refresh if needed
        if datetime.now().timestamp() > token_data['expires_at']:
            access_token = refresh_token_in_background()
            if not access_token:
                print("Failed to refresh token in background")
                return
        else:
            access_token = token_data['access_token']
        

        last_sync = get_last_sync_timestamp()
        
        headers = {'Authorization': f"Bearer {access_token}"}
        

        response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=50', headers=headers)
        
        if response.status_code == 200:
            recent_data = response.json()
            items = recent_data.get('items', [])
            

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
                    played_at = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
                    
                    context = item.get('context')
                    
                    process_and_store_track(track, played_at, access_token, context)
                
                
                save_last_sync_timestamp(latest_timestamp)
                print(f"✓ Background sync: Processed {len(new_plays)} new track(s)")
            else:
                print("✓ Background sync: No new plays to process")
    except Exception as e:
        print(f"Background sync error: {e}")

scheduler.add_job(func=sync_recent_plays_background, trigger="interval", minutes=2, id='sync_job')

#Process a track and store it in the database with all related data
def process_and_store_track(track, played_at, access_token, context=None):
    
    try:
        is_blacklisted = False
        
        if context and context.get('type') == 'playlist':
            playlist_uri = context.get('uri', '')
            playlist_id = playlist_uri.split(':')[-1] if playlist_uri else None
            
            if playlist_id:
                blacklist = get_blacklist()
                is_blacklisted = any(p['id'] == playlist_id for p in blacklist)
        
        print(f"\n[Processing] {track['name']} by {', '.join([a['name'] for a in track['artists']])} - Blacklisted: {is_blacklisted}")
        
        # Prepare song data
        song_data = {
            'id': track['id'],
            'title': track['name'],
            'length_ms': track['duration_ms'],
            'played_at': played_at,
            'image_url': track['album']['images'][0]['url'] if track['album'].get('images') else None,
            'is_blacklisted': is_blacklisted
        }
        
        # Insert/update song
        if not insert_or_update_song(song_data):
            print(f"⚠ Failed to insert song: {track['name']}")
            return
        print(f"  ✓ Song inserted/updated")
        
        album_id = track['album']['id']
        album_title = track['album']['name']
        
        headers = {'Authorization': f"Bearer {access_token}"}
        album_response = requests.get(f"{API_BASE_URL}/albums/{album_id}", headers=headers)
        
        if album_response.status_code == 200:
            album_full = album_response.json()
            total_tracks = album_full.get('total_tracks', 0)
            album_length_ms = sum(t['duration_ms'] for t in album_full.get('tracks', {}).get('items', []))
            album_image_url = album_full['images'][0]['url'] if album_full.get('images') else None
            
            if not insert_or_update_album(
                album_id,
                album_title,
                total_tracks,
                album_length_ms,
                track['duration_ms'],
                album_image_url,
                is_blacklisted
            ):
                print(f"  ⚠ Failed to insert album: {album_title}")
                return
            else:
                print(f"  ✓ Album inserted/updated: {album_title}")
        else:
            print(f"  ⚠ Failed to fetch album details for {album_title}: {album_response.status_code}")
            return
        
        # process artists and create relationships (album exists now yippee!)
        for artist in track['artists']:
            artist_id = artist['id']
            artist_name = artist['name']
            
            # Fetch artist details to get image
            artist_image_url = None
            artist_response = requests.get(f"{API_BASE_URL}/artists/{artist_id}", headers=headers)
            if artist_response.status_code == 200:
                artist_full = artist_response.json()
                artist_image_url = artist_full['images'][0]['url'] if artist_full.get('images') else None
            
            # Insert/update artist
            if not insert_or_update_artist(artist_id, artist_name, track['duration_ms'], artist_image_url, is_blacklisted):
                print(f"  ⚠ Failed to insert artist: {artist_name}")
            else:
                print(f"  ✓ Artist inserted/updated: {artist_name}")
            
            # Link artist, song, and album in Creates table
            if not link_song_artist_album(track['id'], artist_id, album_id):
                print(f"  ⚠ Failed to link song-artist-album for: {track['name']}")
            else:
                print(f"  ✓ Linked artist-song-album")
        
        # Link album and song in Album_Song table
        if not link_album_song(album_id, track['id']):
            print(f"  ⚠ Failed to link album-song for: {track['name']}")
        else:
            print(f"  ✓ Linked album-song")
    except Exception as e:
        print(f"❌ Error processing track '{track.get('name', 'Unknown')}': {e}")

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1'

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kungungalacorgus.stats</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: #121212;
                color: #FFFFFF;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                flex-direction: column;
            }
            h1 {
                font-size: 48px;
                font-weight: bold;
                margin-bottom: 10px;
                text-align: center;
                color: #1DB954;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            }
            .subtitle {
                font-size: 18px;
                color: #FFFFFF;
                margin-bottom: 30px;
                text-align: center;
                opacity: 1;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            }
            .login-button {
                padding: 15px 40px;
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 30px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: background-color 0.3s, transform 0.1s;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            }
            .login-button:hover {
                background-color: #1ed760;
                transform: scale(1.05);
            }
            .login-button:active {
                transform: scale(0.98);
            }
        </style>
    </head>
    <body>
        <h1>Welcome to Kungungalacorgus.stats!</h1>
        <p class="subtitle">Login to see your stats</p>
        <a href="/login" class="login-button">Login to Spotify</a>
    </body>
    </html>
    """

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
    
    if 'error' in token_info:
        return f"<h1>Spotify Error</h1><p>{token_info.get('error')}: {token_info.get('error_description', 'No description')}</p>"
    
    if 'access_token' not in token_info:
        return f"<h1>Token Error</h1><p>Did not receive access token. Response: {token_info}</p>"
    
    expires_at = datetime.now().timestamp() + token_info.get('expires_in', 3600)
    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info.get('refresh_token', '')
    session['expires_at'] = expires_at
    
    save_token_to_file(token_info['access_token'], token_info.get('refresh_token', ''), expires_at)
    
    return redirect('/database_values')

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

@app.route('/sync_recent')
def sync_recent():
    """Sync recent songs from Spotify with variable limit"""
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    # Get limit from query parameter, default to 10
    try:
        limit = int(request.args.get('limit', 10))
        # spotify api limit = 50 dont exceed
        limit = min(max(1, limit), 50)
    except ValueError:
        limit = 10
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    try:
        last_sync = get_last_sync_timestamp()
        recent_response = requests.get(API_BASE_URL + f'/me/player/recently-played?limit={limit}', headers=headers)
        
        if recent_response.status_code == 200:
            recent_data = recent_response.json()
            items = recent_data.get('items', [])
            
            # Process items in reverse order (oldest first)
            processed_count = 0
            latest_timestamp = last_sync
            
            for item in reversed(items):
                track = item['track']
                played_at = item['played_at']
                played_at_dt = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
                
                context = item.get('context')
                
                process_and_store_track(track, played_at_dt, session['access_token'], context)
                processed_count += 1
                
                if latest_timestamp is None or played_at > latest_timestamp:
                    latest_timestamp = played_at
            
            # Save the latest timestamp if we processed any tracks
            if processed_count > 0 and latest_timestamp is not None:
                save_last_sync_timestamp(latest_timestamp)
                print(f"✓ Manual sync: Processed {processed_count} track(s)")
            else:
                print("✓ Manual sync: No plays to process")
    except Exception as e:
        print(f"Error syncing recent plays: {e}")
    
    return redirect('/database_values')

@app.route('/add_to_blacklist', methods=['POST'])
def add_to_blacklist_route():
    """Add a playlist to the blacklist"""
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    playlist_url = request.form.get('playlist_url', '').strip()
    if not playlist_url:
        return jsonify({'success': False, 'error': 'No playlist URL provided'})
    
    # Extract playlist ID from URL 
    playlist_id = None
    if 'playlist/' in playlist_url:
        playlist_id = playlist_url.split('playlist/')[-1].split('?')[0]
    elif len(playlist_url) == 22: 
        playlist_id = playlist_url
    
    if playlist_id:
        # Fetch playlist details from Spotify
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        try:
            response = requests.get(API_BASE_URL + f'/playlists/{playlist_id}', headers=headers)
            if response.status_code == 200:
                playlist_data = response.json()
                playlist_name = playlist_data.get('name', 'Unknown Playlist')
                
                # Get playlist image URL
                image_url = None
                if playlist_data.get('images') and len(playlist_data['images']) > 0:
                    image_url = playlist_data['images'][0]['url']
                
                add_to_blacklist(playlist_id, playlist_name, image_url)
                
                return jsonify({
                    'success': True,
                    'playlist': {
                        'id': playlist_id,
                        'name': playlist_name,
                        'image_url': image_url
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Could not fetch playlist from Spotify'})
        except Exception as e:
            print(f"Error adding playlist to blacklist: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid playlist URL'})

@app.route('/remove_from_blacklist/<playlist_id>')
def remove_from_blacklist_route(playlist_id):
    """Remove a playlist from the blacklist"""
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        remove_from_blacklist(playlist_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear_database')
def clear_database_route():
    """Clear all data from the database"""
    if 'access_token' not in session:
        return redirect('/login')
    
    try:
        # Import and run the clear_database module
        import clear_database
        import importlib
        importlib.reload(clear_database)  # Reload to get fresh execution
        
        return """
        <html>
        <head>
            <title>Database Cleared</title>
            <style>
                body {{
                    background-color: #121212;
                    color: #FFFFFF;
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    flex-direction: column;
                }}
                h1 {{ color: #1DB954; }}
                a {{
                    color: #1DB954;
                    text-decoration: none;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: 2px solid #1DB954;
                    border-radius: 5px;
                    margin-top: 20px;
                    display: inline-block;
                }}
                a:hover {{
                    background-color: #1DB954;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <h1>✓ Database Cleared Successfully</h1>
            <p>All songs, artists, and albums have been deleted.</p>
            <a href='/database_values'>Return to Dashboard</a>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <h1>Error Clearing Database</h1>
        <p>{str(e)}</p>
        <p><a href='/database_values'>Go Back</a></p>
        """

@app.route('/database_values')
def database_values():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    # Get user profile for display
    try:
        profile_response = requests.get(API_BASE_URL + '/me', headers=headers)
        profile_response.raise_for_status()
        user_profile = profile_response.json()
        user_id = user_profile.get('id', 'N/A')
        user_username = user_profile.get('display_name', 'N/A')
        user_image = user_profile.get('images', [{}])[0].get('url') if user_profile.get('images') else None
        user_image = user_profile.get('images', [{}])[0].get('url') if user_profile.get('images') else None
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
                # Get the first (usually highest resolution) image if available
                image_url = None
                if playlist.get('images') and len(playlist['images']) > 0:
                    image_url = playlist['images'][0]['url']
                
                all_playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'image_url': image_url
                })
    except Exception as e:
        print(f"Error fetching playlists: {e}")
    
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
            'length_ms': song['length_ms'],
            'length_formatted': f"{song['length_ms'] // 60000}:{(song['length_ms'] % 60000) // 1000:02d}",
            'listen_count': song['listen_count'],
            'listen_time_ms': song['listen_time_ms'],
            'listen_time_formatted': f"{song['listen_time_ms'] // 60000}:{(song['listen_time_ms'] % 60000) // 1000:02d}",
            'blacklisted_listens': song.get('blacklisted_listens', 0),
            'blacklisted_time_ms': song.get('blacklisted_time_ms', 0),
            'blacklisted_time_formatted': f"{song.get('blacklisted_time_ms', 0) // 60000}:{(song.get('blacklisted_time_ms', 0) % 60000) // 1000:02d}",
            'image_url': song.get('image_url')
        })
    
    # Format artist data for display
    artist_list = []
    for artist in db_artists:
        artist_list.append({
            'id': artist['id'],
            'name': artist['name'],
            'listens': artist['listens'],
            'listen_time_ms': artist['listen_time_ms'],
            'listen_time_formatted': f"{artist['listen_time_ms'] // 60000}:{(artist['listen_time_ms'] % 60000) // 1000:02d}",
            'blacklisted_listens': artist.get('blacklisted_listens', 0),
            'blacklisted_time_ms': artist.get('blacklisted_time_ms', 0),
            'blacklisted_time_formatted': f"{artist.get('blacklisted_time_ms', 0) // 60000}:{(artist.get('blacklisted_time_ms', 0) % 60000) // 1000:02d}",
            'image_url': artist.get('image_url')
        })
    
    # Format album data for display
    album_list = []
    for album in db_albums:
        album_list.append({
            'id': album['id'],
            'title': album['title'],
            'listen_time_ms': album['listen_time_ms'],
            'listen_time_formatted': f"{album['listen_time_ms'] // 60000}:{(album['listen_time_ms'] % 60000) // 1000:02d}",
            'listens': album['listens'],
            'length_ms': album['length_ms'],
            'length_formatted': f"{album['length_ms'] // 60000}:{(album['length_ms'] % 60000) // 1000:02d}",
            'blacklisted_listens': album.get('blacklisted_listens', 0),
            'blacklisted_time_ms': album.get('blacklisted_time_ms', 0),
            'blacklisted_time_formatted': f"{album.get('blacklisted_time_ms', 0) // 60000}:{(album.get('blacklisted_time_ms', 0) % 60000) // 1000:02d}",
            'image_url': album.get('image_url')
        })
    
    # Calculate totals for songs
    total_song_listens = sum(song['listen_count'] for song in song_list)
    total_song_time_ms = sum(song['listen_time_ms'] for song in song_list)
    total_song_time_formatted = f"{total_song_time_ms // 60000}:{(total_song_time_ms % 60000) // 1000:02d}"
    total_song_blacklisted_listens = sum(song['blacklisted_listens'] for song in song_list)
    total_song_blacklisted_time_ms = sum(song['blacklisted_time_ms'] for song in song_list)
    total_song_blacklisted_time_formatted = f"{total_song_blacklisted_time_ms // 60000}:{(total_song_blacklisted_time_ms % 60000) // 1000:02d}"
    
    # Calculate totals for artists
    total_artist_listens = sum(artist['listens'] for artist in artist_list)
    total_artist_time_ms = sum(artist['listen_time_ms'] for artist in artist_list)
    total_artist_time_formatted = f"{total_artist_time_ms // 60000}:{(total_artist_time_ms % 60000) // 1000:02d}"
    total_artist_blacklisted_listens = sum(artist['blacklisted_listens'] for artist in artist_list)
    total_artist_blacklisted_time_ms = sum(artist['blacklisted_time_ms'] for artist in artist_list)
    total_artist_blacklisted_time_formatted = f"{total_artist_blacklisted_time_ms // 60000}:{(total_artist_blacklisted_time_ms % 60000) // 1000:02d}"
    
    # Calculate totals for albums
    total_album_listens = sum(album['listens'] for album in album_list)
    total_album_time_ms = sum(album['listen_time_ms'] for album in album_list)
    total_album_time_formatted = f"{total_album_time_ms // 60000}:{(total_album_time_ms % 60000) // 1000:02d}"
    total_album_blacklisted_listens = sum(album['blacklisted_listens'] for album in album_list)
    total_album_blacklisted_time_ms = sum(album['blacklisted_time_ms'] for album in album_list)
    total_album_blacklisted_time_formatted = f"{total_album_blacklisted_time_ms // 60000}:{(total_album_blacklisted_time_ms % 60000) // 1000:02d}"
    
   
    blacklist = get_blacklist()
    
    # Build HTML response with tabs
    html = f"""
    <style>
        body {{
            background-color: #121212;
            color: #FFFFFF;
            font-family: Arial, sans-serif;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light-mode {{
            background-color: #FFFFFF;
            color: #000000;
        }}
        h1, h2, h3 {{
            color: #1DB954;
        }}
        .tab {{
            overflow: hidden;
            border-bottom: 2px solid #1DB954;
            background-color: #1e1e1e;
            transition: background-color 0.3s;
        }}
        body.light-mode .tab {{
            background-color: #f1f1f1;
        }}
        .tab button {{
            background-color: inherit;
            color: #FFFFFF;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 20px;
            transition: 0.3s;
            font-size: 16px;
            font-weight: bold;
        }}
        body.light-mode .tab button {{
            color: #000000;
        }}
        .tab button:hover {{
            background-color: #2a2a2a;
        }}
        body.light-mode .tab button:hover {{
            background-color: #ddd;
        }}
        .tab button.active {{
            background-color: #1DB954;
            color: white;
        }}
        .tabcontent {{
            display: none;
            padding: 20px;
            animation: fadeEffect 0.5s;
            background-color: #181818;
            transition: background-color 0.3s;
        }}
        body.light-mode .tabcontent {{
            background-color: #FFFFFF;
        }}
        @keyframes fadeEffect {{
            from {{opacity: 0;}}
            to {{opacity: 1;}}
        }}
        table {{
            background-color: #1e1e1e;
            color: #FFFFFF;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light-mode table {{
            background-color: #FFFFFF;
            color: #000000;
        }}
        th {{
            background-color: #1DB954;
            color: white;
        }}
        tr:hover {{
            background-color: #2a2a2a;
        }}
        body.light-mode tr:hover {{
            background-color: #f0f0f0;
        }}
        input[type="number"], input[type="text"] {{
            background-color: #2a2a2a;
            color: #FFFFFF;
            border: 1px solid #1DB954;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light-mode input[type="number"], body.light-mode input[type="text"] {{
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #ccc;
        }}
        select {{
            background-color: #2a2a2a;
            color: #FFFFFF;
            border: 1px solid #1DB954;
            padding: 8px;
            border-radius: 4px;
            font-size: 14px;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light-mode select {{
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #ccc;
        }}
        a {{
            color: #1DB954;
        }}
        a:hover {{
            color: #1ed760;
        }}
        .sort-control {{
            margin: 15px 0;
            padding: 10px;
            background-color: #1e1e1e;
            border-radius: 5px;
            display: inline-block;
            transition: background-color 0.3s;
        }}
        body.light-mode .sort-control {{
            background-color: #f5f5f5;
        }}
        .theme-switch-wrapper {{
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            align-items: center;
            z-index: 1000;
        }}
        .theme-switch {{
            display: inline-block;
            height: 34px;
            position: relative;
            width: 60px;
        }}
        .theme-switch input {{
            display: none;
        }}
        .slider {{
            background-color: #ccc;
            bottom: 0;
            cursor: pointer;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
            transition: 0.4s;
            border-radius: 34px;
        }}
        .slider:before {{
            background-color: #fff;
            bottom: 4px;
            content: "";
            height: 26px;
            left: 4px;
            position: absolute;
            transition: 0.4s;
            width: 26px;
            border-radius: 50%;
        }}
        input:checked + .slider {{
            background-color: #1DB954;
        }}
        input:checked + .slider:before {{
            transform: translateX(26px);
        }}
        .theme-label {{
            margin-left: 10px;
            font-weight: bold;
        }}
        .time-format-wrapper {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background-color: #1e1e1e;
            border-radius: 5px;
            font-size: 14px;
            transition: background-color 0.3s;
        }}
        body.light-mode .time-format-wrapper {{
            background-color: #f5f5f5;
        }}
        .time-format-switch {{
            display: inline-block;
            height: 34px;
            position: relative;
            width: 60px;
            margin: 0 10px;
        }}
        .time-format-switch input {{
            display: none;
        }}
        .time-format-label {{
            font-weight: bold;
        }}
        .blacklist-container {{
            transition: background-color 0.3s;
        }}
        body.light-mode .blacklist-container {{
            background-color: #f9f9f9 !important;
        }}
        body.light-mode .blacklist-container .blacklist-list {{
            background-color: #FFFFFF !important;
        }}
        .top-item-card {{
            display: flex;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background-color: #1e1e1e;
            border-radius: 8px;
            transition: all 0.3s;
            border: 1px solid #2a2a2a;
        }}
        body.light-mode .top-item-card {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
        }}
        .top-item-card:hover {{
            background-color: #2a2a2a;
            transform: translateX(5px);
        }}
        body.light-mode .top-item-card:hover {{
            background-color: #e8e8e8;
        }}
        .rank-number {{
            font-size: 32px;
            font-weight: bold;
            color: #1DB954;
            min-width: 60px;
            text-align: center;
        }}
        .item-image {{
            width: 80px;
            height: 80px;
            border-radius: 8px;
            margin: 0 20px;
            object-fit: cover;
        }}
        .item-info {{
            flex-grow: 1;
        }}
        .item-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .item-subtitle {{
            color: #b3b3b3;
            font-size: 14px;
        }}
        body.light-mode .item-subtitle {{
            color: #666;
        }}
        .item-stats {{
            display: flex;
            gap: 30px;
            margin-right: 20px;
            flex-shrink: 0;
        }}
        .stat-box {{
            text-align: center;
            min-width: 80px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #1DB954;
        }}
        .stat-label {{
            font-size: 12px;
            color: #b3b3b3;
        }}
        body.light-mode .stat-label {{
            color: #666;
        }}
        .user-profile {{
            position: absolute;
            top: 20px;
            left: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .user-profile img {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid #1DB954;
        }}
        .user-profile span {{
            font-size: 18px;
            font-weight: bold;
            color: #1DB954;
        }}
        h1.main-title {{
            text-align: center;
            font-weight: bold;
            margin-top: 80px;
            font-size: 36px;
        }}
    </style>
    <script>
        // Auto-refresh page every 2 minutes
        setTimeout(function() {{
            location.reload();
        }}, 120000);
        
        // Theme toggle function
        function toggleTheme() {{
            document.body.classList.toggle('light-mode');
            var isLightMode = document.body.classList.contains('light-mode');
            localStorage.setItem('theme', isLightMode ? 'light' : 'dark');
            document.querySelector('.theme-label').textContent = isLightMode ? '☀️' : '🌙';
        }}
        
        // Load saved theme preference
        function loadTheme() {{
            var savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {{
                document.body.classList.add('light-mode');
                document.getElementById('theme-toggle').checked = true;
                document.querySelector('.theme-label').textContent = '☀️';
            }} else {{
                document.querySelector('.theme-label').textContent = '🌙';
            }}
        }}
        
        // Time format toggle function
        function toggleTimeFormat(sourceId) {{
            // If sourceId not provided, default to first toggle
            if (!sourceId) sourceId = 'time-format-toggle';
            
            var isExtended = document.getElementById(sourceId).checked;
            localStorage.setItem('timeFormat', isExtended ? 'extended' : 'compact');
            
            // Sync all toggle switches
            var toggles = ['time-format-toggle', 'time-format-toggle-artists', 'time-format-toggle-albums', 'time-format-toggle-stats'];
            toggles.forEach(function(id) {{
                var el = document.getElementById(id);
                if (el) el.checked = isExtended;
            }});
            
            updateTimeDisplays(isExtended);
        }}
        
        // Load saved time format preference
        function loadTimeFormat() {{
            var savedFormat = localStorage.getItem('timeFormat');
            var isExtended = savedFormat === 'extended';
            
            // Set all toggle switches
            var toggles = ['time-format-toggle', 'time-format-toggle-artists', 'time-format-toggle-albums', 'time-format-toggle-stats'];
            toggles.forEach(function(id) {{
                var el = document.getElementById(id);
                if (el) el.checked = isExtended;
            }});
            
            updateTimeDisplays(isExtended);
        }}
        
        // Toggle blacklisted columns visibility
        function toggleBlacklistedColumns() {{
            var showBlacklisted = document.getElementById('blacklist-toggle').checked;
            localStorage.setItem('showBlacklisted', showBlacklisted ? 'true' : 'false');
            
            var blacklistedColumns = document.querySelectorAll('.blacklisted-column');
            blacklistedColumns.forEach(function(column) {{
                column.style.display = showBlacklisted ? '' : 'none';
            }});
        }}
        
        // Toggle blacklisted stats in Top tabs
        function toggleBlacklistedStats() {{
            // Get the toggle that was clicked (event.target) or default to songs toggle
            var clickedToggle = event && event.target ? event.target : document.getElementById('blacklist-toggle-songs');
            
            // Get all toggles
            var songsToggle = document.getElementById('blacklist-toggle-songs');
            var artistsToggle = document.getElementById('blacklist-toggle-artists');
            var albumsToggle = document.getElementById('blacklist-toggle-albums');
            
            // Use the clicked toggle's state
            var showBlacklisted = clickedToggle ? clickedToggle.checked : false;
            
            // Sync all toggles to match the clicked one
            if (songsToggle) songsToggle.checked = showBlacklisted;
            if (artistsToggle) artistsToggle.checked = showBlacklisted;
            if (albumsToggle) albumsToggle.checked = showBlacklisted;
            
            // Save preference
            localStorage.setItem('showBlacklistedStats', showBlacklisted ? 'true' : 'false');
            
            // Toggle visibility of all blacklisted stat boxes
            var blacklistedStats = document.querySelectorAll('.blacklisted-stats');
            blacklistedStats.forEach(function(stat) {{
                stat.style.display = showBlacklisted ? '' : 'none';
            }});
        }}
        
        // Load saved blacklisted stats preference for Top tabs
        function loadBlacklistedStatsPreference() {{
            var showBlacklistedStats = localStorage.getItem('showBlacklistedStats') === 'true';
            var songsToggle = document.getElementById('blacklist-toggle-songs');
            var artistsToggle = document.getElementById('blacklist-toggle-artists');
            var albumsToggle = document.getElementById('blacklist-toggle-albums');
            
            if (songsToggle) songsToggle.checked = showBlacklistedStats;
            if (artistsToggle) artistsToggle.checked = showBlacklistedStats;
            if (albumsToggle) albumsToggle.checked = showBlacklistedStats;
            
            toggleBlacklistedStats();
        }}
        
        // Load saved blacklisted column preference
        function loadBlacklistedPreference() {{
            var showBlacklisted = localStorage.getItem('showBlacklisted') === 'true';
            var toggle = document.getElementById('blacklist-toggle');
            if (toggle) {{
                toggle.checked = showBlacklisted;
                toggleBlacklistedColumns();
            }}
        }}
        
        // Update all time displays based on format
        function updateTimeDisplays(isExtended) {{
            var timeElements = document.querySelectorAll('.time-value');
            timeElements.forEach(function(element) {{
                var ms = parseInt(element.getAttribute('data-ms'));
                element.textContent = formatTime(ms, isExtended);
            }});
        }}
        
        // Format time based on selected format
        function formatTime(ms, isExtended) {{
            if (isExtended) {{
                var days = Math.floor(ms / (24 * 60 * 60 * 1000));
                var hours = Math.floor((ms % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
                var minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));
                
                var parts = [];
                if (days > 0) parts.push(days + 'd');
                if (hours > 0) parts.push(hours + 'h');
                if (minutes > 0 || parts.length === 0) parts.push(minutes + 'm');
                
                return parts.join(' ');
            }} else {{
                var minutes = Math.floor(ms / 60000);
                var seconds = Math.floor((ms % 60000) / 1000);
                return minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            }}
        }}
        
        // Track which tabs have been opened
        var openedTabs = {{}};
        
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
            
            // Sort the tab on first open based on the dropdown's current value
            if (!openedTabs[tabName]) {{
                openedTabs[tabName] = true;
                
                if (tabName === 'TopSongs') {{
                    var songSortBy = document.getElementById('songSort').value;
                    sortCards('TopSongs', songSortBy);
                }} else if (tabName === 'TopArtists') {{
                    var artistSortBy = document.getElementById('artistSort').value;
                    sortCards('TopArtists', artistSortBy);
                }} else if (tabName === 'TopAlbums') {{
                    var albumSortBy = document.getElementById('albumSort').value;
                    sortCards('TopAlbums', albumSortBy);
                }}
            }}
        }}
        
        function syncSongs() {{
            var limit = document.getElementById('syncLimit').value;
            window.location.href = '/sync_recent?limit=' + limit;
        }}
        
        function clearDatabase() {{
            if (confirm('Are you sure you want to clear the entire database? This will delete ALL songs, artists, and albums data. This action cannot be undone!')) {{
                window.location.href = '/clear_database';
            }}
        }}
        
        function sortCards(containerId, sortBy) {{
            var container = document.getElementById(containerId);
            var cards = Array.from(container.getElementsByClassName('top-item-card'));
            
            cards.sort(function(a, b) {{
                var aValue, bValue;
                
                if (sortBy === 'listens') {{
                    // Find all stat-box elements that are NOT blacklisted-stats
                    var aStatBoxes = a.querySelectorAll('.stat-box:not(.blacklisted-stats)');
                    var bStatBoxes = b.querySelectorAll('.stat-box:not(.blacklisted-stats)');
                    // First stat-box is the listens count
                    aValue = parseInt(aStatBoxes[0].querySelector('.stat-value').textContent);
                    bValue = parseInt(bStatBoxes[0].querySelector('.stat-value').textContent);
                }} else if (sortBy === 'time') {{
                    // Find all stat-box elements that are NOT blacklisted-stats
                    var aStatBoxes = a.querySelectorAll('.stat-box:not(.blacklisted-stats)');
                    var bStatBoxes = b.querySelectorAll('.stat-box:not(.blacklisted-stats)');
                    // Second stat-box is the time
                    var aTimeElement = aStatBoxes[1].querySelector('.time-value');
                    var bTimeElement = bStatBoxes[1].querySelector('.time-value');
                    aValue = parseInt(aTimeElement.getAttribute('data-ms'));
                    bValue = parseInt(bTimeElement.getAttribute('data-ms'));
                }}
                
                return bValue - aValue; // Descending order
            }});
            
            // Re-append cards in sorted order and update rank numbers
            cards.forEach(function(card, index) {{
                container.appendChild(card);
                card.querySelector('.rank-number').textContent = index + 1;
            }});
        }}
        
        function sortSongs() {{
            var sortBy = document.getElementById('songSort').value;
            sortCards('TopSongs', sortBy);
        }}
        
        function sortArtists() {{
            var sortBy = document.getElementById('artistSort').value;
            sortCards('TopArtists', sortBy);
        }}
        
        function sortAlbums() {{
            var sortBy = document.getElementById('albumSort').value;
            sortCards('TopAlbums', sortBy);
        }}
        
        function sortTable(tableId, columnIndex) {{
            var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
            table = document.getElementById(tableId);
            switching = true;
            dir = "desc";
            
            while (switching) {{
                switching = false;
                rows = table.rows;
                
                for (i = 1; i < (rows.length - 1); i++) {{
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[columnIndex];
                    y = rows[i + 1].getElementsByTagName("TD")[columnIndex];
                    
                    var xValue = parseFloat(x.innerHTML.replace(/:/g, '.')) || x.innerHTML;
                    var yValue = parseFloat(y.innerHTML.replace(/:/g, '.')) || y.innerHTML;
                    
                    if (dir == "desc") {{
                        if (xValue < yValue) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }} else if (dir == "asc") {{
                        if (xValue > yValue) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }}
                }}
                
                if (shouldSwitch) {{
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                }} else {{
                    if (switchcount == 0 && dir == "desc") {{
                        dir = "asc";
                        switching = true;
                    }}
                }}
            }}
        }}
        
        // Open first tab by default on page load
        window.onload = function() {{
            loadTheme();
            loadTimeFormat();
            loadBlacklistedPreference();
            loadBlacklistedStatsPreference();
            document.getElementsByClassName("tablinks")[0].click();
        }}
        
        // Add playlist to blacklist without page refresh
        function addToBlacklist(event) {{
            event.preventDefault();
            var playlistUrl = document.getElementById('playlist_url').value;
            
            fetch('/add_to_blacklist', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                }},
                body: 'playlist_url=' + encodeURIComponent(playlistUrl)
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    // Add new playlist to the list
                    var ul = document.querySelector('.blacklist-list ul');
                    
                    // Remove "no playlists" message if it exists
                    var noPlaylistsMsg = ul.querySelector('li[style*="italic"]');
                    if (noPlaylistsMsg) {{
                        ul.removeChild(noPlaylistsMsg);
                    }}
                    
                    var li = document.createElement('li');
                    li.style.cssText = 'padding: 5px 0; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;';
                    li.setAttribute('data-playlist-id', data.playlist.id);
                    
                    var playlistIcon = '';
                    if (data.playlist.image_url) {{
                        playlistIcon = '<img src="' + data.playlist.image_url + '" alt="" style="width: 40px; height: 40px; margin-right: 10px; border-radius: 4px; vertical-align: middle;">';
                    }} else {{
                        playlistIcon = '• ';
                    }}
                    
                    li.innerHTML = '<span style="display: flex; align-items: center;">' + playlistIcon + data.playlist.name + '</span>' +
                                   '<a href="#" onclick="removeFromBlacklist(event, \\'' + data.playlist.id + '\\')" style="color: #dc3545; text-decoration: none; font-weight: bold; font-size: 18px; cursor: pointer; padding: 0 10px;" title="Remove from blacklist">✕</a>';
                    
                    ul.appendChild(li);
                    document.getElementById('playlist_url').value = '';
                }} else {{
                    alert('Error: ' + data.error);
                }}
            }})
            .catch(error => {{
                alert('Error adding to blacklist');
                console.error('Error:', error);
            }});
        }}
        
        // Remove playlist from blacklist without page refresh
        function removeFromBlacklist(event, playlistId) {{
            event.preventDefault();
            
            fetch('/remove_from_blacklist/' + playlistId, {{
                method: 'GET'
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    // Remove the playlist from the list
                    var li = document.querySelector('li[data-playlist-id="' + playlistId + '"]');
                    if (li) {{
                        li.remove();
                    }}
                    
                    // If no playlists left, show the "no playlists" message
                    var ul = document.querySelector('.blacklist-list ul');
                    if (ul.children.length === 0) {{
                        var li = document.createElement('li');
                        li.style.cssText = 'color: #888; font-style: italic;';
                        li.textContent = 'No playlists blacklisted yet';
                        ul.appendChild(li);
                    }}
                }} else {{
                    alert('Error removing from blacklist');
                }}
            }})
            .catch(error => {{
                alert('Error removing from blacklist');
                console.error('Error:', error);
            }});
        }}
    </script>
    
    <!-- Theme Toggle Switch -->
    <div class="theme-switch-wrapper">
        <label class="theme-switch" for="theme-toggle">
            <input type="checkbox" id="theme-toggle" onchange="toggleTheme()">
            <div class="slider"></div>
        </label>
        <span class="theme-label">🌙</span>
    </div>
    
    <!-- User Profile -->
    <div class="user-profile">
        {'<img src="' + user_image + '" alt="' + user_username + '">' if user_image else '<div style="width: 50px; height: 50px; border-radius: 50%; background-color: #1DB954; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: white;">' + (user_username[0] if user_username else "?") + '</div>'}
        <span>{user_username}</span>
    </div>
    
    <h1 class="main-title">Welcome to Kungungalacorgus.stats!</h1>
    
    <div class="blacklist-container" style="margin: 20px 0; padding: 15px; border: 2px solid #1DB954; border-radius: 8px; background-color: #1e1e1e;">
        <h3 style="margin-top: 0;">🚫 Blacklist</h3>
        <p style="color: #ffa500; font-size: 14px; margin-bottom: 15px; padding: 10px; background-color: #2a2a2a; border-radius: 4px;">
            ⚠️ <strong>Important:</strong> Blacklisted data will only be collected for songs played <em>after</em> adding the playlist to the blacklist. 
            This does not work retroactively unless you clear the database and reload all songs.
        </p>
        <form onsubmit="addToBlacklist(event)" style="margin-bottom: 15px;">
            <label for="playlist_url" style="font-weight: bold;">Playlist URL or ID:</label>
            <input type="text" id="playlist_url" name="playlist_url" placeholder="https://open.spotify.com/playlist/..." style="width: 400px; padding: 8px; margin: 0 10px; font-size: 14px;">
            <button type="submit" style="padding: 8px 16px; background-color: #dc3545; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px;">
                Blacklist
            </button>
        </form>
        <div class="blacklist-list" style="max-height: 150px; overflow-y: auto; border: 1px solid #1DB954; padding: 10px; background-color: #2a2a2a; border-radius: 4px;">
            <strong>Blacklisted Playlists:</strong>
            <ul style="list-style-type: none; padding-left: 0; margin: 10px 0 0 0;">
    """
    
    if blacklist:
        for playlist in blacklist:
            # Display image if available, otherwise use bullet
            playlist_icon = ""
            if playlist.get('image_url'):
                playlist_icon = f'<img src="{playlist["image_url"]}" alt="" style="width: 40px; height: 40px; margin-right: 10px; border-radius: 4px; vertical-align: middle;">'
            else:
                playlist_icon = "• "
            
            html += f"""<li style='padding: 5px 0; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;' data-playlist-id='{playlist['id']}'>
                <span style='display: flex; align-items: center;'>{playlist_icon}{playlist['name']}</span>
                <a href='#' onclick='removeFromBlacklist(event, "{playlist["id"]}")' style='color: #dc3545; text-decoration: none; font-weight: bold; font-size: 18px; cursor: pointer; padding: 0 10px;' title='Remove from blacklist'>✕</a>
            </li>"""
    else:
        html += "<li style='color: #888; font-style: italic;'>No playlists blacklisted yet</li>"
    
    html += """
            </ul>
        </div>
    </div>
    
    <!-- Clear Database Button -->
    <div style="text-align: center; margin: 20px 0;">
        <button onclick="clearDatabase()" style="padding: 10px 20px; background-color: #dc3545; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px;">
            🗑️ Clear Database
        </button>
        <p style="font-size: 12px; color: #888; margin: 5px 0 0 0;">⚠️ This will delete ALL your data!</p>
    </div>
    
    <!-- Tab Navigation -->
    <div class="tab">
        <button class="tablinks" onclick="openTab(event, 'Statistics')">Statistics</button>
        <button class="tablinks" onclick="openTab(event, 'TopSongs')">Top Songs</button>
        <button class="tablinks" onclick="openTab(event, 'TopArtists')">Top Artists</button>
        <button class="tablinks" onclick="openTab(event, 'TopAlbums')">Top Albums</button>
    </div>
    
    <!-- Statistics Tab -->
    <div id="Statistics" class="tabcontent">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0;">Song Statistics</h2>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="time-format-wrapper">
                    <span class="time-format-label">Hide Blacklisted</span>
                    <label class="time-format-switch" for="blacklist-toggle">
                        <input type="checkbox" id="blacklist-toggle" onchange="toggleBlacklistedColumns()">
                        <div class="slider"></div>
                    </label>
                    <span class="time-format-label">Show Blacklisted</span>
                </div>
                <div class="time-format-wrapper">
                    <span class="time-format-label">Listen Time: m:s</span>
                    <label class="time-format-switch" for="time-format-toggle-stats">
                        <input type="checkbox" id="time-format-toggle-stats" onchange="toggleTimeFormat('time-format-toggle-stats')">
                        <div class="slider"></div>
                    </label>
                    <span class="time-format-label">d/h/m</span>
                </div>
                <div>
                    <label for="syncLimit" style="font-weight: bold; margin-right: 10px;">Load songs (1-50):</label>
                    <input type="number" id="syncLimit" min="1" max="50" value="10" style="width: 70px; padding: 8px; font-size: 14px;">
                    <button onclick="syncSongs()" style="padding: 8px 16px; background-color: #1DB954; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px; margin-left: 10px;">
                        📥 Load
                    </button>
                    <p style="font-size: 12px; color: #888; margin: 5px 0 0 0; font-style: italic;">Can be used multiple times to load more history</p>
                </div>
            </div>
        </div>
        <table border="1" style="border-collapse: collapse; width: 100%; table-layout: fixed;">
            <tr>
                <th style="padding: 10px;">Title</th>
                <th style="padding: 10px;">Artist(s)</th>
                <th style="padding: 10px;">Album</th>
                <th style="padding: 10px; text-align: center; width: 100px;">Length</th>
                <th style="padding: 10px; text-align: center; width: 100px;">Listen Count</th>
                <th style="padding: 10px; text-align: center; width: 120px;">Total Listen Time</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 100px; display: none;">Blacklisted Listens</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 120px; display: none;">Blacklisted Time</th>
            </tr>
    """
    
    for song in song_list:
        html += f"""
            <tr>
                <td style="padding: 10px;">{song['title']}</td>
                <td style="padding: 10px;">{song['artists']}</td>
                <td style="padding: 10px;">{song['album_title']}</td>
                <td style="padding: 10px; text-align: center;" class="time-value" data-ms="{song['length_ms']}">{song['length_formatted']}</td>
                <td style="padding: 10px; text-align: center;">{song['listen_count']}</td>
                <td style="padding: 10px; text-align: center;" class="time-value" data-ms="{song['listen_time_ms']}">{song['listen_time_formatted']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;">{song['blacklisted_listens']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;" class="time-value" data-ms="{song['blacklisted_time_ms']}">{song['blacklisted_time_formatted']}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <!-- Song Totals -->
        <div style="margin: 20px 0; padding: 15px; background-color: #1e1e1e; border-radius: 8px; border: 2px solid #1DB954;">
            <h3 style="margin-top: 0; color: #1DB954;">Song Totals</h3>
            <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                <div>
                    <strong>Total Listens:</strong> """ + str(total_song_listens) + """
                </div>
                <div>
                    <strong>Total Listen Time:</strong> <span class="time-value" data-ms=\"""" + str(total_song_time_ms) + """\">""" + total_song_time_formatted + """</span>
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Listens:</strong> """ + str(total_song_blacklisted_listens) + """
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Time:</strong> <span class="time-value" data-ms=\"""" + str(total_song_blacklisted_time_ms) + """\">""" + total_song_blacklisted_time_formatted + """</span>
                </div>
            </div>
        </div>
        
        <h2>Artist Statistics</h2>
        <table border="1" style="border-collapse: collapse; width: 100%; table-layout: fixed;">
            <tr>
                <th style="padding: 10px;">Artist Name</th>
                <th style="padding: 10px; text-align: center; width: 120px;">Total Listens</th>
                <th style="padding: 10px; text-align: center; width: 140px;">Total Listen Time</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 100px; display: none;">Blacklisted Listens</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 120px; display: none;">Blacklisted Time</th>
            </tr>
    """
    
    for artist in artist_list:
        html += f"""
            <tr>
                <td style="padding: 10px;">{artist['name']}</td>
                <td style="padding: 10px; text-align: center;">{artist['listens']}</td>
                <td style="padding: 10px; text-align: center;" class="time-value" data-ms="{artist['listen_time_ms']}">{artist['listen_time_formatted']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;">{artist['blacklisted_listens']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;" class="time-value" data-ms="{artist['blacklisted_time_ms']}">{artist['blacklisted_time_formatted']}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <!-- Artist Totals -->
        <div style="margin: 20px 0; padding: 15px; background-color: #1e1e1e; border-radius: 8px; border: 2px solid #1DB954;">
            <h3 style="margin-top: 0; color: #1DB954;">Artist Totals</h3>
            <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                <div>
                    <strong>Total Listens:</strong> """ + str(total_artist_listens) + """
                </div>
                <div>
                    <strong>Total Listen Time:</strong> <span class="time-value" data-ms=\"""" + str(total_artist_time_ms) + """\">""" + total_artist_time_formatted + """</span>
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Listens:</strong> """ + str(total_artist_blacklisted_listens) + """
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Time:</strong> <span class="time-value" data-ms=\"""" + str(total_artist_blacklisted_time_ms) + """\">""" + total_artist_blacklisted_time_formatted + """</span>
                </div>
            </div>
        </div>
        
        <h2>Album Statistics</h2>
        <table border="1" style="border-collapse: collapse; width: 100%; table-layout: fixed;">
            <tr>
                <th style="padding: 10px;">Album Title</th>
                <th style="padding: 10px; text-align: center; width: 140px;">Total Listen Time</th>
                <th style="padding: 10px; text-align: center; width: 120px;">Album Listens</th>
                <th style="padding: 10px; text-align: center; width: 120px;">Album Length</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 100px; display: none;">Blacklisted Listens</th>
                <th class="blacklisted-column" style="padding: 10px; text-align: center; width: 120px; display: none;">Blacklisted Time</th>
            </tr>
    """
    
    for album in album_list:
        html += f"""
            <tr>
                <td style="padding: 10px;">{album['title']}</td>
                <td style="padding: 10px; text-align: center;" class="time-value" data-ms="{album['listen_time_ms']}">{album['listen_time_formatted']}</td>
                <td style="padding: 10px; text-align: center;">{album['listens']}</td>
                <td style="padding: 10px; text-align: center;" class="time-value" data-ms="{album['length_ms']}">{album['length_formatted']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;">{album['blacklisted_listens']}</td>
                <td class="blacklisted-column" style="padding: 10px; text-align: center; display: none;" class="time-value" data-ms="{album['blacklisted_time_ms']}">{album['blacklisted_time_formatted']}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <!-- Album Totals -->
        <div style="margin: 20px 0; padding: 15px; background-color: #1e1e1e; border-radius: 8px; border: 2px solid #1DB954;">
            <h3 style="margin-top: 0; color: #1DB954;">Album Totals</h3>
            <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                <div>
                    <strong>Total Listens:</strong> """ + str(total_album_listens) + """
                </div>
                <div>
                    <strong>Total Listen Time:</strong> <span class="time-value" data-ms=\"""" + str(total_album_time_ms) + """\">""" + total_album_time_formatted + """</span>
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Listens:</strong> """ + str(total_album_blacklisted_listens) + """
                </div>
                <div class="blacklisted-column" style="display: none;">
                    <strong>Total Blacklisted Time:</strong> <span class="time-value" data-ms=\"""" + str(total_album_blacklisted_time_ms) + """\">""" + total_album_blacklisted_time_formatted + """</span>
                </div>
            </div>
        </div>
        
        <h2>Your Playlists</h2>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th style="padding: 10px;">Playlist Name</th>
            </tr>
    """
    
    for playlist in all_playlists:
        playlist_display = ""
        if playlist.get('image_url'):
            playlist_display = f'<img src="{playlist["image_url"]}" alt="{playlist["name"]}" style="width: 50px; height: 50px; margin-right: 10px; vertical-align: middle; border-radius: 4px;"> {playlist["name"]}'
        else:
            playlist_display = playlist['name']
        
        html += f"""
            <tr>
                <td style="padding: 10px;">{playlist_display}</td>
            </tr>
        """
    
    html += """
        </table>
    </div>
    
    <!-- Top Songs Tab -->
    <div id="TopSongs" class="tabcontent">
        <h2>Top Songs</h2>
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 15px 0;">
            <div class="sort-control">
                <label for="songSort" style="font-weight: bold; margin-right: 10px;">Sort by:</label>
                <select id="songSort" onchange="sortSongs()">
                    <option value="listens">Listen Count</option>
                    <option value="time">Total Listen Time</option>
                </select>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="time-format-wrapper">
                    <span class="time-format-label">Show Blacklisted</span>
                    <label class="time-format-switch" for="blacklist-toggle-songs">
                        <input type="checkbox" id="blacklist-toggle-songs" onchange="toggleBlacklistedStats()">
                        <div class="slider"></div>
                    </label>
                </div>
                <div class="time-format-wrapper">
                    <span class="time-format-label">Listen Time: m:s</span>
                    <label class="time-format-switch" for="time-format-toggle">
                        <input type="checkbox" id="time-format-toggle" onchange="toggleTimeFormat('time-format-toggle')">
                        <div class="slider"></div>
                    </label>
                    <span class="time-format-label">d/h/m</span>
                </div>
            </div>
        </div>
    """
    
    for idx, song in enumerate(song_list[:50], 1):  # Top 50 songs
        # Use actual album art or fallback to SVG placeholder
        img_url = song.get('image_url') or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='%231DB954'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='40' fill='white'%3E♪%3C/text%3E%3C/svg%3E"
        
        html += f"""
        <div class="top-item-card">
            <div class="rank-number">{idx}</div>
            <img src="{img_url}" alt="{song['title']}" class="item-image">
            <div class="item-info">
                <div class="item-title">{song['title']} - {song['artists']}</div>
                <div class="item-subtitle">{song['album_title']}</div>
            </div>
            <div class="item-stats">
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value">{song.get('blacklisted_listens', 0)}</div>
                    <div class="stat-label">Blacklisted Plays</div>
                </div>
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value time-value" data-ms="{song.get('blacklisted_time_ms', 0)}">{song.get('blacklisted_time_formatted', '0:00')}</div>
                    <div class="stat-label">Blacklisted Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{song['listen_count']}</div>
                    <div class="stat-label">Plays</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value time-value" data-ms="{song['listen_time_ms']}">{song['listen_time_formatted']}</div>
                    <div class="stat-label">Time</div>
                </div>
            </div>
        </div>
        """
    
    html += """
    </div>
    
    <!-- Top Artists Tab -->
    <div id="TopArtists" class="tabcontent">
        <h2>Top Artists</h2>
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 15px 0;">
            <div class="sort-control">
                <label for="artistSort" style="font-weight: bold; margin-right: 10px;">Sort by:</label>
                <select id="artistSort" onchange="sortArtists()">
                    <option value="listens">Total Listens</option>
                    <option value="time">Total Listen Time</option>
                </select>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="time-format-wrapper">
                    <span class="time-format-label">Show Blacklisted</span>
                    <label class="time-format-switch" for="blacklist-toggle-artists">
                        <input type="checkbox" id="blacklist-toggle-artists" onchange="toggleBlacklistedStats()">
                        <div class="slider"></div>
                    </label>
                </div>
                <div class="time-format-wrapper">
                    <span class="time-format-label">Listen Time: m:s</span>
                    <label class="time-format-switch" for="time-format-toggle-artists">
                        <input type="checkbox" id="time-format-toggle-artists" onchange="toggleTimeFormat('time-format-toggle-artists')">
                        <div class="slider"></div>
                    </label>
                    <span class="time-format-label">d/h/m</span>
                </div>
            </div>
        </div>
    """
    
    for idx, artist in enumerate(artist_list[:50], 1):  
        # Use actual artist image or fallback to SVG placeholder
        img_url = artist.get('image_url') or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='%231DB954'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='35' fill='white'%3E🎤%3C/text%3E%3C/svg%3E"
        
        html += f"""
        <div class="top-item-card">
            <div class="rank-number">{idx}</div>
            <img src="{img_url}" alt="{artist['name']}" class="item-image">
            <div class="item-info">
                <div class="item-title">{artist['name']}</div>
            </div>
            <div class="item-stats">
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value">{artist.get('blacklisted_listens', 0)}</div>
                    <div class="stat-label">Blacklisted Listens</div>
                </div>
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value time-value" data-ms="{artist.get('blacklisted_time_ms', 0)}">{artist.get('blacklisted_time_formatted', '0:00')}</div>
                    <div class="stat-label">Blacklisted Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{artist['listens']}</div>
                    <div class="stat-label">Listens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value time-value" data-ms="{artist['listen_time_ms']}">{artist['listen_time_formatted']}</div>
                    <div class="stat-label">Time</div>
                </div>
            </div>
        </div>
        """
    
    html += """
    </div>
    
    <!-- Top Albums Tab -->
    <div id="TopAlbums" class="tabcontent">
        <h2>Top Albums</h2>
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 15px 0;">
            <div class="sort-control">
                <label for="albumSort" style="font-weight: bold; margin-right: 10px;">Sort by:</label>
                <select id="albumSort" onchange="sortAlbums()">
                    <option value="listens">Album Listens</option>
                    <option value="time">Total Listen Time</option>
                </select>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="time-format-wrapper">
                    <span class="time-format-label">Show Blacklisted</span>
                    <label class="time-format-switch" for="blacklist-toggle-albums">
                        <input type="checkbox" id="blacklist-toggle-albums" onchange="toggleBlacklistedStats()">
                        <div class="slider"></div>
                    </label>
                </div>
                <div class="time-format-wrapper">
                    <span class="time-format-label">Listen Time: m:s</span>
                    <label class="time-format-switch" for="time-format-toggle-albums">
                        <input type="checkbox" id="time-format-toggle-albums" onchange="toggleTimeFormat('time-format-toggle-albums')">
                        <div class="slider"></div>
                    </label>
                    <span class="time-format-label">d/h/m</span>
                </div>
            </div>
        </div>
    """
    
    for idx, album in enumerate(album_list[:50], 1): 
        # Use actual album image or fallback to SVG placeholder
        img_url = album.get('image_url') or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='%231DB954'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='35' fill='white'%3E💿%3C/text%3E%3C/svg%3E"
        
        html += f"""
        <div class="top-item-card">
            <div class="rank-number">{idx}</div>
            <img src="{img_url}" alt="{album['title']}" class="item-image">
            <div class="item-info">
                <div class="item-title">{album['title']}</div>
                <div class="item-subtitle">Length: <span class="time-value" data-ms="{album['length_ms']}">{album['length_formatted']}</span></div>
            </div>
            <div class="item-stats">
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value">{album.get('blacklisted_listens', 0)}</div>
                    <div class="stat-label">Blacklisted Listens</div>
                </div>
                <div class="stat-box blacklisted-stats" style="display: none;">
                    <div class="stat-value time-value" data-ms="{album.get('blacklisted_time_ms', 0)}">{album.get('blacklisted_time_formatted', '0:00')}</div>
                    <div class="stat-label">Blacklisted Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{album['listens']}</div>
                    <div class="stat-label">Listens</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value time-value" data-ms="{album['listen_time_ms']}">{album['listen_time_formatted']}</div>
                    <div class="stat-label">Time</div>
                </div>
            </div>
        </div>
        """
    
    html += """
        </table>
    </div>
    
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
    session['refresh_token'] = new_token_info.get('refresh_token', session['refresh_token'])
    session['expires_at'] = expires_at
    
    save_token_to_file(new_token_info['access_token'], session['refresh_token'], expires_at)
    
    return redirect('/menu')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, use_reloader=False)