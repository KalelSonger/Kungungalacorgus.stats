from database import get_all_songs

songs = get_all_songs()
print(f"Total songs: {len(songs)}")
print(f"\nFirst song:")
if songs:
    for key, value in songs[0].items():
        if key == 'image_url':
            print(f"  {key}: {value[:50] if value else 'None'}...")
        else:
            print(f"  {key}: {value}")
