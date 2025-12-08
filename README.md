# Kungungalacorgus.stats

A Spotify listening statistics tracker with intelligent blacklist filtering.

## Overview

Kungungalacorgus.stats is a Flask-based web application that tracks and visualizes your Spotify listening history. It features a unique blacklist system that allows you to exclude specific playlists from your statistics, giving you accurate insights into your actual music preferences vs. background listening.

## Key Features

- **Automatic Tracking**: Background sync every 2 minutes to capture all your listening activity
- **Blacklist System**: Exclude specific playlists (study music, sleep playlists, etc.) from your statistics
- **Separate Counters**: Track both regular and blacklisted listens independently
- **Top Charts**: View your most played songs, artists, and albums
- **Time Tracking**: Monitor total listening time for songs, artists, and albums
- **Toggle Visibility**: Show or hide blacklisted statistics on demand
- **Public Access**: Share your stats via ngrok tunnel
- **Persistent Storage**: MySQL database for reliable data retention

## Quick Start

1. **Install Prerequisites**
   - Python 3.10+
   - MySQL Server 8.0+
   - ngrok account

2. **Set Up Database**
   ```bash
   mysql -u root -p
   CREATE DATABASE spotifyDatabase;
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Install Dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or: source .venv/bin/activate  # Unix
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```

6. **Access via Browser**
   - Visit your ngrok URL
   - Login with Spotify
   - Start tracking!

## Blacklist Feature

### Why Use Blacklisting?

Do you listen to:
- Study/focus playlists while working?
- Sleep music overnight?
- Background ambient music?
- Kids' music for your children?

These can skew your "real" listening statistics. The blacklist feature lets you track these separately, so your Top Songs actually reflect your music taste, not your study playlist.

### How It Works

1. Navigate to the **Blacklist** tab
2. Add any Spotify playlist URL or URI
3. Songs from blacklisted playlists increment separate counters:
   - **Regular listens/time**: Your actual music
   - **Blacklisted listens/time**: Background/utility listening
4. Toggle visibility in any tab to show/hide blacklisted stats

## Project Structure

```
├── main.py              # Flask app with Spotify OAuth
├── database.py          # MySQL database layer
├── clear_database.py    # Database reset utility
├── requirements.txt     # Python dependencies
├── SETUP.md            # Detailed setup instructions
├── Stats.sql           # Database schema
├── run.ps1             # Windows convenience script
├── blacklist.json      # Blacklisted playlist storage
└── .env                # Environment configuration
```

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL 8.0+
- **Authentication**: Spotify OAuth 2.0
- **Scheduling**: APScheduler (background sync)
- **Tunneling**: ngrok (public access)
- **Frontend**: HTML/CSS/JavaScript (embedded)

## Documentation

- [SETUP.md](SETUP.md) - Complete installation and configuration guide
- [Stats.sql](Stats.sql) - Database schema and structure

## Screenshots

### Statistics Dashboard
View all your tracked songs with listen counts and total time played.

### Top Songs/Artists/Albums
Discover your most-played content with sortable charts.

### Blacklist Management
Easily add or remove playlists from your blacklist.

## Contributing

This is a personal project, but suggestions and bug reports are welcome via issues.

## License

MIT License - See LICENSE file for details

## Author

KalelSonger

## Acknowledgments

- Spotify Web API for providing comprehensive music data
- ngrok for easy public access tunneling
- Flask community for excellent documentation
