# Quiz Solver Improvements

## Summary of Enhancements

This document describes the improvements made to the quiz solver to handle all quiz formats comprehensively.

## 1. Enhanced Task Parsing (`parse_task` function)

### A) Submit URL Extraction

**Previous:** Only extracted plain text URLs like "Post to https://..."

**Now:**
- **Plain text patterns:** "Post to", "Submit to", "Send to"
- **Form action attributes:** `<form action="URL">` or `<form method="post" action="URL">`
- **Relative URL resolution:** Converts `/api/submit` → `https://example.com/api/submit`

**Example:**
```html
<form method="post" action="/api/submit">
```
Result: `https://example.com/api/submit` (when quiz URL is `https://example.com/quiz`)

---

### B) File and Data URL Extraction

**Previous:** Only extracted absolute URLs ending in .pdf, .csv, .xlsx

**Now:**
- **File URLs:** Absolute URLs with file extensions (.pdf, .csv, .xlsx, .txt)
- **Data URLs:** All `<a href="...">` links (absolute and relative)
- **Relative URL resolution:**
  - `/data/file.csv` → `https://example.com/data/file.csv`
  - `data/file.csv` → `https://example.com/data/file.csv`

**Example:**
```html
<a href="/data/sales.csv">Download</a>
<a href="https://example.com/report.pdf">Report</a>
```
Results:
- File URLs: `['https://example.com/report.pdf']`
- Data URLs: `['https://example.com/data/sales.csv']`

---

### C) Placeholder Replacement

**New Feature:** Replaces `$EMAIL` with actual student email

**Example:**
```
Submit to: https://api.example.com/submit?user=$EMAIL
```
Result: `https://api.example.com/submit?user=student@example.com`

---

### D) Improved URL Parsing

**Fixes:**
- Skips `javascript:void(0)` links
- Skips `#anchor` links
- Removes trailing punctuation (.,;:)
- Handles both quoted and unquoted href attributes
- Prevents duplicate URL extraction

---

## 2. Enhanced Data Extraction (`solve_quiz` Step 3)

### A) Scrape URL Detection

**New Feature:** Detects when task explicitly mentions scraping a URL

**Patterns:**
- "Scrape the data from https://..."
- "Download from https://..."
- "Fetch data from https://..."
- "Get data from https://..."

**Example:**
```
Scrape the table from https://example.com/data.html and find the total.
```
Result: Prioritizes scraping `https://example.com/data.html`

---

### B) URL Priority System

**Processing order:**
1. **Explicit scrape URLs** (from task text)
2. **File URLs** (PDFs, CSVs, Excel files)
3. **Data URLs** (href links)
4. **Current quiz page** (fallback)

**Benefits:**
- Tries most relevant sources first
- Continues to next source if one fails
- Logs each attempt for debugging

---

### C) File Type Detection

**Supported formats:**
- **PDF:** Uses `pdfplumber` to extract tables
- **CSV:** Uses `pandas.read_csv()`
- **Excel (.xlsx, .xls):** Uses `pandas.read_excel()`
- **TXT:** Attempts CSV parsing
- **Web pages:** Uses `BeautifulSoup` + `pandas.read_html()`

**Example:**
```python
# For file URLs
if url.endswith('.pdf'):
    df = await extract_pdf_tables(file_bytes)
elif url.endswith('.csv'):
    df = pd.read_csv(BytesIO(file_bytes))
else:
    # Try extracting web tables
    df = await extract_web_table(url)
```

---

## 3. Improved Error Handling

### A) Missing Submit URL

**Previous:** Would crash with error

**Now:**
- Logs warning: "⚠ Submit URL not found in task text"
- Records error but continues gracefully
- Adds error to results summary

---

### B) Failed Data Extraction

**Previous:** Would submit "Unable to determine answer"

**Now:**
- Tries multiple data sources (files, URLs, web tables)
- Falls back to LLM with task text only
- Submits empty string if all methods fail

---

### C) Missing Data or Question

**New behavior:**
```python
if not df and not question_text:
    # Try LLM with task text only
    if api_token:
        answer = await analyze_with_llm(task_text, "No data available", api_token)
    else:
        answer = ""  # Submit empty instead of crashing
```

---

## 4. Detailed Logging

### Enhanced Log Output

**Before each question:**
```
Question ID: Q834
Submit URL: Found/Not found
File URLs: 2
Data URLs: 1
```

**During data extraction:**
```
Trying scrape target URL: https://example.com/data.html
✓ Extracted DataFrame from file: (100, 5)
Data source: https://example.com/data.csv
```

**URL summary:**
```
Parsing summary:
  - File URLs: 2
  - Data URLs: 3
  - All URLs: 5 total
  - Submit URL: Found
```

---

## 5. Function Signature Changes

### `parse_task(task_text, quiz_url=None, email=None)`

**New parameters:**
- `quiz_url`: For resolving relative URLs
- `email`: For replacing $EMAIL placeholder

**New return fields:**
```python
{
    "question_id": "Q834",
    "question_text": "What is the total?",
    "submit_url": "https://api.example.com/submit",
    "file_urls": ["https://example.com/data.pdf"],
    "data_urls": ["https://example.com/table.html"],
    "all_urls": ["https://...", "https://..."],
    "raw_text": "..."
}
```

---

## Testing

### Test Coverage

Run tests with:
```bash
python3 test_parse_only.py
```

**Test scenarios:**
1. Form action with relative URL
2. $EMAIL placeholder replacement
3. Multiple href links (absolute + relative)
4. Skipping javascript/anchor links
5. Question text extraction

All tests pass ✓

---

## Usage Example

### Typical Quiz Flow

```python
# Step 1: Extract task from quiz page
task_text = await extract_task_from_url(quiz_url)

# Step 2: Parse task (with quiz_url and email)
parsed = parse_task(task_text, quiz_url=quiz_url, email=student_email)

# Step 3: Try multiple data sources
for url_type, url in [(scrape_url), (file_urls), (data_urls)]:
    if url.endswith(('.pdf', '.csv', '.xlsx')):
        file_bytes = await download_file(url)
        df = extract_from_file(file_bytes)
    else:
        df = await extract_web_table(url)

    if df is not None and not df.empty:
        break

# Step 4: Analyze and solve
if df is not None:
    result = solve_task(df, question_text)
    answer = result['formatted_answer']

    # Fallback to LLM if unknown
    if result['task_type'] == 'unknown':
        answer = await analyze_with_llm(question_text, df_summary, api_token)

# Step 5: Submit answer
if submit_url:
    await submit_answer(submit_url, email, secret, quiz_url, answer)
```

---

## Key Benefits

1. **Handles all URL formats:** Absolute, relative, form actions, href links
2. **Robust data extraction:** Tries multiple sources, handles failures gracefully
3. **Smart placeholder replacement:** $EMAIL substitution
4. **Better error handling:** Never crashes, always submits something
5. **Detailed logging:** Easy debugging with comprehensive logs
6. **LLM fallback:** Uses AI when deterministic methods fail

---

## Backward Compatibility

All previous functionality is preserved. The enhancements are additive:

- Old code: `parse_task(text)` still works
- New code: `parse_task(text, quiz_url, email)` enables new features
- Graceful degradation: Features disabled if parameters not provided

---

## Future Enhancements

Potential improvements:
- Support for JSON data endpoints
- Image-based question extraction (OCR)
- Multi-page PDF handling
- Cached data extraction to avoid re-downloading
