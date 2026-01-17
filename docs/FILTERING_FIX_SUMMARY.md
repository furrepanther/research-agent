# URL Filtering Fix Summary

## Problem

The previous filtering logic was **too aggressive** in filtering out legitimate research papers. The issue was in the `_is_link_aggregator()` method in `src/filter.py`:

**Old Logic (Lines 140-148)**:
```python
# Count URL-like patterns
url_patterns = len(re.findall(r'https?://|www\.|\[.*?\]\(.*?\)', abstract))
word_count = len(abstract.split())

# If more than 30% of words are URL-related, likely a link list
if word_count > 0 and url_patterns / word_count > 0.3:
    return True
```

### Issues with Old Logic:

1. **No context awareness**: Applied the 30% URL density threshold to ALL content, regardless of length
2. **No research indicators**: Didn't check if content had research-oriented language
3. **False positives**: Research papers with reference URLs (common in academic papers) were incorrectly flagged as "link aggregators"
4. **Threshold too low**: 30% URL density applied to both short and long content

### Real-World Impact:

On a backfill run starting from 2003, this would incorrectly filter:
- Research papers with dataset links (e.g., "Our dataset: https://github.com/...")
- Papers with multiple arXiv/DOI references
- Survey papers citing many sources
- Papers with supplementary materials links

## Solution

The improved logic now **intelligently distinguishes** between:
- **Link Aggregators**: Short content with many URLs, list formatting, minimal narrative
- **Research Papers**: Substantial text with research indicators, even if they contain URLs

### New Logic (Lines 119-190):

#### 1. **Context-Aware URL Density Check**
```python
# Only flag as aggregator if BOTH conditions are true:
# 1. Short content (< 300 words) - too short for a research abstract
# 2. High URL density (> 40% of content is URLs)
if word_count < 300 and url_patterns > 0:
    url_density = url_patterns / word_count
    if url_density > 0.4:
        return True  # Short + high density = aggregator
```

**Key Improvement**: Long research papers (300+ words) are NOT subject to URL density checks, since legitimate papers can have many references.

#### 2. **List Formatting Detection**
```python
# If there are MANY URLs (10+) in relatively short text (< 500 words),
# check for list-style formatting
if word_count < 500 and url_patterns >= 10:
    list_indicators = abstract.count('\n-') + abstract.count('\n*') + abstract.count('\n1.')
    if list_indicators >= 5:  # Multiple list items = aggregator
        return True
```

**Key Improvement**: Detects bullet/numbered lists typical of link aggregators.

#### 3. **Research Indicator Detection**
```python
research_indicators = [
    'method', 'experiment', 'result', 'conclusion', 'analysis',
    'dataset', 'model', 'algorithm', 'evaluation', 'approach',
    'propose', 'demonstrate', 'show that', 'find that', 'performance',
    'accuracy', 'training', 'tested', 'measured', 'compared'
]

research_indicator_count = sum(1 for indicator in research_indicators if indicator in content)

# If we have multiple research indicators and reasonable length, it's NOT an aggregator
# even if it has some URLs
if research_indicator_count >= 3 and word_count >= 150:
    return False  # Protected by research indicators
```

**Key Improvement**: Papers with research-oriented language are protected from being filtered, even if they contain URLs.

## Test Results

### New Test Suite: `test_url_filtering_fix.py`

**Legitimate Papers with URLs: 4/4 PASSED** ✓
1. Research paper with dataset URL (71 words, 1 URL) - **PASSED**
2. Research paper with multiple references (89 words, 3 URLs) - **PASSED**
3. Research paper with arXiv links (94 words, 2 URLs) - **PASSED**
4. Long paper with many references (126 words, 7 URLs) - **PASSED**

**Link Aggregators Filtered: 3/3 PASSED** ✓
1. "Weekly Roundup" with 10 URLs in 11 words - **FILTERED**
2. "This Week" with 5 URLs in 9 words - **FILTERED**
3. List format with 6 URLs in 24 words - **FILTERED**

**Total Score: 7/7** ✓

### Existing Tests: `test_content_filtering.py`

All existing tests still pass:
- Job posting detection: 4/4 ✓
- Link aggregator detection: 4/4 ✓
- Marketing content detection: 4/4 ✓
- Legitimate research: 4/4 ✓
- Edge cases: 4/4 ✓

## Impact on Backfill Results

### Before Fix:
- Too many legitimate papers filtered out
- ArXiv backfill from 2003 would return far fewer papers than expected
- Research papers with references incorrectly excluded

### After Fix:
- Legitimate research papers with URLs now pass through
- Link aggregators still correctly filtered
- Expected to see **significantly more papers** in backfill runs
- Better balance between filtering noise and preserving legitimate content

## Thresholds Summary

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Short content | < 300 words | Research abstracts typically 150+ words |
| High URL density | > 40% | Up from 30%, allows some references |
| Many URLs check | 10+ URLs in < 500 words | Catches aggregators with lower density |
| List indicators | 5+ list items | Typical of link aggregator formatting |
| Research indicators | 3+ terms | Strong signal of research content |
| Protected length | 150+ words | Minimum for research abstract |

## Files Modified

1. **src/filter.py** - Updated `_is_link_aggregator()` method (lines 119-190)
2. **test_url_filtering_fix.py** - New comprehensive test suite
3. **FILTERING_FIX_SUMMARY.md** - This documentation

## Verification Steps

To verify the fix works:

```bash
# Run new URL filtering tests
python test_url_filtering_fix.py

# Run existing content filtering tests
python test_content_filtering.py

# Run a backfill to compare results
python main.py --mode TESTING
```

## Expected Behavior

### Should PASS Through (NOT filtered):
- Research papers with 1-2 dataset/code URLs
- Survey papers with multiple arXiv references
- Papers with DOI links in abstract
- Any paper with 150+ words and 3+ research terms

### Should BE FILTERED:
- "Weekly roundup" posts with title keywords
- Short content (< 300 words) with > 40% URL density
- List-formatted pages with 10+ URLs
- Content with < 100 words and aggregator keywords

## Conclusion

The filtering now correctly distinguishes between:
1. **Legitimate research** that happens to contain URLs
2. **Link aggregators** that are primarily lists of URLs

This should result in **significantly better backfill results** with more legitimate papers and fewer false positives.
