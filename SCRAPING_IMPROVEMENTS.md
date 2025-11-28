# Scraping and URL Handling Improvements

## Overview

Major improvements to handle Question 2 and similar quiz types that require scraping data URLs to extract answers.

---

## 1. Enhanced Submit URL Detection

### New Feature: Relative URL Support

**Location:** [quiz_solver.py:132-181](quiz_solver.py#L132-L181)

**Previously:** Only detected absolute URLs like `https://example.com/submit`

**Now:** Detects and resolves relative URLs:

#### Patterns Detected:

1. **Absolute URLs** (existing)
   ```
   Post to https://example.com/submit
   ```

2. **Relative URLs** (NEW)
   ```
   POST to /submit
   Submit to /api/answer
   ```
   → Resolves to: `{base_domain}/submit`

3. **Form actions** (existing, improved)
   ```html
   <form action="/submit">
   ```

4. **Href links** (NEW)
   ```html
   <a href="/submit">Submit here</a>
   ```

#### Example:

**Input:**
- Task text: `"POST your answer to /submit"`
- Quiz URL: `"https://example.com/quiz-2"`

**Output:**
```python
submit_url = "https://example.com/submit"
```

**Logs:**
```
INFO - Found relative submit URL: /submit -> https://example.com/submit
```

---

## 2. URL Scraping for Answers

### New Function: `scrape_and_extract_answer(url)`

**Location:** [quiz_solver.py:65-168](quiz_solver.py#L65-L168)

**Purpose:** Scrape a URL and intelligently extract the answer from its content.

### Supported Content Types:

#### A) JSON Responses

**Pattern:** Looks for specific keys in JSON
```python
answer_keys = ['answer', 'secret', 'code', 'secret_code', 'value', 'result']
```

**Example:**
```json
{
  "secret": "ABC123"
}
```
→ Extracts: `"ABC123"`

**Logs:**
```
INFO - Scraped JSON data: {'secret': 'ABC123'}
INFO - ✓ Found answer in JSON field 'secret': ABC123
```

#### B) HTML with Patterns

**Patterns matched:**
- `secret code: XYZ789`
- `answer: 12345`
- `code: demo-secret`
- `value: test123`

**Example HTML:**
```html
<html>
  <body>
    <p>Your secret code: XYZ789</p>
  </body>
</html>
```
→ Extracts: `"XYZ789"`

**Logs:**
```
INFO - Visible text extracted: Your secret code: XYZ789
INFO - ✓ Found answer using pattern 'secret\s*code\s*[:\-]?\s*([A-Za-z0-9_\-]+)': XYZ789
```

#### C) Plain Text Responses

**Condition:** Content is short (<100 chars) and looks like an answer

**Example:**
```
demo-secret-123
```
→ Extracts: `"demo-secret-123"`

**Logs:**
```
INFO - ✓ Using scraped text as answer: demo-secret-123
```

### Features:

- ✅ Handles JSON, HTML, and plain text
- ✅ Extracts visible text from HTML (removes scripts/styles)
- ✅ Multiple pattern matching for flexibility
- ✅ Cleans up common prefixes
- ✅ Comprehensive logging

---

## 3. Scraping Integration in Quiz Flow

### New Step: 3.5 - Scrape URLs for Answers

**Location:** [quiz_solver.py:689-713](quiz_solver.py#L689-L713)

**When it runs:**
- After trying to extract data from files/tables (Step 3)
- Before analyzing data (Step 4)
- Only if no DataFrame data found OR task explicitly mentions scraping

### Priority Order:

1. **Explicit scrape URL** (from task text)
   ```
   "Scrape data from https://example.com/data"
   ```

2. **Data URLs** (from href links)
   ```html
   <a href="/demo-scrape-data?email=...">Get data</a>
   ```

### Logic:

```python
# Step 3.5: Try scraping URLs for direct answers
urls_to_scrape = []
if scrape_url:
    urls_to_scrape.append(scrape_url)
urls_to_scrape.extend(parsed_task.get("data_urls", []))

# Only scrape if we don't have DataFrame OR task explicitly mentions scraping
should_scrape = (df is None or df.empty) or scrape_url is not None

if urls_to_scrape and should_scrape:
    for url_to_scrape in urls_to_scrape:
        scraped_answer = await scrape_and_extract_answer(url_to_scrape)
        if scraped_answer:
            # Use this answer!
            break
```

### Updated Step 4 Answer Selection:

**Priority:**

1. **Scraped answer** (NEW - highest priority)
2. **Demo example** (only if clearly a placeholder)
3. **DataFrame analysis** (existing)
4. **LLM fallback** (existing)
5. **Default values** (existing)

---

## 4. Smarter Example Answer Detection

### Updated: `extract_example_answer()`

**Location:** [quiz_solver.py:24-62](quiz_solver.py#L24-L62)

**Problem:** Previously used ANY JSON answer as an example

**Solution:** Now checks if it's actually a demo placeholder

### Placeholder Keywords:

```python
placeholder_keywords = ['anything', 'demo', 'test', 'example', 'your answer']
```

### Examples:

| JSON Answer | Used as Example? | Reason |
|-------------|------------------|--------|
| `"anything you want"` | ✅ Yes | Contains "anything" |
| `"demo"` | ✅ Yes | Contains "demo" |
| `"test answer"` | ✅ Yes | Contains "test" |
| `"XYZ123"` | ❌ No | Real answer - scrape instead |
| `"secret-code-789"` | ❌ No | Real answer - scrape instead |

**Logs:**

**Demo example:**
```
INFO - Found demo example answer in task text: 'anything you want'
```

**Real answer (should scrape):**
```
INFO - Found answer in JSON but not a demo placeholder: 'XYZ123' - will scrape instead
```

---

## 5. Complete Flow for Question 2

### Example: Demo-Scrape Task

**Task Text:**
```
Question 2:
Scrape this URL: /demo-scrape-data?email=$EMAIL
POST your answer to /submit
```

**Processing:**

#### Step 1: Extract task
```
✓ Extracted task text
```

#### Step 2: Parse task
```
INFO - Base domain: https://example.com
INFO - Found relative submit URL: /submit -> https://example.com/submit
INFO - Replaced $EMAIL in data URL: /demo-scrape-data?email=student@example.com
INFO - Found data URL (href): https://example.com/demo-scrape-data?email=student@example.com
```

**Parsed result:**
```python
{
  "submit_url": "https://example.com/submit",
  "data_urls": ["https://example.com/demo-scrape-data?email=student@example.com"]
}
```

#### Step 3: Try to extract data
```
INFO - No file URLs or tables found
```

#### Step 3.5: Scrape URLs for answers
```
INFO - Step 3.5: Trying to scrape URLs for direct answers
INFO - Attempting to scrape answer from: https://example.com/demo-scrape-data?email=student@example.com
INFO - Scraping URL for answer: https://example.com/demo-scrape-data?email=student@example.com
INFO - Scrape response status: 200
INFO - Scraped JSON data: {'secret': 'demo-secret-789'}
INFO - ✓ Found answer in JSON field 'secret': demo-secret-789
INFO - ✓ Successfully scraped answer: demo-secret-789
```

#### Step 4: Use scraped answer
```
INFO - Step 4: Analyzing data and solving task
INFO - Using scraped answer: 'demo-secret-789'
```

**Question result:**
```python
{
  "answer": "demo-secret-789",
  "task_type": "scraped",
  "used_scraping": True,
  "scraped_from": "https://example.com/demo-scrape-data?email=student@example.com"
}
```

#### Step 5: Submit answer
```
INFO - Step 5: Submitting answer
INFO - Submitting answer to: https://example.com/submit
INFO - Answer: demo-secret-789
```

**Submission payload:**
```json
{
  "email": "student@example.com",
  "secret": "student_secret",
  "url": "https://example.com/quiz-2",
  "answer": "demo-secret-789"
}
```

---

## 6. Testing

### Run Tests:

```bash
python3 test_scraping.py
```

### Test Coverage:

1. **Scraping Simulation:**
   - JSON with secret code
   - HTML with pattern matching
   - Plain text responses

2. **Relative URL Extraction:**
   - `POST to /submit`
   - `Submit to /api/answer`
   - `<a href="/submit">`

3. **Example Answer Filtering:**
   - Demo placeholders (use as example)
   - Real answers (scrape instead)

**All tests pass ✓**

---

## 7. Key Improvements Summary

### For Question 2 Specifically:

1. ✅ **Recognizes relative submit URLs**
   - `POST to /submit` → `https://example.com/submit`

2. ✅ **Actually scrapes data URLs**
   - Not just extracting tables
   - Fetches URL content
   - Extracts answer intelligently

3. ✅ **Handles $EMAIL placeholder**
   - Replaces in all URLs
   - Including data URLs

4. ✅ **Extracts secret codes**
   - From JSON: `{"secret": "ABC123"}`
   - From HTML: `<p>Secret code: XYZ789</p>`
   - From text: `demo-secret-123`

5. ✅ **Smart example detection**
   - Only uses demos (not real answers)
   - Scrapes when answer looks real

6. ✅ **Comprehensive logging**
   - Shows what was scraped
   - Shows what answer was found
   - Clear debugging trail

### Benefits:

- **Versatile:** Handles JSON, HTML, and text responses
- **Intelligent:** Knows when to scrape vs when to use examples
- **Robust:** Multiple fallback patterns
- **Transparent:** Detailed logging at every step
- **Compatible:** Doesn't break existing quiz types

---

## 8. Configuration

No configuration needed! All improvements work automatically:

- Scraping is automatic when needed
- Relative URLs resolved automatically
- Pattern matching built-in

To test with actual scraping, ensure network access and valid URLs.

---

## 9. Backward Compatibility

All existing functionality preserved:

- ✅ File downloads still work
- ✅ PDF/CSV/Excel extraction unchanged
- ✅ DataFrame analysis still used
- ✅ LLM fallback still available
- ✅ Demo quizzes still work

**New features are additive and non-breaking!**

---

## Summary

The quiz solver now:

1. ✅ Detects relative submit URLs (`/submit`)
2. ✅ Scrapes data URLs for answers
3. ✅ Extracts secret codes from JSON/HTML/text
4. ✅ Only uses demo examples when appropriate
5. ✅ Provides detailed scraping logs
6. ✅ Handles Question 2 format perfectly

**Ready for deployment!**
