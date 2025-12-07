# Kungungalacorgus.stats Setup Instructions

## Prerequisites
- Python 3.10+
- ngrok
- MySQL Server 8.0+
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

### 3. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Spotify API Credentials
CLIENT_ID=2a061e08a3f94fd68b36a41fc9922a3b
CLIENT_SECRET=599323f77f88464fbe768772e4d4c716
REDIRECT_URI=https://easily-crankier-coleman.ngrok-free.dev/callback

# ngrok Configuration
NGROK_AUTHTOKEN=2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz
NGROK_DOMAIN=easily-crankier-coleman.ngrok-free.dev

# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=spotify_user
DB_PASSWORD=your_password_here
DB_NAME=spotifyDatabase
```

### 4. Install Python Dependencies

**Windows/MacOS:**
```bash
pip install -r requirements.txt
```

**Linux:**
```bash
pip3 install -r requirements.txt
```

### 5. Install and Configure ngrok

#### Windows
**Install ngrok:**
- Download from https://ngrok.com/download
- Or use: `winget install ngrok`

**Configure ngrok with the authtoken:**
```powershell
ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz
```

#### MacOS
**Install ngrok:**
```bash
brew install ngrok
```

**Configure ngrok with the authtoken:**
```bash
ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz
```

#### Linux
**Install ngrok:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ngrok

# Or download from https://ngrok.com/download
# Extract and move to PATH
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/ngrok
```

**Configure ngrok with the authtoken:**
```bash
ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz
```

This must be done once per machine. This allows the app to use the reserved ngrok domain for a consistent redirect URI.

### 6. Run the App

**Windows:**
```powershell
python main.py
```

**MacOS/Linux:**
```bash
python3 main.py
```

The app will:
1. Initialize the MySQL database tables automatically
2. Start ngrok tunnel
3. Start Flask server on port 5000
4. Begin background monitoring for new songs (checks every 30 seconds)

The app will:
- Automatically start ngrok tunnel on `https://easily-crankier-coleman.ngrok-free.dev`
- Start the Flask server on `http://0.0.0.0:5000` (accessible from any machine)
- Print "✓ ngrok tunnel started successfully" when ready

### 4. Access the App

From any computer (local or remote), visit in your browser:
```
https://easily-crankier-coleman.ngrok-free.dev
```

Click "Login with Spotify" to authenticate and view your Spotify statistics.

## Spotify Credentials

The app uses the following Spotify API credentials (already configured in the code):
- CLIENT_ID: `2a061e08a3f94fd68b36a41fc9922a3b`
- CLIENT_SECRET: `599323f77f88464fbe768772e4d4c716`
- Redirect URI: `https://easily-crankier-Coleman.ngrok-free.dev/callback`

These are pre-registered and no additional Spotify setup is needed.

## Important Notes

- **Each user needs their own Spotify account** - When logging in via the app, you authenticate with your personal Spotify account
- **The ngrok domain is shared** - All users accessing the app will go through the same ngrok tunnel to the same server
- **Sessions are isolated** - Each browser/user maintains their own session with their own Spotify data
- **The authtoken is the same for all machines** - Use the authtoken provided above on every machine that runs this app

## Troubleshooting

**"No web processes running" or connection refused:**
- Make sure `python main.py` (or `python3 main.py` on Linux/Mac) is still running
- Check that ngrok started successfully (look for the "✓" message)
- Verify the ngrok domain is accessible: visit https://easily-crankier-coleman.ngrok-free.dev

**ngrok says "authentication failed":**
- Run: `ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz`
- Then restart the app

**Spotify redirect URI error:**
- The redirect URI should match exactly: `https://easily-crankier-coleman.ngrok-free.dev/callback`
- Check Spotify Developer Dashboard > Your App > Redirect URIs
- Do not include trailing slashes

**Module not found errors (ImportError):**
- Make sure you ran `pip install -r requirements.txt` (or `pip3` on Linux/Mac)
- Try upgrading pip: `pip install --upgrade pip`

**Port 5000 already in use:**
- Close any other Flask applications running on port 5000
- Or modify the port in `main.py` at the bottom (change `app.run(host='0.0.0.0', debug=True)`)

**Permission denied when running ngrok on Linux:**
- Make sure ngrok is in your PATH: `which ngrok`
- Or run with full path: `/usr/local/bin/ngrok http 5000 --domain=easily-crankier-coleman.ngrok-free.dev`
