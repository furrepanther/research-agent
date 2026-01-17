# Mode-Specific Parameter Settings Guide

## Overview

The Research Agent now supports three distinct operational modes with customized parameters for each:

1. **AUTOMATIC** - Detects mode based on database state
2. **TEST** - Count-only verification (no downloads)
3. **BACKFILL** - Historical collection with unlimited total papers

## Configuration

### Config File Structure (`config.yaml`)

mode_settings:
  # Testing mode - small limits for quick verification
  testing:
    max_papers_per_agent: 10       # Total papers per agent (hard limit)
    per_query_limit: 5             # Papers fetched per API call/batch
    respect_date_range: false      # Stop when limit hit, ignore dates

  # Test mode - count only, no downloads or database updates
  test:
    max_papers_per_agent: 0        # No downloads
    per_query_limit: 100           # Fetch counts only
    respect_date_range: true       # Respect date ranges for accurate counts

  # Daily mode - moderate limits for incremental updates
  daily:
    max_papers_per_agent: 50       # Total papers per agent
    per_query_limit: 20            # Papers per API call
    respect_date_range: true       # Stop at start_date

  # Backfill mode - unlimited total, small batches for stability
  backfill:
    max_papers_per_agent: null     # No limit (null = unlimited)
    per_query_limit: 10            # Smaller batches to avoid connection errors
    respect_date_range: true       # Continue until date range satisfied

## Mode Behavior

### TESTING Mode
- **Purpose**: Quick verification during development/testing
- **Total Limit**: 10 papers per agent (40 total across 4 agents)
- **Batch Size**: 5 papers per API call
- **Date Handling**: Ignores date ranges (stops when limit reached)
- **Use Case**: "Run a quick test to verify everything works"

```bash
python main.py --mode TESTING
```

### DAILY Mode
- **Purpose**: Daily incremental updates
- **Total Limit**: 50 papers per agent (200 total across 4 agents)
- **Batch Size**: 20 papers per API call
- **Date Handling**: Respects start_date (only fetches papers after latest DB date)
- **Use Case**: "Fetch new papers published since last run"
- **Auto-Detection**: Automatically selected if database contains papers

```bash
python main.py --mode DAILY
```

### BACKFILL Mode
- **Purpose**: Historical collection for new topics or empty database
- **Total Limit**: **UNLIMITED** (fetches until date range satisfied)
- **Batch Size**: 10 papers per API call (smaller to avoid connection errors)
- **Date Handling**: Respects start_date (continues until reaching 2023-01-01 or earlier)
- **Use Case**: "Fill database with all relevant papers from past years"
- **Auto-Detection**: Automatically selected if database is empty

```bash
python main.py --mode BACKFILL
```

## Key Parameters Explained

### max_papers_per_agent
- **Type**: `int` or `null` (for unlimited)
- **Purpose**: Total papers each agent will download before stopping
- **Notes**:
  - Set to `null` for backfill mode to allow unlimited downloads
  - Converts to `float('inf')` internally for comparison logic
  - Each agent (ArXiv, Semantic Scholar, LessWrong, AI Labs) respects this limit independently

### per_query_limit
- **Type**: `int`
- **Purpose**: Maximum papers fetched in a single API call/batch
- **Notes**:
  - **Smaller values** (5-10): More stable, fewer connection errors, better for backfill
  - **Larger values** (20-50): Faster but riskier, better for daily updates
  - This is NOT the total limit, just the batch size per API request

### respect_date_range
- **Type**: `boolean`
- **Purpose**: Whether to filter papers by published date
- **Notes**:
  - `true`: Only fetch papers published after `start_date`
  - `false`: Ignore dates, fetch newest papers regardless
  - Affects searcher behavior and filtering logic

## Mode Auto-Detection

The system automatically detects the appropriate mode:

```python
# In CLI (main.py) and GUI (gui.py)
latest_date = storage.get_latest_date()

if latest_date exists:
    mode = DAILY  # Database has papers, do incremental update
else:
    mode = BACKFILL  # Empty database, do full backfill
```

Override with `--mode` flag:
```bash
python main.py --mode TESTING   # Force testing mode
python main.py --mode DAILY     # Force daily mode
python main.py --mode BACKFILL  # Force backfill mode
```

## Implementation Details

### Parameter Flow

1. **main.py** or **gui.py** loads `mode_settings` from config
2. Builds `search_params` dict:
   ```python
   search_params = {
       'max_papers_per_agent': 50,
       'per_query_limit': 20,
       'respect_date_range': True,
       'start_date': datetime(2024, 1, 1)
   }
   ```
3. Passes to **Supervisor**
4. Supervisor passes to **worker.py** (run_worker function)
5. Worker extracts parameters and passes to each **searcher**
6. Worker enforces `max_papers_per_agent` limit during download loop

### Worker Limit Enforcement

```python
# In worker.py
downloaded_count = 0
for paper in filtered_papers:
    if downloaded_count >= max_papers_per_agent:
        break  # Stop at limit

    download_and_store(paper)
    downloaded_count += 1
```

