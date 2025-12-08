"""Quick test to check if image URLs are in the database"""
from database import get_all_songs, get_all_artists, get_all_albums

print("\n=== Testing Song Images ===")
songs = get_all_songs()[:3]
for song in songs:
    print(f"Song: {song['title']}")
    print(f"  image_url: {song.get('image_url', 'KEY NOT FOUND')}")
    print()

print("\n=== Testing Artist Images ===")
artists = get_all_artists()[:3]
for artist in artists:
    print(f"Artist: {artist['name']}")
    print(f"  image_url: {artist.get('image_url', 'KEY NOT FOUND')}")
    print()

print("\n=== Testing Album Images ===")
albums = get_all_albums()[:3]
for album in albums:
    print(f"Album: {album['title']}")
    print(f"  image_url: {album.get('image_url', 'KEY NOT FOUND')}")
    print()
