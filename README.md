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
- **Public Access**: Accessible via ngrok tunnel from any device
- **Persistent Storage**: MySQL database for reliable data retention

## Prerequisites

- Python 3.10 or higher
- MySQL Server 8.0 or higher
- Spotify account (free or premium)

## Quick Start

See [SETUP.md](SETUP.md) for complete installation instructions.

**TL;DR:**
1. Install MySQL and create `spotifyDatabase`
2. Configure `.env` file with database password
3. Run `python main.py` (or `.\run.ps1` on Windows)
4. Visit the ngrok URL and login with Spotify

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

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL 8.0+
- **Authentication**: Spotify OAuth 2.0
- **Scheduling**: APScheduler (background sync)
- **Tunneling**: ngrok (public access)
- **Frontend**: HTML/CSS/JavaScript

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

## Documentation

- [SETUP.md](SETUP.md) - Installation and setup guide

## Authors

Kalel Songer
