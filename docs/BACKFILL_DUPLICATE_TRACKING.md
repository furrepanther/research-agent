# BACKFILL Mode Duplicate Tracking

## Summary

Implemented mode-specific duplicate tracking that ONLY applies during BACKFILL mode. This provides better visibility into retrieval progress when encountering papers that already exist in the database.

## Changes Made

### Modified: `src/worker.py`

**Lines 149-193**: Enhanced duplicate detection and progress tracking

- Added `duplicate_count` variable to track papers skipped because they already exist
- In BACKFILL mode: Count duplicates toward progress display
- In other modes (DAILY, TESTING): Do NOT count duplicates toward progress

**Duplicate Detection Logic** (Lines 168-193):
```python
# Check for duplicates before downloading
# 1. Check Cloud Storage first
if cloud_storage.check_duplicates(source_url):
    duplicate_count += 1
    is_cloud_duplicate = True

# 2. Check Database second
elif storage.paper_exists(source_url=source_url):
    duplicate_count += 1

# ONLY in BACKFILL mode: count duplicates toward progress
if mode == "BACKFILL":
    processed = downloaded_count + duplicate_count
```

**Download Progress Updates** (Lines 195-228):
- BACKFILL mode: Shows "New: X, Duplicates: Y" in details
- Other modes: Shows "Downloading (X/Y)" in details
- Downloaded count in BACKFILL includes both new and duplicates
- Downloaded count in other modes includes only new papers

**Final Status Messages** (Lines 247-268):
- BACKFILL mode: "✓ New: X, Duplicates: Y"
- Other modes: "✓ Downloaded X papers"
- Log messages include breakdown for BACKFILL

## Behavior by Mode

### BACKFILL Mode
- **Progress Display**: "New: 45, Duplicates: 155"
- **Downloaded Count**: 200 (45 new + 155 duplicates)
- **Final Message**: "45 new papers, 155 duplicates"
- **Purpose**: Show progress even when encountering many existing papers

### DAILY/TESTING Modes
- **Progress Display**: "Downloading (12/50)"
- **Downloaded Count**: 12 (only new papers)
- **Final Message**: "12 papers downloaded"
- **Purpose**: Focus on newly added papers only

## Why BACKFILL Mode is Different

When running BACKFILL mode to collect historical papers (e.g., from 2003-2024), you're likely to encounter MANY papers that already exist in the database from previous runs. Without duplicate counting:

- Progress appears stuck at 0 for long periods
- Users don't know if the system is working or frozen
- No visibility into how many papers are being checked

With duplicate counting:
- Progress bar moves forward as papers are processed
- Clear breakdown shows what's new vs already collected
- Users can see the system is actively working
- Better understanding of collection completeness

## Testing

Run `test_backfill_mode_display.py` to verify the implementation:
```bash
python test_backfill_mode_display.py
```

Manual verification:
1. Run BACKFILL mode: `python main.py --mode BACKFILL`
2. Observe progress messages showing "New: X, Duplicates: Y"
3. Run DAILY mode: `python main.py --mode DAILY`
4. Observe progress messages showing "Downloading (X/Y)"

## Implementation Details

**Duplicate Count Tracking**:
- Separate `duplicate_count` variable maintains count of skipped papers
- Only incremented when `storage.paper_exists(source_url=source_url)` returns True
- Independent of `downloaded_count` which tracks successfully added papers

**Progress Percentage**:
- BACKFILL: Based on (new + duplicates) / total_to_process
- Other modes: Based on new / total_to_process

**Message Format**:
- Mode-specific branching ensures correct format for each mode
- Consistent between progress updates and final status

## Future Considerations

- Could add configuration option to enable/disable duplicate counting in other modes
- Could add more detailed statistics (e.g., duplicate sources)
- Could expose duplicate count in GUI summary window
