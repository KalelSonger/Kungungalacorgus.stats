# Kungungalacorgus.stats Setup Instructions

A Spotify listening statistics tracker with blacklist functionality.

**Note**: This application comes pre-configured with Spotify API credentials and ngrok settings. You only need to set up the database and run the application.

## Prerequisites

- **Python 3.10+** - Download from https://www.python.org/downloads/
- **MySQL Server 8.0+** - Download from https://dev.mysql.com/downloads/installer/
- **Spotify Account** - Free or Premium (login required to use the app)

## Installation Steps

### 1. Install MySQL Server

#### Windows
1. Download MySQL Installer from https://dev.mysql.com/downloads/installer/
2. Run the installer and select "MySQL Server"
3. Set a root password during configuration (remember this!)
4. Start MySQL Server from Windows Services

#### MacOS
```bash
brew install mysql
brew services start mysql
mysql_secure_installation  # Follow prompts to set root password
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo mysql_secure_installation  # Follow prompts to set root password
```

### 2. Create the Database

### 2. Configure MySQL Root Password

The application will automatically create the database and user when it first runs. You just need to provide your MySQL root password.

Edit the `.env` file and set your MySQL root password:

```env
DB_PASSWORD=your_mysql_root_password_here
```

**That's it!** The database will be created automatically on first run.

#### (Optional) Manual Database Setup

If you prefer to create the database manually, or if automatic creation fails:

Login to MySQL with your root password:

```bash
mysql -u root -p
```

Run these commands in the MySQL prompt:

```sql
CREATE DATABASE spotifyDatabase;
CREATE USER 'spotify_user'@'localhost' IDENTIFIED BY 'Spotify123!';
GRANT ALL PRIVILEGES ON spotifyDatabase.* TO 'spotify_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Then import the schema:

```bash
mysql -u root -p spotifyDatabase < Stats.sql
```

If you do manual setup, update `.env` to use `spotify_user` instead of `root`:
```env
DB_USER=spotify_user
DB_PASSWORD=Spotify123!
```

### 3. Install Python Dependencies

The application requires a virtual environment with specific packages.

#### Windows
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### MacOS/Linux
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Verify Configuration

The `.env` file is already configured with:
- **Spotify API credentials** (no setup needed)
- **ngrok domain and authtoken** (pre-configured)
- **Database settings** (default: `spotify_user` / `Spotify123!`)

**Only edit `.env` if you changed the database password in Step 2.**

## Running the Application

### Option 1: Using the Convenience Script (Windows)

```powershell
.\run.ps1
```

This script:
- Sets UTF-8 encoding for proper character display
- Starts Flask server
- Automatically stops when you press Ctrl+C

### Option 2: Running Directly

#### Windows
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run the app
python main.py
```

#### MacOS/Linux
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the app
python3 main.py
```

### What Happens When You Run

The application will:
1. Connect to MySQL database
2. Auto-create tables if they don't exist
3. Start ngrok tunnel at https://easily-crankier-coleman.ngrok-free.dev
4. Start Flask server on port 5000
5. Begin background sync (every 2 minutes)

You'll see output like:
```
Connected to database successfully (8 tables found)
ngrok tunnel started successfully
   App available at: https://easily-crankier-coleman.ngrok-free.dev
 * Running on http://127.0.0.1:5000
```

### Accessing the Application

Open your browser and visit:
```
https://easily-crankier-coleman.ngrok-free.dev
```

**From any device** (phone, tablet, another computer):
- The ngrok URL works from anywhere with internet
- No port forwarding or firewall configuration needed

### First Time Login

1. Click **"Login with Spotify"**
2. Authorize the app to access your Spotify data
3. You'll be redirected back to the dashboard
4. The app starts tracking your listening history automatically

## Using the Application

### Statistics Tab
- View all tracked songs with play counts and listening time
- Toggle "Show Blacklisted Listens" to see/hide blacklisted data
- Click "Sync Songs" to manually fetch recent tracks

### Top Songs/Artists/Albums Tabs
- View your most-played content
- Toggle "Show Blacklisted" to display blacklisted statistics
- Only shows items with at least 1 regular (non-blacklisted) play

### Blacklist Tab
- Add playlists you want to exclude from regular statistics
- Paste Spotify playlist URL: `https://open.spotify.com/playlist/...`
- Or Spotify URI: `spotify:playlist:...`
- Remove playlists by clicking the red X

### How Blacklisting Works
- Songs played from blacklisted playlists are tracked separately
- **Regular stats**: Music from albums, non-blacklisted playlists
- **Blacklisted stats**: Music from blacklisted playlists only
- Use for study playlists, sleep music, etc. that skew your real preferences

## Stopping the Application

Press **Ctrl+C** in the terminal where the app is running.

The app will automatically:
- Stop the Flask server
- Close the ngrok tunnel
- Save all data to the database

## Resetting Your Data

To clear all statistics and start fresh:

```bash
# Windows
.\.venv\Scripts\python.exe clear_database.py

# MacOS/Linux
.venv/bin/python clear_database.py
```

This will delete all songs, artists, albums, and relationships from the database.

## Troubleshooting

### "Can't connect to database"
- Verify MySQL is running
- Check that `spotifyDatabase` exists: `mysql -u root -p -e "SHOW DATABASES;"`
- Verify password in `.env` matches what you set in Step 2

### "Port 5000 already in use"
- Another application is using port 5000
- Stop the other application or modify the port in `main.py`
- Look for `app.run(port=5000)` and change to another port

### "Module not found" errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check that you're using the correct Python version (3.10+)

### "ngrok authentication failed"
- The ngrok authtoken is pre-configured in `.env`
- If you see this error, verify `.env` file exists and contains `NGROK_AUTHTOKEN`

### Songs not appearing after listening
- Wait 2 minutes for the automatic background sync
- Or click "Sync Songs" button in the Statistics tab
- Check terminal output for error messages

### Blacklist not working
- Only playlist-based plays can be blacklisted
- Playing from album/artist page won't trigger blacklist
- Must play from the actual playlist you blacklisted

### Website shows "502 Bad Gateway"
- Make sure `python main.py` is still running
- Check terminal for error messages
- Restart the application

## Technical Details

### Background Sync
- Runs every 2 minutes automatically
- Fetches up to 50 most recent tracks
- Only processes new tracks (no duplicates)
- Uses `last_sync.txt` to track last sync time

### Database Structure
- **Songs**: Track ID, title, length, play counts, times
- **Artists**: Artist ID, name, play counts, times  
- **Albums**: Album ID, title, release year, play counts, times
- **Blacklist columns**: Separate counters for blacklisted plays

### Pre-configured Settings
- **Spotify Client ID**: 2a061e08a3f94fd68b36a41fc9922a3b
- **ngrok Domain**: easily-crankier-coleman.ngrok-free.dev
- **Database**: spotifyDatabase (user: spotify_user)

These are ready to use - no additional configuration needed.

## System Requirements

- **RAM**: 512 MB minimum
- **Disk Space**: 100 MB for application + database storage
- **Internet**: Required for Spotify API and ngrok tunnel
- **Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

## Support

If you encounter issues:
1. Check the Troubleshooting section above
2. Review terminal output for error messages
3. Verify all prerequisites are installed
4. Ensure `.env` file exists with correct settings
