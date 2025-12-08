from database import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

# Check Songs table
cursor.execute("SHOW COLUMNS FROM Songs")
songs_columns = cursor.fetchall()
print("Songs table columns:")
for col in songs_columns:
    print(f"  - {col[0]}")

# Check if image_url exists
cursor.execute("""
    SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = 'spotifyDatabase' 
    AND TABLE_NAME = 'Songs' 
    AND COLUMN_NAME = 'image_url'
""")
has_image_url = cursor.fetchone()[0] > 0
print(f"\nimage_url column exists in Songs: {has_image_url}")

# Check a sample song
cursor.execute("SELECT S_ID, S_Title, image_url FROM Songs LIMIT 3")
print("\nSample songs:")
for row in cursor.fetchall():
    print(f"  {row[1]}: image_url = {row[2]}")

cursor.close()
connection.close()
