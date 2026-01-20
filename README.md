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
- Gmail account (for auto-import feature)

## Setup

1. Build the solution in Visual Studio or run `Build.bat`
2. For Gmail sync, add your OAuth credentials to `gmail-mcp/gcp-oauth.keys.json`
3. Run the app and click "Sync Gmail" to import applications

## Tech Stack

- WinUI 3 / Windows App SDK
- C# / .NET 8
- Python (Gmail extraction script)
