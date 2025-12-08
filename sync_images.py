"""
Sync images for existing songs, artists, and albums in the database
This is a one-time script to populate image URLs for existing data
"""
import os
import requests
import json
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

TOKEN_FILE = 'spotify_token.json'
API_BASE_URL = 'https://api.spotify.com/v1'

def load_token_from_file():
    """Load access token from file"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            return data.get('access_token')
    except FileNotFoundError:
        print("❌ Token file not found. Please login to Spotify first.")
        return None

def get_all_song_ids():
    """Get all song IDs from database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT S_ID FROM Songs WHERE flag = 1")
        result = cursor.fetchall()
        cursor.close()
        return [row[0] for row in result]
    except Error as e:
        print(f"Error getting song IDs: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def get_all_artist_ids():
    """Get all artist IDs from database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT A_ID FROM Artists WHERE flag = 1")
        result = cursor.fetchall()
        cursor.close()
        return [row[0] for row in result]
    except Error as e:
        print(f"Error getting artist IDs: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def get_all_album_ids():
    """Get all album IDs from database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT A_ID FROM Albums WHERE flag = 1")
        result = cursor.fetchall()
        cursor.close()
        return [row[0] for row in result]
    except Error as e:
        print(f"Error getting album IDs: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def update_song_image(song_id, image_url):
    """Update song image URL in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Add image_url column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'image_url'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Songs ADD COLUMN image_url VARCHAR(500) DEFAULT NULL")
            connection.commit()
            print("✓ Added image_url column to Songs table")
        
        cursor.execute("UPDATE Songs SET image_url = %s WHERE S_ID = %s", (image_url, song_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error updating song image: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def update_artist_image(artist_id, image_url):
    """Update artist image URL in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Add image_url column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Artists' 
            AND COLUMN_NAME = 'image_url'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Artists ADD COLUMN image_url VARCHAR(500) DEFAULT NULL")
            connection.commit()
            print("✓ Added image_url column to Artists table")
        
        cursor.execute("UPDATE Artists SET image_url = %s WHERE A_ID = %s", (image_url, artist_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error updating artist image: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def update_album_image(album_id, image_url):
    """Update album image URL in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Add image_url column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Albums' 
            AND COLUMN_NAME = 'image_url'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Albums ADD COLUMN image_url VARCHAR(500) DEFAULT NULL")
            connection.commit()
            print("✓ Added image_url column to Albums table")
        
        cursor.execute("UPDATE Albums SET image_url = %s WHERE A_ID = %s", (image_url, album_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error updating album image: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def sync_images():
    """Sync images for all existing songs, artists, and albums"""
    access_token = load_token_from_file()
    if not access_token:
        return
    
    headers = {'Authorization': f"Bearer {access_token}"}
    
    # Sync songs (get track details for album art)
    print("\n📷 Syncing song images...")
    song_ids = get_all_song_ids()
    print(f"Found {len(song_ids)} songs")
    
    for idx, song_id in enumerate(song_ids, 1):
        try:
            response = requests.get(f"{API_BASE_URL}/tracks/{song_id}", headers=headers)
            if response.status_code == 200:
                track = response.json()
                image_url = track['album']['images'][0]['url'] if track['album'].get('images') else None
                if image_url:
                    update_song_image(song_id, image_url)
                    print(f"  [{idx}/{len(song_ids)}] ✓ {track['name']}")
                else:
                    print(f"  [{idx}/{len(song_ids)}] ⚠ No image for {track.get('name', song_id)}")
            else:
                print(f"  [{idx}/{len(song_ids)}] ❌ Failed to fetch track {song_id}: {response.status_code}")
        except Exception as e:
            print(f"  [{idx}/{len(song_ids)}] ❌ Error: {e}")
    
    # Sync artists
    print("\n📷 Syncing artist images...")
    artist_ids = get_all_artist_ids()
    print(f"Found {len(artist_ids)} artists")
    
    for idx, artist_id in enumerate(artist_ids, 1):
        try:
            response = requests.get(f"{API_BASE_URL}/artists/{artist_id}", headers=headers)
            if response.status_code == 200:
                artist = response.json()
                image_url = artist['images'][0]['url'] if artist.get('images') else None
                if image_url:
                    update_artist_image(artist_id, image_url)
                    print(f"  [{idx}/{len(artist_ids)}] ✓ {artist['name']}")
                else:
                    print(f"  [{idx}/{len(artist_ids)}] ⚠ No image for {artist.get('name', artist_id)}")
            else:
                print(f"  [{idx}/{len(artist_ids)}] ❌ Failed to fetch artist {artist_id}: {response.status_code}")
        except Exception as e:
            print(f"  [{idx}/{len(artist_ids)}] ❌ Error: {e}")
    
    # Sync albums
    print("\n📷 Syncing album images...")
    album_ids = get_all_album_ids()
    print(f"Found {len(album_ids)} albums")
    
    for idx, album_id in enumerate(album_ids, 1):
        try:
            response = requests.get(f"{API_BASE_URL}/albums/{album_id}", headers=headers)
            if response.status_code == 200:
                album = response.json()
                image_url = album['images'][0]['url'] if album.get('images') else None
                if image_url:
                    update_album_image(album_id, image_url)
                    print(f"  [{idx}/{len(album_ids)}] ✓ {album['name']}")
                else:
                    print(f"  [{idx}/{len(album_ids)}] ⚠ No image for {album.get('name', album_id)}")
            else:
                print(f"  [{idx}/{len(album_ids)}] ❌ Failed to fetch album {album_id}: {response.status_code}")
        except Exception as e:
            print(f"  [{idx}/{len(album_ids)}] ❌ Error: {e}")
    
    print("\n✅ Image sync complete!")

if __name__ == "__main__":
    print("=" * 60)
    print("SPOTIFY IMAGE SYNC TOOL")
    print("=" * 60)
    print("This will fetch and store image URLs for all existing")
    print("songs, artists, and albums in your database.")
    print("=" * 60)
    
    sync_images()
