"""Script to clear all data from the Spotify database"""
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

print("Clearing database tables...")

# Clear tables in correct order due to foreign keys
cursor.execute("DELETE FROM Album_Song")
print("✓ Cleared Album_Song")

cursor.execute("DELETE FROM Creates")
print("✓ Cleared Creates")

cursor.execute("DELETE FROM Songs")
print("✓ Cleared Songs")

cursor.execute("DELETE FROM Artists")
print("✓ Cleared Artists")

cursor.execute("DELETE FROM Albums")
print("✓ Cleared Albums")

# Drop last_played column if it exists
try:
    cursor.execute("ALTER TABLE Songs DROP COLUMN last_played")
    print("✓ Removed last_played column")
except:
    print("✓ last_played column doesn't exist (that's fine)")

connection.commit()
cursor.close()
connection.close()

print("\n✓ Database cleared successfully!")
print("Now visit /database_values to sync fresh data from Spotify")
