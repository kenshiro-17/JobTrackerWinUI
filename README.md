# JobTracker

A Windows app to track job applications. Automatically syncs with Gmail to detect application emails and track their status.

## Features

- Track job applications with company, position, status, and dates
- Auto-import from Gmail (detects application confirmations, rejections, interviews)
- Filter and search applications
- Local storage (no cloud required)

## Requirements

- Windows 10/11
- .NET 8.0
- Python 3.10+ (for Gmail sync)
- Gmail account (for auto-import feature)

## Setup

### 1. Build the App

Build in Visual Studio or run:
```
Build.bat
```

### 2. Set Up Gmail Sync (Optional)

To use the Gmail auto-import feature, you'll need to create your own Google Cloud OAuth credentials. This keeps your data private - the app only runs locally on your machine.

#### Create Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and click Enable
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Name it whatever you want (e.g., "JobTracker")
   - Click Create
5. Download the credentials:
   - Click the download icon next to your new credential
   - Save the file as `gcp-oauth.keys.json`
6. Configure OAuth consent screen:
   - Go to "OAuth consent screen"
   - Select "External" and click Create
   - Fill in the required fields (app name, support email)
   - Add your email as a test user
   - Save

#### Add Credentials to JobTracker

1. Create a folder called `gmail-mcp` in the app directory
2. Move `gcp-oauth.keys.json` into that folder

Your folder structure should look like:
```
JobTrackerWinUI/
  gmail-mcp/
    gcp-oauth.keys.json
  ...
```

### 3. Run the App

1. Launch JobTracker
2. Click "Sync Gmail" to import job applications
3. On first run, a browser window will open asking you to sign in to your Google account
4. Grant permission to read your emails
5. The app will scan for job-related emails and import them

## How It Works

The Gmail sync scans your inbox for common job application patterns:
- Application confirmations ("Thank you for applying")
- Interview invitations
- Rejection emails
- Offer letters

All processing happens locally. Your emails are never sent to any external server.

## Tech Stack

- WinUI 3 / Windows App SDK
- C# / .NET 8
- Python (Gmail extraction script)
- Google Gmail API

## Troubleshooting

**"Credentials file not found"**
Make sure `gcp-oauth.keys.json` is in the `gmail-mcp` folder.

**"Access blocked: This app's request is invalid"**
Make sure you added your email as a test user in the OAuth consent screen.

**Gmail sync not finding emails**
The scanner looks for emails from the last 90 days by default. Check that you have job-related emails in that timeframe.
