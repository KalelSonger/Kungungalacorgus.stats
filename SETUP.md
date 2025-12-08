# Kungungalacorgus.stats Setup Instructions

A Spotify listening statistics tracker with blacklist functionality for filtering out specific playlists from your stats.

## Features
- Track song, artist, and album listen counts and total listening time
- Automatic background sync every 2 minutes
- Blacklist system to exclude specific playlists from statistics
- View top songs, artists, and albums
- Toggle visibility of blacklisted statistics
- Public access via ngrok tunnel

## Prerequisites
- Python 3.10+
- MySQL Server 8.0+
- ngrok account (free tier works)
- Spotify account
- Git (optional, for cloning)

## Installation

### 1. Install MySQL Server

#### Windows
- Download MySQL Installer from: https://dev.mysql.com/downloads/installer/
- Run the installer and select "MySQL Server" during setup
- During configuration, set a root password (you'll need this later)
- Start MySQL Server from Windows Services

#### MacOS
```bash
brew install mysql
brew services start mysql
# Secure your installation
mysql_secure_installation
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
# Secure your installation
sudo mysql_secure_installation
```

### 2. Configure MySQL Database

After installing MySQL, create the database:

```bash
# Login to MySQL (use your root password)
mysql -u root -p
```

Then run these commands in the MySQL shell:

```sql
CREATE DATABASE spotifyDatabase;
CREATE USER 'spotify_user'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON spotifyDatabase.* TO 'spotify_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Then import the database schema:

```bash
mysql -u root -p spotifyDatabase < Stats.sql
```

### 3. Set Up Python Virtual Environment

**Windows:**
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**MacOS/Linux:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Spotify API Credentials (from https://developer.spotify.com/dashboard)
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=https://your-ngrok-domain.ngrok-free.app/callback

# ngrok Configuration (from https://dashboard.ngrok.com)
NGROK_AUTHTOKEN=your_ngrok_authtoken
NGROK_DOMAIN=your-ngrok-domain.ngrok-free.app

# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=spotify_user
DB_PASSWORD=your_password_here
DB_NAME=spotifyDatabase
```

### 5. Install and Configure ngrok

#### Windows
**Install ngrok:**
```powershell
winget install ngrok
# Or download from https://ngrok.com/download
```

**Configure ngrok with your authtoken:**
```powershell
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

#### MacOS
**Install ngrok:**
```bash
brew install ngrok
```

**Configure ngrok:**
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

#### Linux
**Install ngrok:**
```bash
# Download from https://ngrok.com/download
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

**Configure ngrok:**
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

### 6. Set Up Spotify Developer App

1. Go to https://developer.spotify.com/dashboard
2. Click "Create an App"
3. Fill in app name and description
4. Note your **Client ID** and **Client Secret**
5. Click "Edit Settings"
6. Add your ngrok URL to **Redirect URIs**: `https://your-domain.ngrok-free.app/callback`
7. Save settings
8. Update your `.env` file with these credentials

## Running the Application

### Windows
```powershell
# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Run the app
python main.py

# Or use the convenience script
.\run.ps1
```

### MacOS/Linux
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run the app
python3 main.py
```

The app will:
1. Initialize MySQL database tables automatically
2. Start ngrok tunnel on your configured domain
3. Start Flask server on port 5000
4. Begin background sync (checks every 2 minutes)

### Access the App

Visit your ngrok URL in a browser:
```
https://your-domain.ngrok-free.app
```

Click "Login with Spotify" to authenticate and start tracking your listening statistics.

## Using the Blacklist Feature

The blacklist allows you to exclude specific playlists from your statistics tracking.

### Adding Playlists to Blacklist

1. Navigate to the **Blacklist** tab in the app
2. Paste a Spotify playlist URL or URI:
   - URL format: `https://open.spotify.com/playlist/PLAYLIST_ID`
   - URI format: `spotify:playlist:PLAYLIST_ID`
3. Click "Add to Blacklist"
4. The playlist will appear in your blacklist

### How Blacklisting Works

- Songs played from blacklisted playlists are tracked separately
- **Regular listens/time**: Songs played from albums, non-blacklisted playlists, etc.
- **Blacklisted listens/time**: Songs played from blacklisted playlists
- Top tabs (Songs, Artists, Albums) only show items with regular listens > 0
- Use the "Show Blacklisted" toggle to view blacklisted statistics

### Viewing Blacklisted Stats

In the **Top Songs**, **Top Artists**, and **Top Albums** tabs:
- Toggle "Show Blacklisted" to reveal blacklisted listens and time
- All three toggles are synchronized
- Toggle state persists across page reloads

In the **Statistics** tab:
- Use the "Show Blacklisted Listens" toggle to show/hide blacklisted columns
- View comprehensive statistics for all tracked songs

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running: `mysql -u root -p`
- Check credentials in `.env` file match your MySQL setup
- Ensure database `spotifyDatabase` exists

### ngrok Connection Failed
- Run: `ngrok config add-authtoken YOUR_AUTHTOKEN`
- Check if port 5000 is already in use
- Verify ngrok domain in `.env` matches your ngrok account

### Spotify Authentication Error
- Verify CLIENT_ID and CLIENT_SECRET in `.env`
- Check Redirect URI in Spotify Dashboard matches your ngrok URL exactly
- Ensure ngrok tunnel is running before attempting login

### Background Sync Not Working
- Check Flask terminal output for error messages
- Verify Spotify token hasn't expired (re-login if needed)
- Look for "Background sync job started..." messages every 2 minutes

### Module Not Found Errors
- Ensure virtual environment is activated
- Run: `pip install -r requirements.txt`
- Try: `pip install --upgrade pip`

### Port 5000 Already in Use
- Stop other Flask applications
- Or modify port in `main.py`: `app.run(host='0.0.0.0', port=XXXX, debug=True)`

### Blacklist Not Tracking Correctly
- Clear database and resync: `python clear_database.py`
- Remove sync timestamp: `del last_sync.txt` (Windows) or `rm last_sync.txt` (Unix)
- Restart the app and click "Sync Songs"
- Only playlist-based plays can be blacklisted (not album/artist plays)

## Application Structure

```
Kungungalacorgus.stats/
├── main.py                 # Flask application with Spotify OAuth and UI
├── database.py            # MySQL database abstraction layer
├── requirements.txt       # Python dependencies
├── SETUP.md              # This file
├── Stats.sql             # Database schema
├── clear_database.py     # Utility to reset database
├── run.ps1              # Windows convenience script
├── .env                 # Environment variables (create from .env.example)
├── .env.example         # Template for environment configuration
├── blacklist.json       # Blacklisted playlist storage
├── spotify_token.json   # Cached Spotify OAuth tokens
├── last_sync.txt        # Last sync timestamp
└── .venv/              # Python virtual environment
```

## Advanced Features

### Manual Sync
- Click "Sync Songs" button in the Statistics tab
- Specify limit (1-50) for number of recent tracks to fetch
- Useful after adding new playlists to blacklist

### Background Sync
- Runs automatically every 2 minutes
- Only processes new tracks (no duplicates)
- Uses `last_sync.txt` to track last sync timestamp

### Database Management
- Clear all data: `python clear_database.py`
- Database auto-creates tables on first run
- Schema automatically updates when new columns are needed

## Security Notes

- Never commit `.env` file to version control
- Keep `spotify_token.json` private
- Rotate Spotify Client Secret if exposed
- Use ngrok's free tier only for development/personal use

## Support

For issues or questions:
- Check the Troubleshooting section above
- Review Flask terminal output for error messages
- Verify all prerequisites are installed correctly
- Ensure `.env` file is properly configured
