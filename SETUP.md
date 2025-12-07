# Kungungalacorgus.stats Setup Instructions

## Prerequisites
- Python 3.10+
- ngrok
- Git (optional, for cloning)

## Installation

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install and Configure ngrok

**Install ngrok:**
- Download from https://ngrok.com/download or use a package manager

**Configure ngrok with the authtoken:**
```bash
ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz
```

This must be done once per machine. This allows the app to use the reserved ngrok domain for a consistent redirect URI.

### 3. Run the App

```bash
python main.py
```

The app will:
- Automatically start ngrok tunnel on `https://easily-crankier-coleman.ngrok-free.dev`
- Start the Flask server on `http://localhost:5000`
- Print "✓ ngrok tunnel started successfully" when ready

### 4. Access the App

Visit in your browser:
```
https://easily-crankier-coleman.ngrok-free.dev
```

Click "Login with Spotify" to authenticate and view your 50 most recently played songs.

## Spotify Credentials

The app uses the following Spotify API credentials (already configured in the code):
- CLIENT_ID: `2a061e08a3f94fd68b36a41fc9922a3b`
- CLIENT_SECRET: `599323f77f88464fbe768772e4d4c716`
- Redirect URI: `https://easily-crankier-Coleman.ngrok-free.dev/callback`

These are pre-registered and no additional Spotify setup is needed.

## Troubleshooting

**"No web processes running" or connection refused:**
- Make sure `python main.py` is still running
- Check that ngrok started successfully (look for the "✓" message)

**ngrok says "authentication failed":**
- Run: `ngrok config add-authtoken 2vxIYJpjk30G6C6CWl6NKRT8aZx_6ZubgvFvfvquPBLbohmwz`
- Then restart the app

**Spotify redirect URI error:**
- The redirect URI should match exactly: `https://easily-crankier-coleman.ngrok-free.dev/callback`
- Check Spotify Developer Dashboard > Your App > Redirect URIs
