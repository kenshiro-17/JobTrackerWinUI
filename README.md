# JobTrackerWinUI

Windows desktop application for tracking job applications locally, with optional Gmail sync to detect confirmations, interviews, rejections, and offers.

The project is built for people who want a personal job-application tracker without moving inbox data into a hosted SaaS tool. Application data stays local, and Gmail access is delegated through the user's own Google Cloud OAuth credentials.

## Core Features

- Track applications by company, role, status, and timeline
- Search and filter application history
- Sync Gmail to import job-related emails automatically
- Detect common application states from email content
- Store application records locally on the machine
- Build distributable Windows installers from the repo

## Tech Stack

- WinUI 3 / Windows App SDK
- C# / .NET 8
- Python for Gmail extraction
- Gmail API with user-owned OAuth credentials
- Inno Setup for installer packaging

## Repository Layout

```text
App.xaml / MainWindow.xaml      # App shell
Views/                          # Main application views
Models/                         # Job application models
Services/                       # Application services
Converters/                     # UI converters
gmail_job_extractor.py          # Gmail sync pipeline
gmail-mcp/                      # Local OAuth credential support
Build.bat                       # Build + publish + installer flow
JobTrackerInstaller.iss         # Inno Setup installer script
```

## Prerequisites

- Windows 10 or 11
- .NET 8 SDK
- Python 3.10+
- A Gmail account if you want inbox sync
- Visual Studio or the .NET CLI for local builds

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/kenshiro-17/JobTrackerWinUI.git
cd JobTrackerWinUI
```

### 2. Build the app

```bash
Build.bat
```

You can also open the solution in Visual Studio and build from there.

## Gmail Sync Setup

Gmail sync is optional. The repo intentionally requires you to use your own Google Cloud credentials so inbox access stays under your control.

### 1. Create OAuth credentials in Google Cloud

- create or select a Google Cloud project
- enable the Gmail API
- create an OAuth client ID for a desktop app
- download the JSON credentials file
- configure the OAuth consent screen
- add yourself as a test user if needed

### 2. Place credentials in the expected folder

Expected structure:

```text
JobTrackerWinUI/
  gmail-mcp/
    gcp-oauth.keys.json
```

### 3. Run the sync flow

- launch the app
- click `Sync Gmail`
- complete the browser OAuth flow on first run
- allow the app to scan recent job-related emails

## How Gmail Sync Works

The extractor scans for patterns such as:

- application confirmations
- interview invitations
- rejection messages
- offer-related email content

The processing happens locally via `gmail_job_extractor.py`. Your mailbox contents are not routed through a custom backend owned by this project.

## Build and Packaging

`Build.bat` does more than a simple compile. It handles:

- release build
- self-contained publish output
- distribution folder preparation
- copying Python sync assets
- installer generation through Inno Setup

Related files:

- `Build.bat`
- `JobTrackerInstaller.iss`
- `Properties/PublishProfiles/`

## Verification

Basic checks after setup:

- app launches successfully
- you can add and edit an application manually
- Gmail sync opens the OAuth browser flow
- synced emails create local entries
- filters and search update the displayed list correctly

## Troubleshooting

### `Credentials file not found`

Make sure `gcp-oauth.keys.json` is present under `gmail-mcp/`.

### OAuth screen says the request is invalid or blocked

Check that:

- Gmail API is enabled
- the OAuth client type is `Desktop app`
- your account is added as a test user when required

### No emails are detected

The current extraction logic focuses on recent job-related emails and common recruiting patterns. Make sure relevant emails exist in the scanned time window.

### Python script does not launch from the app

Confirm Python is installed and available on PATH, since the WinUI app starts `gmail_job_extractor.py` as a subprocess.

## Why This Repo Is Useful

Most job trackers stop at CRUD. This one adds practical inbox automation while preserving a local-only data model. That combination is what makes it relevant for privacy-conscious personal use.

## License

Add the preferred project license here if you want reuse terms to be explicit.
