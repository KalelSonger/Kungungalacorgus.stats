import os
import requests
import urllib.parse
import json
import subprocess
import time
import glob
import platform
import shutil

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
    # Detect OS and find ngrok executable
    system = platform.system()
    
    if system == 'Windows':
        ngrok_path = os.path.expanduser('~\\AppData\\Local\\Microsoft\\WindowsApps\\ngrok.exe')
    elif system == 'Darwin':  # MacOS
        ngrok_path = shutil.which('ngrok') or os.path.expanduser('~/.ngrok2/ngrok')
    else:  # Linux and other Unix-like systems
        ngrok_path = shutil.which('ngrok') or '/usr/local/bin/ngrok'
    
    try:
        subprocess.Popen([ngrok_path, 'http', '5000', f'--domain={NGROK_DOMAIN}'], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give ngrok time to start
        print("✓ ngrok tunnel started successfully")
        print(f"   App available at: https://{NGROK_DOMAIN}")
        print(f"\n   IMPORTANT: Your professor must configure ngrok authtoken on their machine:")
        print(f"   ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz")
        print(f"\n   See SETUP.md for full instructions.\n")
    except Exception as e:
        print(f"Warning: Could not start ngrok: {e}")
        print(f"   Make sure ngrok is installed. See SETUP.md for instructions.")

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
        <li><a href='/database_values'>Database Values</a></li>
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

@app.route('/database_values')
def database_values():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    # Fetch user profile
    profile_response = requests.get(API_BASE_URL + '/me', headers=headers)
    user_profile = profile_response.json()
    user_id = user_profile.get('id', 'N/A')
    user_username = user_profile.get('display_name', 'N/A')
    
    # Fetch all playlists
    all_playlists = []
    playlists_response = requests.get(API_BASE_URL + '/me/playlists?limit=50', headers=headers)
    playlists = playlists_response.json()
    if 'items' in playlists:
        for playlist in playlists['items']:
            all_playlists.append({
                'id': playlist['id'],
                'name': playlist['name']
            })
    
    # Fetch 25 most recent songs
    recent_response = requests.get(API_BASE_URL + '/me/player/recently-played?limit=25', headers=headers)
    recent = recent_response.json()
    
    # Dictionary to track song stats: {song_id: {title, length_ms, listen_count, artists, album}}
    song_stats = {}
    # Dictionary to track artist stats: {artist_id: {name, listens, listen_time_ms}}
    artist_stats = {}
    # Dictionary to track album stats: {album_id: {title, songs: {song_id: {length, listen_count, listen_time}}}}
    album_stats = {}
    
    if 'items' in recent:
        for item in recent['items']:
            track = item['track']
            song_id = track['id']
            song_title = track['name']
            song_length_ms = track['duration_ms']
            artists = track['artists']
            album = track['album']
            album_id = album['id']
            album_title = album['name']
            
            if song_id in song_stats:
                # Song already exists, increment listen count
                song_stats[song_id]['listen_count'] += 1
            else:
                # New song, add to dictionary
                song_stats[song_id] = {
                    'title': song_title,
                    'length_ms': song_length_ms,
                    'listen_count': 1,
                    'artists': artists,
                    'album_id': album_id,
                    'album_title': album_title
                }
    
    # Calculate listen time for each song (length * listen_count)
    song_list = []
    for song_id, stats in song_stats.items():
        listen_time_ms = stats['length_ms'] * stats['listen_count']
        
        # Format artist names
        artist_names = ', '.join([artist['name'] for artist in stats['artists']])
        
        song_list.append({
            'id': song_id,
            'title': stats['title'],
            'artists': artist_names,
            'album_title': stats['album_title'],
            'length_ms': stats['length_ms'],
            'length_formatted': f"{stats['length_ms'] // 60000}:{(stats['length_ms'] % 60000) // 1000:02d}",
            'listen_count': stats['listen_count'],
            'listen_time_ms': listen_time_ms,
            'listen_time_formatted': f"{listen_time_ms // 60000}:{(listen_time_ms % 60000) // 1000:02d}"
        })
        
        # Aggregate artist stats
        for artist in stats['artists']:
            artist_id = artist['id']
            artist_name = artist['name']
            
            if artist_id in artist_stats:
                # Artist already exists, add to their stats
                artist_stats[artist_id]['listens'] += stats['listen_count']
                artist_stats[artist_id]['listen_time_ms'] += listen_time_ms
            else:
                # New artist, add to dictionary
                artist_stats[artist_id] = {
                    'name': artist_name,
                    'listens': stats['listen_count'],
                    'listen_time_ms': listen_time_ms
                }
        
        # Aggregate album stats
        album_id = stats['album_id']
        album_title = stats['album_title']
        
        if album_id not in album_stats:
            album_stats[album_id] = {
                'title': album_title,
                'songs': {}
            }
        
        # Track this song within the album
        album_stats[album_id]['songs'][song_id] = {
            'length_ms': stats['length_ms'],
            'listen_count': stats['listen_count'],
            'listen_time_ms': listen_time_ms
        }
    
    # Create artist list with formatted times
    artist_list = []
    for artist_id, stats in artist_stats.items():
        artist_list.append({
            'id': artist_id,
            'name': stats['name'],
            'listens': stats['listens'],
            'listen_time_ms': stats['listen_time_ms'],
            'listen_time_formatted': f"{stats['listen_time_ms'] // 60000}:{(stats['listen_time_ms'] % 60000) // 1000:02d}"
        })
    
    # Create album list with calculated stats
    album_list = []
    for album_id, stats in album_stats.items():
        # Fetch full album details to get ALL tracks on the album
        album_response = requests.get(API_BASE_URL + f'/albums/{album_id}', headers=headers)
        album_data = album_response.json()
        
        # Get all track IDs from the full album
        all_album_track_ids = set()
        if 'tracks' in album_data and 'items' in album_data['tracks']:
            for track in album_data['tracks']['items']:
                all_album_track_ids.add(track['id'])
        
        # Calculate total listen time (sum of all song listen times in this album from our recent plays)
        total_listen_time_ms = sum(song['listen_time_ms'] for song in stats['songs'].values())
        
        # Calculate total album length (sum of all song lengths from the full album)
        total_album_length_ms = 0
        if 'tracks' in album_data and 'items' in album_data['tracks']:
            for track in album_data['tracks']['items']:
                total_album_length_ms += track['duration_ms']
        
        # Calculate album listens (minimum listen count across ALL songs on the full album)
        # If a song from the album hasn't been played, its listen count is 0
        min_listen_count = 0
        if all_album_track_ids:
            # For each track on the album, get its listen count (0 if not in our recent plays)
            listen_counts = []
            for track_id in all_album_track_ids:
                if track_id in stats['songs']:
                    listen_counts.append(stats['songs'][track_id]['listen_count'])
                else:
                    listen_counts.append(0)  # Song not in recent plays = 0 listens
            
            min_listen_count = min(listen_counts) if listen_counts else 0
        
        album_list.append({
            'id': album_id,
            'title': stats['title'],
            'listen_time_ms': total_listen_time_ms,
            'listen_time_formatted': f"{total_listen_time_ms // 60000}:{(total_listen_time_ms % 60000) // 1000:02d}",
            'listens': min_listen_count,
            'length_ms': total_album_length_ms,
            'length_formatted': f"{total_album_length_ms // 60000}:{(total_album_length_ms % 60000) // 1000:02d}"
        })
    
    # Delete old database_values txt files
    old_files = glob.glob('database_values_*.txt')
    for old_file in old_files:
        try:
            os.remove(old_file)
        except:
            pass  # If file can't be deleted, just continue
    
    # Save to txt file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'database_values_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("SPOTIFY STATS - DATABASE VALUES\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("SONG STATISTICS FROM 20 MOST RECENT TRACKS\n")
        f.write("-" * 80 + "\n\n")
        
        for song in song_list:
            f.write(f"Song ID: {song['id']}\n")
            f.write(f"Title: {song['title']}\n")
            f.write(f"Artist(s): {song['artists']}\n")
            f.write(f"Album: {song['album_title']}\n")
            f.write(f"Length: {song['length_formatted']} ({song['length_ms']} ms)\n")
            f.write(f"Listen Count: {song['listen_count']}\n")
            f.write(f"Total Listen Time: {song['listen_time_formatted']} ({song['listen_time_ms']} ms)\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n\nARTIST STATISTICS\n")
        f.write("-" * 80 + "\n\n")
        
        for artist in artist_list:
            f.write(f"Artist ID: {artist['id']}\n")
            f.write(f"Artist Name: {artist['name']}\n")
            f.write(f"Total Listens: {artist['listens']}\n")
            f.write(f"Total Listen Time: {artist['listen_time_formatted']} ({artist['listen_time_ms']} ms)\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n\nALBUM STATISTICS\n")
        f.write("-" * 80 + "\n\n")
        
        for album in album_list:
            f.write(f"Album ID: {album['id']}\n")
            f.write(f"Album Title: {album['title']}\n")
            f.write(f"Album Listen Time: {album['listen_time_formatted']} ({album['listen_time_ms']} ms)\n")
            f.write(f"Album Listens: {album['listens']}\n")
            f.write(f"Album Length: {album['length_formatted']} ({album['length_ms']} ms)\n")
            f.write("-" * 80 + "\n")
    
    # Build HTML response
    html = f"""
    <h1>Database Values - Song, Artist & Album Statistics</h1>
    <p><em>Data saved to: {filename}</em></p>
    <p><em>Based on your 25 most recently played tracks</em></p>
    
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
    
    session['access_token'] = new_token_info['access_token']
    session['refresh_token'] = new_token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
    
    return redirect('/playlists')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug = True)