## Backward Compatibility

### Legacy Settings Preserved

```yaml
# OLD (still supported)
max_results_daily: 200
max_results_backfill: 200
```

### Deprecated Flag

```bash
python main.py --max-results 100  # Still works but shows warning
# WARNING: Using deprecated --max-results flag. Consider using mode_settings in config.yaml
```

## Testing

Run the test suite to verify mode settings:

```bash
python test_mode_settings.py
```

Expected output:
```
[PASS] All three modes present in config
[PASS] TESTING mode configured correctly
[PASS] DAILY mode configured correctly
[PASS] BACKFILL mode configured correctly (unlimited)
[PASS] Supervisor stores search_params correctly
[PASS] Parameter extraction works correctly
[PASS] Infinity handling works correctly
[PASS] Legacy settings preserved for backward compatibility
```

## Example Scenarios

### Scenario 1: New Research Topic (First Run)
**Goal**: Collect all papers on "quantum AI alignment" from 2023 onwards

```bash
# Edit prompt.txt with new search terms
# Database is empty, so BACKFILL auto-detected
python main.py

# Result:
# - Mode: BACKFILL
# - Limits: UNLIMITED total, 10 per query
# - Fetches papers until reaching 2023-01-01
# - May download hundreds of papers
```

### Scenario 2: Daily Morning Update
**Goal**: Check for new papers published overnight

```bash
# Database contains papers from yesterday
# DAILY mode auto-detected
python main.py

# Result:
# - Mode: DAILY
# - Limits: 50 total, 20 per query
# - Only fetches papers after yesterday's date
# - Quick update with ~0-50 new papers
```

### Scenario 3: Quick Test After Code Change
**Goal**: Verify changes work without waiting 10 minutes

```bash
python main.py --mode TESTING

# Result:
# - Mode: TESTING
# - Limits: 10 total, 5 per query
# - Ignores dates, just fetches newest papers
# - Completes in ~30 seconds
```

### Scenario 4: Expanding Date Range
**Goal**: Go back further in time to collect older papers

```python
# Edit main.py or gui.py to change start_date
start_date = datetime(2020, 1, 1)  # Instead of 2023

python main.py --mode BACKFILL

# Result:
# - Fetches papers from 2020-2023 that weren't collected before
# - UNLIMITED total with small 10-paper batches
```

## Benefits of Mode-Specific Settings

### Stability
- **Backfill** uses small batches (10) to avoid timeouts during long runs
- Prevents "connection reset" errors on multi-hour backfills

### Efficiency
- **Daily** uses larger batches (20) for faster updates
- **Testing** uses tiny limits (10 total) for instant feedback

### Flexibility
- Each mode optimized for its use case
- Easy to adjust parameters per-environment (dev vs prod)

### Safety
- **Daily** mode has hard cap (50) to prevent runaway downloads
- **Testing** mode protects against accidental large fetches

## Troubleshooting

### Problem: "Backfill stopping at 50 papers"
**Cause**: Mode is set to DAILY instead of BACKFILL

**Solution**:
```bash
python main.py --mode BACKFILL  # Force backfill mode
```

### Problem: "Per-query limit too high, getting connection errors"
**Cause**: `per_query_limit` is set too high (e.g., 100)

**Solution**: Edit `config.yaml`
```yaml
backfill:
  per_query_limit: 5  # Reduce to 5 for more stability
```

### Problem: "Testing mode fetching too many papers"
**Cause**: `max_papers_per_agent` too high in testing section

**Solution**: Edit `config.yaml`
```yaml
testing:
  max_papers_per_agent: 5  # Reduce to 5 for faster tests
```

### Problem: "Dates being ignored in daily mode"
**Cause**: `respect_date_range: false` in daily section

**Solution**: Edit `config.yaml`
```yaml
daily:
  respect_date_range: true  # Must be true for daily updates
```

## Future Enhancements

Potential improvements for future development:

1. **Environment-Specific Configs**
   - `config.dev.yaml` vs `config.prod.yaml`
   - Different limits for development vs production

2. **Per-Agent Limits**
   - ArXiv: 20 papers max
   - Semantic Scholar: 100 papers max
   - Different limits per source

3. **Time-Based Limits**
   - "Stop after 30 minutes regardless of paper count"
   - Prevents infinite backfill runs

4. **Smart Batch Sizing**
   - Automatically reduce `per_query_limit` after errors
   - Adaptive batch sizing based on API responsiveness

5. **Progress Tracking**
   - "Backfill: 45% complete (fetched papers back to 2021-06-15)"
   - Visual progress bar in GUI

---

## Summary

| Mode | Total Limit | Batch Size | Respects Dates | Use Case |
|------|------------|------------|----------------|----------|
| **TESTING** | 10 | 5 | No | Quick verification |
| **DAILY** | 50 | 20 | Yes | Incremental updates |
| **BACKFILL** | ∞ | 10 | Yes | Historical collection |

The new mode-specific settings provide fine-grained control over search behavior while maintaining simplicity through sensible defaults and automatic mode detection.
