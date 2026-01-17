# Research Agent

**Intelligent Research Paper Discovery and Management System**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](test_verification.py)

---

## Overview

Research Agent is an automated system for discovering, filtering, downloading, and organizing academic research papers from multiple sources. It uses intelligent filtering to identify relevant papers while automatically excluding job postings, link aggregators, and marketing content.

### Key Features

- 🔍 **Multi-Source Search**: Simultaneously searches ArXiv, LessWrong, and AI lab publications
- ☁️ **Cloud Storage Integration**: Automatically transfers results to a "ground truth" cloud folder (e.g., Google Drive)
- 🛡️ **Absolute Data Protection**: Robust safeguards prevent accidental deletion of existing papers in cloud storage
- 🧠 **Intelligent Filtering**: Advanced content filtering with boolean query support
- 🚀 **Parallel Execution**: All sources searched concurrently using multiprocessing for maximum speed
- 🔄 **Self-Healing**: Automatic error detection, rollback, and retry
- 💾 **Smart Deduplication**: Detects and merges papers found across multiple sources and cloud storage
- 🎯 **Mode-Based Operation**: AUTOMATIC, TEST (Count-only), and BACKFILL modes
- 🖥️ **Progress Tracking**: Real-time stats and progress bars for large backfill operations
- 📦 **ZIP Backups**: Dedicated backup system with compression and cloud directory support

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Configuration](#configuration)
5. [Search Modes](#search-modes)
6. [Prompt Syntax](#prompt-syntax)
7. [Architecture](#architecture)
8. [Features](#features)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Topics](#advanced-topics)
12. [Contributing](#contributing)

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Your Search Query

Edit `prompts/prompt.txt`:
```bash
# Example
echo '("AI" OR "machine learning") AND ("safety" OR "alignment")' > prompts/prompt.txt
```

### 3. Run the Agent

**CLI (Recommended)**:
```bash
python main.py --mode TESTING
```

**GUI (Recommended)**:
```bash
# Double-click the launcher script:
run_gui.bat
```

### 4. View Results

Results are organized across staging and production storage:
- **Production (Cloud)**: `R:/MyDrive/03 Research Papers/` (Configurable)
- **Staging (Temp)**: `F:/RESTMP/` (Temporary staging area)
- **Database**: `F:/TMPRES/metadata.db` (Indexed metadata)
- **Excel Log**: `F:/Antigravity_Results/Research_Papers/research_log.xlsx`

---

## Installation

### System Requirements

**Operating System**:
- ✅ Windows 10/11
- ✅ macOS 10.15 (Catalina) or higher
- ✅ Linux (Ubuntu 20.04+, Debian 10+, or equivalent)

**Hardware**:
- **RAM**: 2GB minimum, 4GB+ recommended
- **Disk Space**:
  - 500MB for application and dependencies
  - 1GB+ recommended for paper storage
  - 5GB+ for extensive backfill operations
- **Network**: Stable internet connection required for API access

**Performance Estimates**:
- TESTING mode: ~50MB download
- DAILY mode: ~200MB download
- BACKFILL mode: 500MB - 5GB+ (depends on query scope)

---

### Prerequisites

#### Required Software

1. **Python 3.8 or higher**
   - Check version: `python --version` or `python3 --version`
   - Download from: https://www.python.org/downloads/
   - ⚠️ **Important**: During installation, check "Add Python to PATH"

2. **pip (Python package manager)**
   - Usually included with Python 3.8+
   - Check: `pip --version` or `pip3 --version`
   - If missing: `python -m ensurepip --upgrade`

3. **Git** (for cloning repository)
   - Check: `git --version`
   - Download from: https://git-scm.com/downloads
   - Alternative: Download ZIP from GitHub

#### System Dependencies

**Windows**:
- No additional dependencies required
- Microsoft Visual C++ Redistributable (usually pre-installed)

**macOS**:
- Xcode Command Line Tools (usually pre-installed)
- Install if needed: `xcode-select --install`

**Linux** (Debian/Ubuntu):
```bash
# Install system dependencies for Playwright
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```

**Linux** (Fedora/RHEL):
```bash
sudo dnf install -y \
    nss \
    nspr \
    atk \
    at-spi2-atk \
    cups-libs \
    libdrm \
    libxkbcommon \
    libXcomposite \
    libXdamage \
    libXfixes \
    libXrandr \
    mesa-libgbm \
    alsa-lib
```

#### Optional (Recommended)

- **SQLite Browser**: For viewing database contents
  - Download: https://sqlitebrowser.org/
  - Alternative: Use command-line `sqlite3`

- **Virtual Environment Support**: Included with Python 3.8+
  - Check: `python -m venv --help`

---

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/research-agent.git
   cd research-agent
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (for web scraping):
   ```bash
   playwright install chromium
   ```

5. **Configure settings**:
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your paths
   ```

6. **Create prompt file**:
   ```bash
   echo '("AI" OR "machine learning") AND ("safety")' > prompts/prompt.txt
   ```

### Verify Installation

Run these commands to verify everything is working:

**1. Check Python and Dependencies**:
```bash
# Verify Python version
python --version
# Should show: Python 3.8.x or higher

# Verify dependencies installed
pip list | grep arxiv
pip list | grep playwright
pip list | grep openpyxl
# Should show versions for each package
```

**2. Verify Playwright Browsers**:
```bash
playwright install --dry-run chromium
# Should show: chromium is already installed
```

**3. Run Quick Test**:
```bash
python test_mode_settings.py
# Expected output:
# [PASS] All three modes present in config
# [PASS] TESTING mode configured correctly
# [PASS] DAILY mode configured correctly
# [PASS] BACKFILL mode configured correctly
# [PASS] Supervisor stores search_params correctly
# ...all tests passing
```

**4. Test Run (Optional)**:
```bash
# Quick 30-second test
python main.py --mode TESTING
# Should complete without errors and download a few papers
```

**Troubleshooting Verification**:

If test fails with **"ModuleNotFoundError"**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

If test fails with **"playwright command not found"**:
```bash
# Install playwright CLI
pip install playwright
playwright install chromium
```

If test fails with **"FileNotFoundError: config.yaml"**:
```bash
# Create default config
cp config.yaml.example config.yaml
# OR manually create config.yaml from template
```

---

## Usage

### Command-Line Interface (CLI)

#### Basic Usage

```bash
# Automatic mode (detects based on database)
python main.py

# Test mode (count-only verification)
python main.py --mode TEST

# Backfill mode (full historical retrieval)
python main.py --mode BACKFILL
```

#### Advanced Options

```bash
# Custom prompt from command line
python main.py --mode TESTING --prompt '("robotics") AND ("safety")'

# Override max results (deprecated, use config.yaml instead)
python main.py --max-results 50
```

#### Auto-Detection

If no mode specified, the agent automatically chooses:
- **BACKFILL** if database is empty
- **DAILY** if database contains papers

```bash
python main.py  # Auto-detects appropriate mode
```

---

### Graphical User Interface (GUI)

#### Launch GUI

```bash
python gui.py
```

#### Features

- **Real-time progress** for each source (ArXiv, Semantic Scholar, etc.)
- **Live status updates** showing current operations
- **Cancel button** for graceful shutdown
- **Scrolling log** of all operations
- **Paper counts** per source

#### Workflow

1. Launch GUI: `python gui.py`
2. Edit `prompts/prompt.txt` with your search terms
3. Click **"Start Agent"**
4. Monitor progress in real-time
5. Click **"Cancel Run"** if needed
6. Results saved automatically when complete

---

## Configuration

### Configuration File (`config.yaml`)

```yaml
# General Settings
storage_path: "F:/Antigravity_Results/Research_Papers/data"
staging_dir: "F:/RESTMP"
db_path: "F:/TMPRES/metadata.db"

# Cloud Storage Settings
cloud_storage:
  enabled: true
  path: "R:/MyDrive/03 Research Papers"
  check_duplicates: true
  backup_enabled: true

# Mode-Specific Settings
mode_settings:
  testing:
    max_papers_per_agent: 10
    per_query_limit: 5
    respect_date_range: false

  test:
    max_papers_per_agent: 0    # Count-only mode
    per_query_limit: 100

  daily:
    max_papers_per_agent: 50
    per_query_limit: 20
    respect_date_range: true

  backfill:
    max_papers_per_agent: null # Unlimited
    per_query_limit: 10
    respect_date_range: true

# Retry and Timeout Settings
retry_settings:
  max_worker_retries: 2            # Worker restart attempts
  worker_retry_delay: 5            # Seconds between retries
  worker_timeout: 600              # Worker timeout (10 min)
  api_max_retries: 3               # API call retries
  api_base_delay: 2                # Exponential backoff base
  request_pacing_delay: 1.0        # Rate limiting delay

# Export Settings
export_dir: "."
export_filename: "research_log.xlsx"
```

### Key Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `papers_dir` | Where PDFs are saved | `data/papers` |
| `db_path` | SQLite database location | `data/metadata.db` |
| `max_papers_per_agent` | Total papers per source | Mode-dependent |
| `per_query_limit` | Papers per API call | Mode-dependent |
| `worker_timeout` | Max worker runtime | 600 seconds |

---

## Search Modes

### TESTING Mode

**Purpose**: Quick verification during development

**Characteristics**:
- Limit: 10 papers per source (40 total)
- Batch size: 5 papers per API call
- Date handling: Ignores date ranges
- Duration: ~30 seconds

**When to use**:
- Testing new search queries
- Verifying system works
- Quick sampling of results

**Example**:
```bash
python main.py --mode TESTING
```

---

### DAILY Mode

**Purpose**: Incremental updates for ongoing monitoring

**Characteristics**:
- Limit: 50 papers per source (200 total)
- Batch size: 20 papers per API call
- Date handling: Only papers after last run
- Duration: 2-5 minutes

**When to use**:
- Daily morning update
- Scheduled cron jobs
- Monitoring new publications

**Example**:
```bash
python main.py --mode DAILY
```

**Auto-selected when**: Database contains papers

---

### BACKFILL Mode

**Purpose**: Historical collection for new topics

**Characteristics**:
- Limit: **UNLIMITED** (until date range satisfied)
- Batch size: 10 papers per API call (stable)
- Date handling: Fetches back to start_date (default: 2023-01-01)
- Duration: 10+ minutes (depends on topic)

**When to use**:
- First run with new topic
- Building historical corpus
- Comprehensive literature review

**Example**:
```bash
python main.py --mode BACKFILL
```

**Auto-selected when**: Database is empty

---

## Prompt Syntax

### Boolean Query Format

Research Agent uses boolean logic for precise filtering:

```
("term1" OR "term2") AND ("term3" OR "term4") ANDNOT ("exclude1" OR "exclude2")
```

### Components

1. **Quoted Terms**: Always use quotes around search terms
   ```
   "AI safety"
   "machine learning"
   ```

2. **OR Groups**: Parentheses with OR for alternatives
   ```
   ("AI" OR "artificial intelligence" OR "machine learning")
   ```

3. **AND Logic**: Connect groups with AND
   ```
   ("AI" OR "ML") AND ("safety" OR "alignment")
   ```

4. **Exclusions**: Use ANDNOT at the end
   ```
   ANDNOT ("automotive" OR "medical" OR "clinical")
   ```

### Examples

**Basic Search**:
```
("AI safety")
```

**Multiple Terms**:
```
("AI" OR "machine learning") AND ("safety")
```

**Complex Query**:
```
("artificial intelligence" OR "large language model" OR "LLM")
AND ("alignment" OR "safety" OR "risk")
ANDNOT ("automotive" OR "medical" OR "agriculture")
```

**Very Specific**:
```
("AI" OR "machine learning" OR "deep learning")
AND ("safety" OR "alignment" OR "interpretability" OR "explainability")
AND ("language model" OR "LLM" OR "GPT" OR "transformer")
ANDNOT ("medical" OR "clinical" OR "automotive" OR "financial")
```

### Validation

Prompts are automatically validated for:
- ✓ Balanced parentheses
- ✓ Balanced quotes
- ✓ No empty groups
- ✓ Valid operators (AND, OR, ANDNOT only)
- ✓ At least one inclusion term

**Invalid prompts are rejected with helpful error messages.**

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│                     (CLI: main.py / GUI: gui.py)            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Supervisor                             │
│          (Orchestrates workers, handles errors)             │
└───┬──────────┬──────────┬──────────┬─────────┬─────────────┘
    │          │          │          │         │
    ▼          ▼          ▼          ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ ArXiv  │ │Semantic│ │LessWrong│ │AI Labs│ │  ...   │
│ Worker │ │Scholar │ │ Worker  │ │ Worker│ │ Worker │
│        │ │ Worker │ │         │ │        │ │        │
└────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘
     │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┘
                            │
                            ▼
     ┌──────────────────────────────────────────────┐
     │            FilterManager                       │
     │    (Boolean logic, content filtering)         │
     └───────────────────┬──────────────────────────┘
                         │
                         ▼
     ┌──────────────────────────────────────────────┐
     │         StorageManager                        │
     │  (SQLite DB, deduplication, versioning)      │
     └───────────────────┬──────────────────────────┘
                         │
                         ▼
     ┌──────────────────────────────────────────────┐
     │          ExportManager                        │
     │         (Excel generation)                    │
     └──────────────────────────────────────────────┘
```

### Key Classes

**Supervisor** (`src/supervisor.py`)
- Manages worker processes
- Handles errors and retries
- Implements self-healing
- Tracks heartbeats and timeouts

**Worker** (`src/worker.py`)
- Runs searchers in isolated processes
- Filters results
- Downloads PDFs
- Stores metadata

**FilterManager** (`src/filter.py`)
- Parses boolean queries
- Filters papers by content
- Excludes job postings, marketing, link aggregators

**StorageManager** (`src/storage.py`)
- SQLite database operations
- Deduplication across sources and cloud storage
- Schema migrations
- Rollback support with cloud protection

**CloudTransferManager** (`src/cloud_transfer.py`)
- Manages staging to cloud transfers
- Implements conflict resolution dialogs
- Verified non-destructive operations

**BackupManager** (`src/backup.py`)
- ZIP compression for database and papers
- Configurable backup directories

**Searchers** (`src/searchers/`)
- `ArxivSearcher`: arXiv.org papers
- `LessWrongSearcher`: LessWrong/Alignment Forum
- `LabScraper`: OpenAI, Anthropic, DeepMind, etc.

---

## Features

### 1. Intelligent Content Filtering

Automatically excludes non-research content:

**Job Postings**:
- "Job Opening: AI Researcher"
- "We're Hiring - Apply Now"
- "Career Opportunities"

**Link Aggregators**:
- "Weekly AI Safety Roundup"
- "This Week in Machine Learning"
- "Curated Research Links"

**Marketing Content**:
- "New AI Platform - Sign Up Today"
- "Request a Demo"
- "Buy Now - Limited Offer"

**36+ default exclusion terms** always applied.

See [CONTENT_FILTERING_GUIDE.md](CONTENT_FILTERING_GUIDE.md) for details.

---

### 2. Cross-Source Deduplication

Papers found on multiple sources are automatically merged:

```
ArXiv: "AI Safety Survey" (ID: arxiv-123)
  ↓
Database: [arxiv-123, source="arxiv"]

Semantic Scholar: "AI Safety Survey" (ID: arxiv-123)
  ↓
Database: [arxiv-123, source="arxiv, semantic", urls="url1 ; url2"]
```

**Benefits**:
- Single entry per paper
- All source URLs preserved
- No duplicate downloads

---

### 3. Self-Healing Error Recovery

When errors occur:

1. **Detection**: Worker crash or timeout detected
2. **Rollback**: Database entries and files deleted
3. **Analysis**: Error logged and analyzed
4. **Retry**: Worker restarted (up to N times)
5. **Recovery**: System continues with other workers

**Example**:
```
[ArXiv] ERROR: Connection reset
[Supervisor] Rolling back ArXiv work...
[Supervisor] Deleted 5 DB entries, 5 files
[Supervisor] Self-healing attempt 1/2...
[ArXiv] Restarting...
[ArXiv] Complete - 10 papers downloaded
```

---

### 4. Mode-Specific Parameters

Different modes optimized for different use cases:

| Feature | TESTING | DAILY | BACKFILL |
|---------|---------|-------|----------|
| Total Limit | 10 | 50 | ∞ |
| Batch Size | 5 | 20 | 10 |
| Duration | 30s | 2-5m | 10-60m |
| Use Case | Quick test | Incremental | Historical |

See [MODE_SETTINGS_GUIDE.md](MODE_SETTINGS_GUIDE.md) for details.

---

### 5. Database Migrations

Automatic schema versioning and migrations:

```python
# Current version tracked in database
CURRENT_VERSION = 2

# Migrations applied automatically
v1: Add 'source' column
v2: Create schema_version table
```

**Benefits**:
- Safe upgrades across versions
- Idempotent migrations
- Handles legacy databases

See [test_migrations.py](test_migrations.py) for verification.

---

### 6. URL Normalization

URLs normalized to prevent duplicates:

```
http://example.com/paper/        →  https://example.com/paper
https://example.com/paper?utm_source=twitter  →  https://example.com/paper
HTTP://EXAMPLE.COM/PAPER         →  https://example.com/paper
```

**Normalized by**:
- Protocol (https)
- Domain case (lowercase)
- Trailing slashes (removed)
- Tracking parameters (removed)

---

### 7. Parallel Execution

All sources searched simultaneously:

```
[2024-01-11 10:00:00] Starting parallel search workers...
[2024-01-11 10:00:00] Supervisor started worker: ArXiv
[2024-01-11 10:00:00] Supervisor started worker: Semantic Scholar
[2024-01-11 10:00:00] Supervisor started worker: LessWrong
[2024-01-11 10:00:01] Supervisor started worker: AI Labs
```

**Performance**: ~3-4x faster than sequential execution

---

### 8. Configurable Retry Logic

All retry/timeout settings configurable:

```yaml
retry_settings:
  max_worker_retries: 2      # Supervisor retries
  worker_retry_delay: 5      # Seconds between retries
  worker_timeout: 600        # Worker max runtime
  api_max_retries: 3         # API call retries
  api_base_delay: 2          # Exponential backoff
  request_pacing_delay: 1.0  # Rate limiting
```

---

## Testing

### Test Suite

Run all tests:
```bash
# Mode settings
python test_mode_settings.py

# Config loading
python test_config_settings.py

# Migrations
python test_migrations.py

# Content filtering
python test_content_filtering.py

# Integration tests
python test_integration.py

# High priority fixes
python test_verification.py

# Self-healing
python test_self_healing.py

# Prompt validation
python test_prompt_validation.py
```

### Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| test_mode_settings.py | 8 | ✅ PASS |
| test_config_settings.py | 8 | ✅ PASS |
| test_migrations.py | 6 | ✅ PASS |
| test_content_filtering.py | 7 | ✅ PASS |
| test_integration.py | 5 | ✅ PASS |
| test_prompt_validation.py | 8 | ✅ PASS |

**Total**: 42+ automated tests

---

## Troubleshooting

### Problem: "Invalid prompt syntax"

**Symptom**:
```
ERROR - Invalid prompt syntax:
  - Unbalanced quotes: found 3 quotes (must be even)
```

**Solution**:
- Check all terms have matching quotes
- Example: `("AI" OR "ML")` not `("AI OR "ML")`

---

### Problem: "Zero documents returned during backfill"

**Symptom**:
```
ERROR - Zero documents returned during backfill run.
```

**Causes**:
1. Search terms too specific (no matches)
2. All papers filtered out
3. API errors across all sources

**Solutions**:
1. Broaden search terms
2. Check debug logs: `python main.py --mode TESTING 2>&1 | grep Filtered`
3. Test individual sources

---

### Problem: "Worker timeout after 600s"

**Symptom**:
```
WARNING - Worker ArXiv timeout after 600s
```

**Solutions**:
1. Increase timeout in config.yaml:
   ```yaml
   retry_settings:
     worker_timeout: 1200  # 20 minutes
   ```
2. Reduce per_query_limit to avoid connection errors
3. Check network connectivity

---

### Problem: Papers saved but not in Excel

**Symptom**: PDFs exist but `research_log.xlsx` empty

**Cause**: Papers marked as synced_to_cloud=1 already

**Solution**:
```sql
# Reset sync status
sqlite3 data/metadata.db
UPDATE papers SET synced_to_cloud = 0;
.exit

# Re-run agent
python main.py --mode DAILY
```

---

### Problem: "Database locked"

**Symptom**:
```
ERROR - database is locked
```

**Cause**: Multiple processes accessing database

**Solution**:
1. Ensure only one agent running
2. Close GUI if running CLI
3. Restart if hung: `pkill -f python` (Linux/Mac)

---

### Problem: Legitimate papers filtered out

**Symptom**: Expected papers not downloaded

**Solution**:
1. Check logs for filtering reason:
   ```bash
   python main.py --mode TESTING 2>&1 | grep "Filtered"
   ```

2. If default exclusion too broad, edit `src/filter.py`:
   ```python
   DEFAULT_EXCLUSIONS = [
       # 'sign up',  # Comment out if too aggressive
   ]
   ```

3. Adjust detection thresholds if needed

---

## Advanced Topics

### Custom Searcher

Add a new source by creating a searcher:

```python
# src/searchers/custom_searcher.py
from .base import BaseSearcher

class CustomSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "custom"
        self.download_dir = os.path.join(
            config.get("papers_dir"),
            self.source_name
        )
        os.makedirs(self.download_dir, exist_ok=True)

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        papers = []
        # Implement search logic
        return papers

    def download(self, paper_meta):
        # Implement download logic
        return pdf_path
```

Register in `main.py`:
```python
from src.searchers.custom_searcher import CustomSearcher

workers = [
    (ArxivSearcher, "ArXiv"),
    (CustomSearcher, "Custom Source"),  # Add here
    # ...
]
```

---

### Scheduled Execution

**Linux/Mac (cron)**:
```bash
# Edit crontab
crontab -e

# Run daily at 6 AM
0 6 * * * cd /path/to/research-agent && /path/to/venv/bin/python main.py --mode DAILY
```

**Windows (Task Scheduler)**:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 6:00 AM
4. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `main.py --mode DAILY`
   - Start in: `C:\path\to\research-agent`

---

### Database Queries

Useful SQL queries:

```sql
# Open database
sqlite3 data/metadata.db

# Count papers by source
SELECT source, COUNT(*) FROM papers GROUP BY source;

# Recent papers
SELECT title, published_date FROM papers
ORDER BY published_date DESC LIMIT 10;

# Papers from multiple sources
SELECT title, source FROM papers
WHERE source LIKE '%,%';

# Unsynced papers
SELECT COUNT(*) FROM papers WHERE synced_to_cloud = 0;

# Check schema version
SELECT * FROM schema_version;
```

---

### Environment-Specific Configs

Create configs for different environments:

```bash
# Development
cp config.yaml config.dev.yaml
# Edit config.dev.yaml (smaller limits)

# Production
cp config.yaml config.prod.yaml
# Edit config.prod.yaml (full limits)

# Use specific config
export RESEARCH_AGENT_CONFIG=config.dev.yaml
python main.py --mode TESTING
```

---

## Performance Tuning

### Optimize for Speed

```yaml
mode_settings:
  daily:
    per_query_limit: 50  # Larger batches (faster but riskier)

retry_settings:
  request_pacing_delay: 0.5  # Faster requests (watch rate limits)
```

### Optimize for Stability

```yaml
mode_settings:
  backfill:
    per_query_limit: 5  # Smaller batches (slower but stable)

retry_settings:
  request_pacing_delay: 2.0  # Slower requests (avoid rate limits)
  api_max_retries: 5          # More retries
```

---

## Project Structure

```
research-agent/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── config.yaml                        # Configuration
├── prompts/
│   └── prompt.txt                     # Search query
│
├── main.py                           # CLI entry point
├── gui.py                            # GUI entry point
│
├── src/
│   ├── supervisor.py                 # Worker orchestration
│   ├── worker.py                     # Worker process logic
│   ├── filter.py                     # Query parsing & filtering
│   ├── storage.py                    # Database operations
│   ├── export.py                     # Excel generation
│   ├── utils.py                      # Utilities
│   │
│   └── searchers/
│       ├── base.py                   # Base searcher class
│       ├── arxiv_searcher.py         # ArXiv integration
│       ├── semantic_searcher.py      # Semantic Scholar API
│       ├── lesswrong_searcher.py     # LessWrong/AF scraper
│       └── lab_scraper.py            # AI lab scrapers
│
├── test_*.py                         # Test files
│
├── data/
│   ├── metadata.db                   # SQLite database
│   └── papers/                       # Downloaded PDFs
│       ├── arxiv/
│       ├── semantic/
│       ├── lesswrong/
│       └── labs/
│
└── docs/
    ├── MODE_SETTINGS_GUIDE.md        # Mode configuration
    ├── CONTENT_FILTERING_GUIDE.md    # Filtering details
    ├── LOW_PRIORITY_RECOMMENDATIONS.md  # Future enhancements
    └── TEST_RESULTS.md               # Test documentation
```

---

## Dependencies

### Core Dependencies

```
arxiv==2.1.0           # ArXiv API client
requests==2.31.0       # HTTP library
pyyaml==6.0.1         # Config parsing
openpyxl==3.1.2       # Excel generation
beautifulsoup4==4.12.2  # HTML parsing
playwright==1.40.0     # Browser automation
semanticscholar==0.8.0  # Semantic Scholar API
```

### Development Dependencies

```
pytest==7.4.3         # Testing framework
pytest-qt==4.2.0      # GUI testing (optional)
memory-profiler==0.61.0  # Performance profiling (optional)
```

Install all:
```bash
pip install -r requirements.txt
```

---

## Versioning

This project uses semantic versioning: `MAJOR.MINOR.PATCH`

**Current Version**: 1.0.0

### Version History

- **1.0.0** (2026-01-11):
  - Initial release
  - Multi-source search (ArXiv, Semantic Scholar, LessWrong, AI Labs)
  - Intelligent content filtering
  - Self-healing architecture
  - Mode-specific parameters
  - Database migration versioning
  - Comprehensive test suite

---

## Changelog

### [1.0.0] - 2026-01-11

#### Added
- Multi-source parallel search (ArXiv, Semantic Scholar, LessWrong, AI Labs)
- Intelligent content filtering (job postings, link aggregators, marketing)
- Self-healing error recovery with rollback
- Mode-specific parameters (TESTING, DAILY, BACKFILL)
- Database migration versioning system
- URL normalization for deduplication
- Configurable retry/timeout settings
- Comprehensive test suite (42+ tests)
- CLI and GUI interfaces
- Excel export with metadata
- Cross-source deduplication

#### Fixed
- GUI worker management crash
- Stop event responsiveness across searchers
- ArXiv hardcoded query issue
- Self-healing file cleanup
- Worker timeout detection

---

## FAQ

**Q: How do I add a new search term?**
A: Edit `prompts/prompt.txt` and re-run the agent.

**Q: Can I search for papers before 2023?**
A: Yes, edit `start_date` in `main.py` or `gui.py` to an earlier date.

**Q: How do I exclude more terms?**
A: Add them to the `ANDNOT` section of your prompt.

**Q: Where are PDFs saved?**
A: `data/papers/{source}/` where source is arxiv, semantic, lesswrong, or labs.

**Q: Can I disable a source?**
A: Yes, comment it out in the `workers` list in `main.py` or `gui.py`.

**Q: How do I reset the database?**
A: Delete `data/metadata.db` (backups recommended).

**Q: Does it work offline?**
A: No, requires internet for searching and downloading.

**Q: What's the API rate limit?**
A: Varies by source. Built-in rate limiting handles this automatically.

**Q: Can I run multiple instances?**
A: No, database locking prevents this. Run one at a time.

**Q: How do I update to a new version?**
A: `git pull` and run `python test_migrations.py` to verify database compatibility.

---

## Support

### Getting Help

1. **Documentation**: Check guides in `docs/` folder
2. **Tests**: Run relevant test file to diagnose issues
3. **Logs**: Check `research_agent.log` for detailed errors
4. **Issues**: Report bugs on GitHub Issues

### Debug Mode

Enable detailed logging:
```python
# In src/utils.py
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    # ...
)
```

---

## Contributing

### Development Setup

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes
4. Run tests: `python test_*.py`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature-name`
7. Submit pull request

### Code Style

- PEP 8 compliance
- Type hints where appropriate
- Docstrings for all public methods
- Unit tests for new features

### Areas for Contribution

- New searcher implementations
- Additional export formats (CSV, JSON, BibTeX)
- Performance optimizations
- Additional test coverage
- Documentation improvements

---

## License

MIT License - see LICENSE file for details.

---

## Acknowledgments

- **ArXiv** for open access to research papers
- **Semantic Scholar** for comprehensive academic search
- **LessWrong** and **Alignment Forum** for AI safety content
- **AI Research Labs** (Anthropic, OpenAI, DeepMind, etc.) for publishing research

---

## Contact

**Project Repository**: https://github.com/yourusername/research-agent
**Issues**: https://github.com/yourusername/research-agent/issues
**Documentation**: See `docs/` folder

---

## Quick Reference Card

### Common Commands

```bash
# Test run
python main.py --mode TESTING

# Daily update
python main.py --mode DAILY

# Full backfill
python main.py --mode BACKFILL

# Launch GUI
python gui.py

# Run all tests
python test_*.py
```

### Prompt Syntax

```
("term1" OR "term2") AND ("term3") ANDNOT ("exclude")
```

### Configuration Files

- `config.yaml` - Main configuration
- `prompts/prompt.txt` - Search query
- `data/metadata.db` - Database
- `research_log.xlsx` - Output

### Test Suite

```bash
python test_mode_settings.py        # Mode configuration
python test_content_filtering.py    # Filtering logic
python test_integration.py          # End-to-end tests
```

---

**Built with ❤️ for the AI safety research community**
