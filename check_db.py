"""Check database contents"""
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

connection = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'spotifyDatabase')
)

cursor = connection.cursor()

print("\n=== SONGS ===")
cursor.execute("SELECT S_ID, S_Title FROM Songs LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n=== ARTISTS ===")
cursor.execute("SELECT A_ID, A_Name FROM Artists LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n=== ALBUMS ===")
cursor.execute("SELECT A_ID, A_Title FROM Albums LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n=== CREATES (Song-Artist-Album links) ===")
cursor.execute("SELECT ART_ID, S_ID, A_ID FROM Creates LIMIT 5")
rows = cursor.fetchall()
print(f"  Total rows: {len(rows)}")
for row in rows:
    print(f"  Artist:{row[0]} -> Song:{row[1]} -> Album:{row[2]}")

print("\n=== ALBUM_SONG (Album-Song links) ===")
cursor.execute("SELECT A_ID, S_ID FROM Album_Song LIMIT 5")
rows = cursor.fetchall()
print(f"  Total rows: {len(rows)}")
for row in rows:
    print(f"  Album:{row[0]} -> Song:{row[1]}")

cursor.close()
connection.close()
