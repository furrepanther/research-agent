# GUI Features Guide

## Overview

The Research Agent GUI provides a user-friendly interface for running the paper collection agent with full control over modes, monitoring, and data management.

## New Features

### 1. Mode Selection Dropdown

**Location**: Below the log area, above the control buttons

**Options**:
- **Automatic** (default): Automatically detects mode based on database state
  - Empty database → BACKFILL mode
  - Existing papers → DAILY mode
- **Test**: Count-only mode. Fetches paper counts but **skips all downloads and database updates**.
- **Backfill**: Forces a full historical retrieval from early 2000s.

**How to Use**:
1. Select desired mode from dropdown before starting
2. Click "Start Agent"
3. The window title will show which mode is active

### 2. System Backup

**Location**: Teal "Backup" button in control panel

**What Gets Backed Up**:
The backup system creates a compressed **ZIP archive** containing:
- `metadata.db` - The SQLite database
- `R:/MyDrive/03 Research Papers/` - All papers currently in your cloud library
- `config.yaml` - Your system configuration

**Backup Process**:
1. Click the teal "Backup" button.
2. The agent will use the default backup path configured in Settings.
3. If no path is configured, you will be prompted to select one.
4. A ZIP file is created: `research_backup_YYYYMMDD_HHMMSS.zip`.
5. Progress is shown in the status bar at bottom.

**Safety Features**:
- Cannot backup while agent is running.
- ZIP compression reduces cloud storage footprint.
- Includes both metadata and PDF files in a single portable archive.

## Progress Tracking

### BACKFILL Mode
- Opens a dedicated Progress Window.
- Shows real-time stats per source:
  - Papers found.
  - Progress percentage.
  - Details: **"Found: X, Filtered: Y"**.
- Overall progress bar across all sources.

### Test Mode
- Performs real-time filtering and reports counts.
- **No files are downloaded** and the database is not modified.
- Useful for validating search query volume before a full run.

## Control Buttons

### Start Agent
- **Color**: Green
- **Function**: Starts the research agent with selected mode.

### Cancel Run
- **Color**: Red
- **Function**: Stops all workers and cancels current run.
- **Shows**: "Stopping..." during shutdown.

### Settings
- **Color**: Dark Gray
- **Function**: Opens settings dialog with tabs:
  - **General**: Storage and Staging paths.
  - **Search**: Limits and Batch sizes.
  - **Prompts**: Core search query and excluded terms.
  - **Paths**: Cloud storage and Backup directory configuration.

### Backup
- **Color**: Teal
- **Function**: Creates a ZIP backup of your entire system.

## Status Indicators

### Status Bar (Bottom)
- Shows current operation status (e.g., "Transferring to Cloud...").
- Updates in real-time during runs.
- Final messages: "Finished." or "Cancelled by user."

### Log Area
- Scrollable text area with real-time logs
- Shows:
  - Worker progress
  - Papers found/filtered
  - Download status
  - Errors and warnings
  - Backup operations

## Keyboard Shortcuts

- **Enter**: Start agent (when not running)
- **Escape**: Cancel run (when running) or close window (when idle)

## Window Features

- **Resizable**: Minimum 600x400, default 800x600
- **Centered**: Automatically centered on screen at launch
- **Title Updates**: Shows current mode (TESTING/DAILY/BACKFILL)
- **Multiple Windows**:
  - Main GUI window (always)
  - Progress Window (BACKFILL mode only)
  - Summary Window (after completion, shows collected papers)
  - Settings Dialog (when opened)

## Best Practices

### When to Use Each Mode

**TESTING Mode**:
- Testing new search prompts
- Verifying configuration changes
- Quick sanity checks
- Development/debugging

**DAILY Mode**:
- Regular scheduled updates
- Incremental paper collection
- After initial BACKFILL is complete

**BACKFILL Mode**:
- First-time setup
- Historical paper collection
- Recovering from database issues
- Large-scale collection projects

### Backup Recommendations

**Before**:
- Major configuration changes
- Running BACKFILL mode on large date ranges
- Testing new search prompts
- Software updates

**Frequency**:
- Weekly: If running DAILY mode regularly
- After each BACKFILL: To preserve new collections
- Before database maintenance: Migrations, cleanup, etc.

**What to Backup**:
- Always: Database file (quick, small)
- Periodically: Papers directory (slower, large)
- Critical: Config and prompt files (your custom settings)

### Working with Backups

**Restoring from Backup**:
```bash
# Stop the agent first!
# Then copy files back:
copy backup_folder\metadata.db data\metadata.db
copy backup_folder\config.yaml config.yaml
copy backup_folder\prompt.txt prompt.txt
xcopy /E /I backup_folder\papers data\papers
```

**Backup Storage Tips**:
- Store on different drive than working directory
- Keep at least 2-3 recent backups
- Compress old backups to save space
- Label backups with purpose (e.g., "before_prompt_change")

## Troubleshooting

### "Workers already running"
- Wait for current run to complete, or
- Click "Cancel Run" and wait for shutdown

### Backup Fails
- Check target directory has write permissions
- Ensure enough disk space for papers directory
- Close any programs accessing the database

### Mode Selection Doesn't Change
- Mode is determined when clicking "Start Agent"
- Change dropdown BEFORE starting
- Window title updates after start to show active mode

### Progress Window Doesn't Appear
- Only appears in BACKFILL mode
- Check mode selection before starting
- If using Auto mode, ensure database is empty or select BACKFILL manually

## Tips & Tricks

1. **Quick Test**: Use TESTING mode with "Auto" to test prompt changes
2. **Safe Experimentation**: Backup before trying new configurations
3. **Monitor Progress**: Watch log area for detailed real-time updates
4. **Scheduled Runs**: Use DAILY mode for consistent incremental updates
5. **Large Collections**: Use BACKFILL mode with backups at intervals
6. **Disk Space**: Before backing up papers directory, check available space
7. **Mode Override**: Use manual mode selection to override auto-detection
