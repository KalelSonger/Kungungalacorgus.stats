import mysql.connector
from mysql.connector import Error
import os
import json
from dotenv import load_dotenv

load_dotenv()

def create_database_if_not_exists():
    """Create the database and user if they don't exist"""
    try:
        # Connect without specifying database
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user='root',  # Need root to create database
            password=os.getenv('DB_PASSWORD', '')
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        db_name = os.getenv('DB_NAME', 'spotifyDatabase')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✓ Database '{db_name}' ready")
        
        # Create user if it doesn't exist (MySQL 5.7+ syntax)
        db_user = os.getenv('DB_USER', 'spotify_user')
        db_pass = os.getenv('DB_PASSWORD', '')
        
        try:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")
            cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
            print(f"✓ Database user '{db_user}' configured")
        except Error as e:
            # User might already exist, that's okay
            pass
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        # Auto-creation failed - database likely already exists or wrong root password
        # This is fine, will try connecting with regular credentials next
        return False

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
    """Initialize the database - create if needed, then verify tables"""
    # Try to create database if it doesn't exist
    create_database_if_not_exists()
    
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
        
        # Add S_Blacklisted_Listens column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'S_Blacklisted_Listens'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Songs ADD COLUMN S_Blacklisted_Listens INT DEFAULT 0")
            connection.commit()
            print("✓ Added S_Blacklisted_Listens column to Songs table")
        
        # Add S_Blacklisted_Time column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'S_Blacklisted_Time'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Songs ADD COLUMN S_Blacklisted_Time BIGINT DEFAULT 0")
            connection.commit()
            print("✓ Added S_Blacklisted_Time column to Songs table")
        
        # Convert played_at to MySQL datetime format if it exists
        played_at = song_data.get('played_at')
        if played_at and hasattr(played_at, 'strftime'):
            played_at_str = played_at.strftime('%Y-%m-%d %H:%M:%S')
        else:
            played_at_str = None
        
        # Check if song exists
        cursor.execute("SELECT S_Listens, S_Listen_Time, S_Blacklisted_Listens, S_Blacklisted_Time FROM Songs WHERE S_ID = %s", (song_data['id'],))
        result = cursor.fetchone()
        
        is_blacklisted = song_data.get('is_blacklisted', False)
        
        if result:
            # Update existing song - increment appropriate counters
            new_listen_count = result[0] + (0 if is_blacklisted else 1)
            new_listen_time = result[1] + (0 if is_blacklisted else song_data['length_ms'])
            new_blacklisted_listens = result[2] + (1 if is_blacklisted else 0)
            new_blacklisted_time = result[3] + (song_data['length_ms'] if is_blacklisted else 0)
            
            cursor.execute("""
                UPDATE Songs 
                SET S_Listens = %s, S_Listen_Time = %s, S_Blacklisted_Listens = %s, S_Blacklisted_Time = %s, 
                    last_played = %s, image_url = %s, flag = 1
                WHERE S_ID = %s
            """, (new_listen_count, new_listen_time, new_blacklisted_listens, new_blacklisted_time,
                  played_at_str, song_data.get('image_url'), song_data['id']))
        else:
            # Insert new song
            initial_listens = 0 if is_blacklisted else 1
            initial_time = 0 if is_blacklisted else song_data['length_ms']
            initial_blacklisted_listens = 1 if is_blacklisted else 0
            initial_blacklisted_time = song_data['length_ms'] if is_blacklisted else 0
            
            cursor.execute("""
                INSERT INTO Songs (S_ID, S_Title, S_Length, S_Listens, S_Listen_Time, S_Blacklisted_Listens, 
                                   S_Blacklisted_Time, last_played, image_url, flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                song_data['id'],
                song_data['title'][:50],  # Limit to 50 chars per schema
                song_data['length_ms'],
                initial_listens,
                initial_time,
                initial_blacklisted_listens,
                initial_blacklisted_time,
                played_at_str,
                song_data.get('image_url'),
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

def insert_or_update_artist(artist_id, artist_name, song_length_ms, image_url=None, is_blacklisted=False):
    """Insert a new artist or update existing artist's stats"""
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
        
        # Add A_Blacklisted_Listens column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Artists' 
            AND COLUMN_NAME = 'A_Blacklisted_Listens'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Artists ADD COLUMN A_Blacklisted_Listens INT DEFAULT 0")
            connection.commit()
            print("✓ Added A_Blacklisted_Listens column to Artists table")
        
        # Add A_Blacklisted_Time column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Artists' 
            AND COLUMN_NAME = 'A_Blacklisted_Time'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Artists ADD COLUMN A_Blacklisted_Time BIGINT DEFAULT 0")
            connection.commit()
            print("✓ Added A_Blacklisted_Time column to Artists table")
        
        # Check if artist exists
        cursor.execute("SELECT A_Listens, A_ListenTime, A_Blacklisted_Listens, A_Blacklisted_Time FROM Artists WHERE A_ID = %s", (artist_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing artist
            new_listens = result[0] + (0 if is_blacklisted else 1)
            new_listen_time = result[1] + (0 if is_blacklisted else song_length_ms)
            new_blacklisted_listens = result[2] + (1 if is_blacklisted else 0)
            new_blacklisted_time = result[3] + (song_length_ms if is_blacklisted else 0)
            
            cursor.execute("""
                UPDATE Artists 
                SET A_Listens = %s, A_ListenTime = %s, A_Blacklisted_Listens = %s, A_Blacklisted_Time = %s, 
                    image_url = %s, flag = 1
                WHERE A_ID = %s
            """, (new_listens, new_listen_time, new_blacklisted_listens, new_blacklisted_time, image_url, artist_id))
        else:
            # Insert new artist
            initial_listens = 0 if is_blacklisted else 1
            initial_time = 0 if is_blacklisted else song_length_ms
            initial_blacklisted_listens = 1 if is_blacklisted else 0
            initial_blacklisted_time = song_length_ms if is_blacklisted else 0
            
            cursor.execute("""
                INSERT INTO Artists (A_ID, A_Name, A_Listens, A_ListenTime, A_Blacklisted_Listens, 
                                     A_Blacklisted_Time, image_url, flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (artist_id, artist_name[:50], initial_listens, initial_time, 
                  initial_blacklisted_listens, initial_blacklisted_time, image_url, 1))
        
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

def insert_or_update_album(album_id, album_title, total_tracks, album_length_ms, song_length_ms, image_url=None, is_blacklisted=False):
    """Insert a new album or update existing album's stats
    Note: A_Listens will be calculated as MIN(song listens) only if ALL tracks have been listened to"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Add total_tracks column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Albums' 
            AND COLUMN_NAME = 'total_tracks'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Albums ADD COLUMN total_tracks INT DEFAULT NULL")
            connection.commit()
            print("✓ Added total_tracks column to Albums table")
        
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
        
        # Add A_Blacklisted_Listens column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Albums' 
            AND COLUMN_NAME = 'A_Blacklisted_Listens'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Albums ADD COLUMN A_Blacklisted_Listens INT DEFAULT 0")
            connection.commit()
            print("✓ Added A_Blacklisted_Listens column to Albums table")
        
        # Add A_Blacklisted_Time column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Albums' 
            AND COLUMN_NAME = 'A_Blacklisted_Time'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Albums ADD COLUMN A_Blacklisted_Time BIGINT DEFAULT 0")
            connection.commit()
            print("✓ Added A_Blacklisted_Time column to Albums table")
        
        # Check if album exists
        cursor.execute("SELECT A_Listen_Time, total_tracks, A_Blacklisted_Listens, A_Blacklisted_Time FROM Albums WHERE A_ID = %s", (album_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing album
            new_listen_time = result[0] + (0 if is_blacklisted else song_length_ms)
            stored_total_tracks = result[1] if result[1] else total_tracks
            new_blacklisted_listens = result[2] + (1 if is_blacklisted else 0)
            new_blacklisted_time = result[3] + (song_length_ms if is_blacklisted else 0)
            
            # Calculate complete album listens:
            # Check if user has listened to ALL tracks in the album
            cursor.execute("""
                SELECT COUNT(DISTINCT s.S_ID) as songs_in_db
                FROM Songs s
                JOIN Album_Song als ON s.S_ID = als.S_ID
                WHERE als.A_ID = %s AND s.flag = 1
            """, (album_id,))
            songs_in_db = cursor.fetchone()[0]
            
            # If user has ALL tracks from album AND all have listens > 0, get MIN
            if songs_in_db >= stored_total_tracks:
                cursor.execute("""
                    SELECT MIN(s.S_Listens) as min_listens
                    FROM Songs s
                    JOIN Album_Song als ON s.S_ID = als.S_ID
                    WHERE als.A_ID = %s AND s.flag = 1
                """, (album_id,))
                min_result = cursor.fetchone()
                # If MIN is 0, that means at least one song hasn't been played
                complete_listens = min_result[0] if min_result and min_result[0] and min_result[0] > 0 else 0
            else:
                # User hasn't listened to all tracks yet
                complete_listens = 0
            
            cursor.execute("""
                UPDATE Albums 
                SET A_Listen_Time = %s, A_Listens = %s, A_Blacklisted_Listens = %s, A_Blacklisted_Time = %s,
                    total_tracks = %s, image_url = %s, flag = 1
                WHERE A_ID = %s
            """, (new_listen_time, complete_listens, new_blacklisted_listens, new_blacklisted_time,
                  stored_total_tracks, image_url, album_id))
        else:
            # Insert new album with 0 listens initially
            initial_listens = 0
            initial_time = 0 if is_blacklisted else song_length_ms
            initial_blacklisted_listens = 1 if is_blacklisted else 0
            initial_blacklisted_time = song_length_ms if is_blacklisted else 0
            
            cursor.execute("""
                INSERT INTO Albums (A_ID, A_Title, A_Listen_Time, A_Listens, A_Blacklisted_Listens,
                                    A_Blacklisted_Time, A_Length, total_tracks, image_url, flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (album_id, album_title[:50], initial_time, initial_listens, 
                  initial_blacklisted_listens, initial_blacklisted_time,
                  album_length_ms, total_tracks, image_url, 1))
        
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
        
        # Check if image_url column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Songs' 
            AND COLUMN_NAME = 'image_url'
        """)
        has_image_url = cursor.fetchone()['COUNT(*)'] > 0
        
        # Build query based on column existence
        if has_last_played and has_image_url:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       S_Blacklisted_Listens as blacklisted_listens, S_Blacklisted_Time as blacklisted_time_ms,
                       last_played, image_url, '' as artists, '' as album_title
                FROM Songs
                WHERE flag = 1
                ORDER BY last_played DESC, S_Listens DESC
            """)
        elif has_last_played:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       S_Blacklisted_Listens as blacklisted_listens, S_Blacklisted_Time as blacklisted_time_ms,
                       last_played, NULL as image_url, '' as artists, '' as album_title
                FROM Songs
                WHERE flag = 1
                ORDER BY last_played DESC, S_Listens DESC
            """)
        elif has_image_url:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       S_Blacklisted_Listens as blacklisted_listens, S_Blacklisted_Time as blacklisted_time_ms,
                       NULL as last_played, image_url, '' as artists, '' as album_title
                FROM Songs
                WHERE flag = 1
                ORDER BY S_Listens DESC
            """)
        else:
            cursor.execute("""
                SELECT S_ID as id, S_Title as title, S_Length as length_ms, 
                       S_Listens as listen_count, S_Listen_Time as listen_time_ms,
                       S_Blacklisted_Listens as blacklisted_listens, S_Blacklisted_Time as blacklisted_time_ms,
                       NULL as last_played, NULL as image_url, '' as artists, '' as album_title
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
    """Retrieve all artists from the database, excluding those with only blacklisted listens"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if image_url column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Artists' 
            AND COLUMN_NAME = 'image_url'
        """)
        has_image_url = cursor.fetchone()['COUNT(*)'] > 0
        
        # Filter out artists with zero non-blacklisted listens
        if has_image_url:
            cursor.execute("""
                SELECT a.A_ID as id, a.A_Name as name, a.A_Listens as listens, 
                       a.A_ListenTime as listen_time_ms, a.A_Blacklisted_Listens as blacklisted_listens,
                       a.A_Blacklisted_Time as blacklisted_time_ms, a.image_url
                FROM Artists a
                WHERE a.flag = 1 AND a.A_Listens > 0
                ORDER BY a.A_Listens DESC
            """)
        else:
            cursor.execute("""
                SELECT a.A_ID as id, a.A_Name as name, a.A_Listens as listens, 
                       a.A_ListenTime as listen_time_ms, a.A_Blacklisted_Listens as blacklisted_listens,
                       a.A_Blacklisted_Time as blacklisted_time_ms, NULL as image_url
                FROM Artists a
                WHERE a.flag = 1 AND a.A_Listens > 0
                ORDER BY a.A_Listens DESC
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
    """Retrieve all albums from the database, excluding those with only blacklisted listens"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if image_url column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'spotifyDatabase' 
            AND TABLE_NAME = 'Albums' 
            AND COLUMN_NAME = 'image_url'
        """)
        has_image_url = cursor.fetchone()['COUNT(*)'] > 0
        
        # Filter out albums with zero non-blacklisted listens (checking A_Listen_Time since A_Listens is for complete album plays)
        if has_image_url:
            cursor.execute("""
                SELECT al.A_ID as id, al.A_Title as title, al.A_Listen_Time as listen_time_ms, 
                       al.A_Listens as listens, al.A_Length as length_ms, al.A_Blacklisted_Listens as blacklisted_listens,
                       al.A_Blacklisted_Time as blacklisted_time_ms, al.image_url
                FROM Albums al
                WHERE al.flag = 1 AND al.A_Listen_Time > 0
                ORDER BY al.A_Listens DESC
            """)
        else:
            cursor.execute("""
                SELECT al.A_ID as id, al.A_Title as title, al.A_Listen_Time as listen_time_ms, 
                       al.A_Listens as listens, al.A_Length as length_ms, al.A_Blacklisted_Listens as blacklisted_listens,
                       al.A_Blacklisted_Time as blacklisted_time_ms, NULL as image_url
                FROM Albums al
                WHERE al.flag = 1 AND al.A_Listen_Time > 0
                ORDER BY al.A_Listens DESC
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

def get_blacklist():
    """Get the blacklist from persistent storage"""
    try:
        if os.path.exists('blacklist.json'):
            with open('blacklist.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading blacklist: {e}")
    return []

def save_blacklist(blacklist):
    """Save the blacklist to persistent storage"""
    try:
        with open('blacklist.json', 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving blacklist: {e}")

def add_to_blacklist(playlist_id, playlist_name, image_url=None):
    """Add a playlist to the blacklist"""
    blacklist = get_blacklist()
    # Avoid duplicates
    if not any(p['id'] == playlist_id for p in blacklist):
        blacklist.append({
            'id': playlist_id,
            'name': playlist_name,
            'image_url': image_url
        })
        save_blacklist(blacklist)
        return True
    return False

def remove_from_blacklist(playlist_id):
    """Remove a playlist from the blacklist"""
    blacklist = get_blacklist()
    blacklist = [p for p in blacklist if p['id'] != playlist_id]
    save_blacklist(blacklist)
    return True

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

