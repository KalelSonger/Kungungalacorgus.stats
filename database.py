import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'spotifyDatabase')
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_database():
    """Initialize the database - tables should already exist from Stats.sql"""
    connection = get_db_connection()
    if not connection:
        print("Warning: Could not connect to database. Make sure MySQL is running and credentials in .env are correct.")
        return False
    
    try:
        cursor = connection.cursor()
        # Just verify connection works
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()
        print(f"✓ Connected to database successfully ({len(tables)} tables found)")
        return True
    except Error as e:
        print(f"Error checking database: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def insert_or_update_song(song_data):
    """Insert a new song or update existing song's listen count and time"""
    connection = get_db_connection()
    if not connection:
        print(f"⚠ Failed to connect to database for song: {song_data.get('title', 'Unknown')}")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Add last_played column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'last_played'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Songs ADD COLUMN last_played DATETIME DEFAULT NULL")
            connection.commit()
            print("✓ Added last_played column to Songs table")
        
        # Convert played_at to MySQL datetime format if it exists
        played_at = song_data.get('played_at')
        if played_at and hasattr(played_at, 'strftime'):
            played_at_str = played_at.strftime('%Y-%m-%d %H:%M:%S')
        else:
            played_at_str = None
        
        # Check if song exists
        cursor.execute("SELECT S_Listens, S_Listen_Time FROM Songs WHERE S_ID = %s", (song_data['id'],))
        result = cursor.fetchone()
        
        if result:
            # Update existing song - increment listens and update last_played
            new_listen_count = result[0] + 1
            new_listen_time = result[1] + song_data['length_ms']
            cursor.execute("""
                UPDATE Songs 
                SET S_Listens = %s, S_Listen_Time = %s, last_played = %s, flag = 1
                WHERE S_ID = %s
            """, (new_listen_count, new_listen_time, played_at_str, song_data['id']))
        else:
            # Insert new song
            cursor.execute("""
                INSERT INTO Songs (S_ID, S_Title, S_Length, S_Listens, S_Listen_Time, last_played, flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                song_data['id'],
                song_data['title'][:50],  # Limit to 50 chars per schema
                song_data['length_ms'],
                1,
                song_data['length_ms'],
                played_at_str,
                1
            ))
        
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error inserting/updating song '{song_data.get('title', 'Unknown')}': {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def insert_or_update_artist(artist_id, artist_name, song_length_ms):
    """Insert a new artist or update existing artist's stats"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if artist exists
        cursor.execute("SELECT A_Listens, A_ListenTime FROM Artists WHERE A_ID = %s", (artist_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing artist
            new_listens = result[0] + 1
            new_listen_time = result[1] + song_length_ms
            cursor.execute("""
                UPDATE Artists 
                SET A_Listens = %s, A_ListenTime = %s, flag = 1
                WHERE A_ID = %s
            """, (new_listens, new_listen_time, artist_id))
        else:
            # Insert new artist
            cursor.execute("""
                INSERT INTO Artists (A_ID, A_Name, A_Listens, A_ListenTime, flag)
                VALUES (%s, %s, %s, %s, %s)
            """, (artist_id, artist_name[:50], 1, song_length_ms, 1))
        
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error inserting/updating artist: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def link_song_artist_album(song_id, artist_id, album_id):
    """Create a link between song, artist, and album in the Creates table"""
    connection = get_db_connection()
    if not connection:
        print(f"⚠ Failed to connect for linking song {song_id}")
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT IGNORE INTO Creates (ART_ID, S_ID, A_ID)
            VALUES (%s, %s, %s)
        """, (artist_id, song_id, album_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error linking song {song_id}, artist {artist_id}, album {album_id}: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def link_album_song(album_id, song_id):
    """Create a link between album and song in Album_Song table"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT IGNORE INTO Album_Song (A_ID, S_ID)
            VALUES (%s, %s)
        """, (album_id, song_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error linking album and song: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def insert_or_update_album(album_id, album_title, total_tracks, album_length_ms, song_length_ms):
    """Insert a new album or update existing album's stats
    Note: A_Listens will be calculated separately as MIN(song listens) for complete album plays"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if album exists
        cursor.execute("SELECT A_Listen_Time FROM Albums WHERE A_ID = %s", (album_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing album - only update listen time, listens will be calculated separately
            new_listen_time = result[0] + song_length_ms
            
            # Calculate complete album listens:
            # First check if user has ALL songs from the album in database
            # If not, album listens = 0 (haven't completed the album)
            # If yes, album listens = MIN(song listens) across all album songs
            
            # Get total tracks in the actual album (from A_Length which stores total tracks)
            cursor.execute("SELECT A_Length FROM Albums WHERE A_ID = %s", (album_id,))
            album_info = cursor.fetchone()
            
            if album_info:
                # Count how many songs from this album are in the database
                cursor.execute("""
                    SELECT COUNT(DISTINCT s.S_ID) as song_count
                    FROM Songs s
                    JOIN Album_Song als ON s.S_ID = als.S_ID
                    WHERE als.A_ID = %s AND s.flag = 1
                """, (album_id,))
                db_song_count = cursor.fetchone()[0]
                
                # Note: We can't know total album tracks without fetching from API
                # So we'll just use MIN of songs we have, and if any song has 0 listens, album = 0
                cursor.execute("""
                    SELECT MIN(s.S_Listens) as min_listens
                    FROM Songs s
                    JOIN Album_Song als ON s.S_ID = als.S_ID
                    WHERE als.A_ID = %s AND s.flag = 1
                """, (album_id,))
                min_result = cursor.fetchone()
                # If ANY song has 0 listens (or no songs), complete_listens = 0
                complete_listens = min_result[0] if min_result and min_result[0] and min_result[0] > 0 else 0
            else:
                complete_listens = 0
            
            cursor.execute("""
                UPDATE Albums 
                SET A_Listen_Time = %s, A_Listens = %s, flag = 1
                WHERE A_ID = %s
            """, (new_listen_time, complete_listens, album_id))
        else:
            # Insert new album with 0 listens initially (will be calculated after songs are linked)
            cursor.execute("""
                INSERT INTO Albums (A_ID, A_Title, A_Listen_Time, A_Listens, A_Length, flag)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (album_id, album_title[:50], song_length_ms, 0, album_length_ms, 1))
        
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error inserting/updating album: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def get_all_songs():
    """Retrieve all songs from the database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if last_played column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'last_played'
        """)
        has_last_played = cursor.fetchone()['COUNT(*)'] > 0
        
        # Build query based on column existence
        if has_last_played:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       last_played, '' as artists, '' as album_title
                FROM Songs
                WHERE flag = 1
                ORDER BY last_played DESC, S_Listens DESC
            """)
        else:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       NULL as last_played, '' as artists, '' as album_title
                FROM Songs
                WHERE flag = 1
                ORDER BY S_Listens DESC
            """)
        songs = cursor.fetchall()
        
        # Get artists and album for each song
        for song in songs:
            # Get artists for this song
            cursor.execute("""
                SELECT DISTINCT ar.A_Name
                FROM Creates c
                JOIN Artists ar ON c.ART_ID = ar.A_ID
                WHERE c.S_ID = %s
            """, (song['id'],))
            artists = cursor.fetchall()
            song['artists'] = ', '.join([a['A_Name'] for a in artists])
            
            # Get album for this song
            cursor.execute("""
                SELECT al.A_Title
                FROM Album_Song als
                JOIN Albums al ON als.A_ID = al.A_ID
                WHERE als.S_ID = %s
                LIMIT 1
            """, (song['id'],))
            album = cursor.fetchone()
            song['album_title'] = album['A_Title'] if album else 'Unknown Album'
        
        cursor.close()
        return songs
    except Error as e:
        print(f"Error retrieving songs: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def get_all_artists():
    """Retrieve all artists from the database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT A_ID as id, A_Name as name, A_Listens as listens, 
                   A_ListenTime as listen_time_ms
            FROM Artists
            WHERE flag = 1
            ORDER BY A_Listens DESC
        """)
        artists = cursor.fetchall()
        cursor.close()
        return artists
    except Error as e:
        print(f"Error retrieving artists: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def get_all_albums():
    """Retrieve all albums from the database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT A_ID as id, A_Title as title, A_Listen_Time as listen_time_ms, 
                   A_Listens as listens, A_Length as length_ms
            FROM Albums
            WHERE flag = 1
            ORDER BY A_Listens DESC
        """)
        albums = cursor.fetchall()
        cursor.close()
        return albums
    except Error as e:
        print(f"Error retrieving albums: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def get_or_create_user(spotify_user_id, username):
    """Get existing user or create new user, returns U_ID"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Try to find user by username (since we don't store Spotify ID in schema)
        cursor.execute("SELECT U_ID FROM Users WHERE U_Username = %s", (username[:20],))
        result = cursor.fetchone()
        
        if result:
            user_id = result[0]
        else:
            # Insert new user
            cursor.execute("INSERT INTO Users (U_Username) VALUES (%s)", (username[:20],))
            connection.commit()
            user_id = cursor.lastrowid
        
        cursor.close()
        return user_id
    except Error as e:
        print(f"Error getting/creating user: {e}")
        return None
    finally:
        if connection.is_connected():
            connection.close()

def get_user_playlists(user_id):
    """Get all playlists for a user"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT P_ID as id, P_Name as name
            FROM Playlists
            WHERE U_ID = %s
        """, (user_id,))
        playlists = cursor.fetchall()
        cursor.close()
        return playlists
    except Error as e:
        print(f"Error retrieving playlists: {e}")
        return []
    finally:
        if connection.is_connected():
            connection.close()

def insert_or_update_playlist(playlist_id, playlist_name, user_id):
    """Insert or update a playlist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if playlist exists
        cursor.execute("SELECT P_ID FROM Playlists WHERE P_ID = %s", (playlist_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing playlist
            cursor.execute("""
                UPDATE Playlists 
                SET P_Name = %s
                WHERE P_ID = %s
            """, (playlist_name[:50], playlist_id))
        else:
            # Insert new playlist
            cursor.execute("""
                INSERT INTO Playlists (P_ID, P_Name, U_ID)
                VALUES (%s, %s, %s)
            """, (playlist_id, playlist_name[:50], user_id))
        
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error inserting/updating playlist: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def link_playlist_song(playlist_id, song_id):
    """Link a song to a playlist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT IGNORE INTO Playlist_Songs (P_ID, S_ID)
            VALUES (%s, %s)
        """, (playlist_id, song_id))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error linking playlist and song: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

def get_last_sync_timestamp():
    """Get the timestamp of the last sync from a tracking file"""
    try:
        if os.path.exists('last_sync.txt'):
            with open('last_sync.txt', 'r') as f:
                timestamp_str = f.read().strip()
                if timestamp_str:
                    return timestamp_str
    except Exception as e:
        print(f"Error reading last sync timestamp: {e}")
    return None

def save_last_sync_timestamp(timestamp):
    """Save the timestamp of the last successful sync"""
    try:
        with open('last_sync.txt', 'w') as f:
            f.write(timestamp)
    except Exception as e:
        print(f"Error saving last sync timestamp: {e}")

def check_if_play_exists(song_id, played_at_timestamp):
    """Check if a specific play (song + timestamp) has already been processed"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # We'll use a simple heuristic: if the song exists, we've likely processed recent plays
        # For a more robust solution, we'd need a play_history table with timestamps
        cursor.execute("SELECT S_ID FROM Songs WHERE S_ID = %s", (song_id,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except Error as e:
        print(f"Error checking if play exists: {e}")
        return False
    finally:
        if connection.is_connected():
            connection.close()

