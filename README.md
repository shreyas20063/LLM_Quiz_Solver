# LLM Quiz Solver

A FastAPI-based application for handling LLM quiz solving requests.

## Features

- POST endpoint at `/` to receive quiz solving requests
- Secret-based authentication
- Request validation using Pydantic
- Environment variable configuration
- Health check endpoint at `/health`
- **Headless browser extraction** with Selenium Chrome WebDriver
- **Automatic base64 decoding** from JavaScript-rendered pages
- Comprehensive logging for debugging

## Setup Instructions

### 1. Create Conda Environment

```bash
# Create a new conda environment with Python 3.11
conda create -n quiz_solver python=3.11

# Activate the environment
conda activate quiz_solver
```

### 2. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your actual credentials
# STUDENT_EMAIL=your@email.com
# STUDENT_SECRET=your_secret_here
```

### 4. Run the Application

```bash
# Run with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or run the main.py file
python main.py
```

The application will start on `http://localhost:8000`

## API Documentation

Once running, you can access:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative API docs (ReDoc): `http://localhost:8000/redoc`

## Testing the Endpoint

### Using curl

```bash
# Valid request (replace with your actual secret from .env)
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "secret": "your_secret_here",
    "url": "https://example.com/quiz"
  }'

# Expected response (200 OK):
# {"status": "received", "url": "https://example.com/quiz"}
```

```bash
# Invalid secret
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "secret": "wrong_secret",
    "url": "https://example.com/quiz"
  }'

# Expected response (403 Forbidden):
# {"detail": {"error": "Invalid secret"}}
```

```bash
# Malformed request (missing required field)
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "secret": "your_secret_here"
  }'

# Expected response (400 Bad Request with validation error)
```

### Using Python requests

```python
import requests

url = "http://localhost:8000/"
payload = {
    "email": "test@example.com",
    "secret": "your_secret_here",
    "url": "https://example.com/quiz"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

### Using HTTPie

```bash
# Install httpie: pip install httpie

http POST http://localhost:8000/ \
  email=test@example.com \
  secret=your_secret_here \
  url=https://example.com/quiz
```

## API Endpoints

### POST /

Accepts quiz solving requests.

**Request Body:**
```json
{
  "email": "user@example.com",
  "secret": "your_secret",
  "url": "https://quiz-url.com"
}
```

**Responses:**

- `200 OK`: Request received successfully
  ```json
  {
    "status": "received",
    "url": "https://quiz-url.com",
    "extracted_content": {
      "page_text": "Full text content from the page...",
      "decoded_text": "Decoded base64 content if found...",
      "has_decoded_content": true,
      "error": null
    }
  }
  ```

- `400 Bad Request`: Invalid or malformed request
  ```json
  {
    "detail": [
      {
        "loc": ["body", "email"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
  ```

- `403 Forbidden`: Invalid secret
  ```json
  {
    "detail": {
      "error": "Invalid secret"
    }
  }
  ```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Project Structure

```
llm_quiz_solver/
├── main.py                      # FastAPI application
├── quiz_solver.py               # Main quiz solving orchestrator
├── browser_handler.py           # Headless browser extraction with Selenium
├── data_extractor.py            # Data extraction module (PDFs, web, APIs)
├── data_analyzer.py             # Data analysis and task solver
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── .env.example                 # Example environment file
├── .gitignore                   # Git ignore rules
├── test_api.py                  # API endpoint tests
├── test_browser.py              # Browser extraction tests
├── test_data_extractor.py       # Data extractor tests
├── test_data_analyzer.py        # Data analyzer tests
├── test_quiz_solver.py          # Quiz solver tests
├── example_data_extraction.py   # Usage examples for data extractor
├── test_api.sh                  # Bash-based API tests
├── start_server.sh              # Server startup script
└── README.md                    # This file
```

## How Browser Extraction Works

The application uses Selenium with headless Chrome to extract content from quiz URLs:

1. **Headless Browser**: Uses Chrome WebDriver in headless mode (no GUI)
2. **JavaScript Rendering**: Waits for JavaScript to execute and render the page
3. **Content Extraction**: Extracts both visible text and HTML source
4. **Base64 Decoding**: Automatically detects and decodes base64-encoded content
   - Searches for `atob()` JavaScript patterns
   - Extracts standalone base64 strings
   - Returns decoded content if found

### Browser Features

- **Automatic ChromeDriver installation** via webdriver-manager
- **Configurable timeouts** (10 seconds for page load)
- **Multiple wait strategies** (body element, #result element)
- **Comprehensive error handling** with detailed logging
- **Chrome options**:
  - `--headless` - No GUI
  - `--no-sandbox` - Required for some environments
  - `--disable-dev-shm-usage` - Prevents memory issues
  - `--disable-gpu` - Better compatibility

## Development

To run in development mode with auto-reload:

```bash
uvicorn main:app --reload
```

## Testing Browser Extraction

To test the browser extraction functionality independently:

```bash
# Test browser extraction with various URLs
python test_browser.py
```

This will test:
- Simple HTML page extraction
- Base64 decoding functionality
- JavaScript-rendered content

## Data Extraction Module

The `data_extractor.py` module provides async functions for extracting data from various sources:

### Features

- **Download Files**: Download any file from a URL with automatic retry logic
- **PDF Table Extraction**: Extract tables from PDFs using pdfplumber
- **Web Table Extraction**: Extract HTML tables from web pages using pandas
- **API Calls**: Make GET/POST requests to APIs with error handling

### Available Functions

```python
# Async functions
await download_file(url, max_retries=3)           # Download file, returns bytes
await extract_pdf_tables(pdf_bytes, page_num=None) # Extract PDF tables, returns DataFrame
await extract_web_table(url)                      # Extract first table, returns DataFrame
await extract_all_web_tables(url)                 # Extract all tables, returns List[DataFrame]
await call_api(url, method="GET", data=None)      # Call API, returns dict

# Synchronous wrappers (for convenience)
download_file_sync(url)
extract_pdf_tables_sync(pdf_bytes, page_num=None)
extract_web_table_sync(url)
call_api_sync(url, method="GET", data=None)
```

### Testing Data Extractor

```bash
# Run comprehensive tests
python test_data_extractor.py

# Run usage examples
python example_data_extraction.py
```

The tests will:
- Download a sample PDF file
- Extract tables from the PDF
- Extract tables from Wikipedia
- Make API calls to test endpoints
- Demonstrate both async and sync usage

## Data Analyzer Module

The `data_analyzer.py` module provides intelligent task detection and data analysis:

### Features

- **Task Type Detection**: Automatically detects what operation to perform (sum, count, mean, max, min, filter, extract)
- **Smart Column Detection**: Extracts column names from natural language task descriptions
- **Page Number Extraction**: Identifies page numbers in task text
- **DataFrame Analysis**: Performs calculations on pandas DataFrames
- **Answer Formatting**: Converts results to JSON-serializable format

### Available Functions

```python
# Task detection
detect_task_type(task_text)                    # Returns: "sum", "count", "mean", etc.
extract_column_name(task_text)                 # Extracts column name from text
extract_page_number(task_text)                 # Extracts page number (0-indexed)

# Data analysis
analyze_dataframe(df, task_type, task_text)    # Performs analysis, returns result
format_answer(answer)                          # Converts to JSON-serializable format
get_dataframe_summary(df)                      # Returns DataFrame summary

# Complete pipeline
solve_task(df, task_text)                      # Detects task, analyzes, formats answer
```

### Example Usage

```python
import pandas as pd
from data_analyzer import solve_task

# Create sample data
df = pd.DataFrame({
    'Product': ['Laptop', 'Mouse', 'Keyboard'],
    'Price': [1200.0, 25.0, 75.0],
    'Stock': [15, 100, 50]
})

# Solve a task
result = solve_task(df, "Find the total 'Price'")
print(result['formatted_answer'])  # Output: 1300.0
```

### Supported Task Types

- **sum**: "Find the sum of Sales", "What is the total revenue?"
- **count**: "Count how many items", "Number of rows"
- **mean**: "Calculate average price", "Mean temperature"
- **max**: "Find maximum value", "Highest score"
- **min**: "Find minimum value", "Lowest price"
- **filter**: "Filter where status is active"
- **extract**: "Extract the product name"

### Testing Data Analyzer

```bash
# Run comprehensive tests
python test_data_analyzer.py
```

The tests will:
- Test task type detection with various phrases
- Test column name and page number extraction
- Test DataFrame analysis operations
- Test answer formatting for different types
- Test complete task solving pipeline

## Quiz Solver - Complete Pipeline

The `quiz_solver.py` module orchestrates the entire quiz solving process:

### Complete Workflow

```
1. User submits quiz URL
   ↓
2. Extract task using browser (Selenium)
   ↓
3. Parse task (question ID, submit URL, file URLs)
   ↓
4. Download data files (PDF, CSV, Excel)
   ↓
5. Extract tables into DataFrame
   ↓
6. Analyze data (detect task type, solve)
   ↓
7. Format answer (JSON serializable)
   ↓
8. Submit answer to quiz API
   ↓
9. Handle response (next URL or finish)
   ↓
10. Repeat until complete or timeout
```

### Main Functions

```python
# Complete quiz solving
solve_quiz(initial_url, email, secret, timeout_seconds=180)

# Parse task text
parse_task(task_text)  # Extract question ID, submit URL, file URLs

# Submit answer
submit_answer(submit_url, email, secret, quiz_url, answer)
```

### Testing Quiz Solver

```bash
# Run quiz solver tests
python test_quiz_solver.py
```

### Usage Example

Start the server and send a POST request:

```bash
# Start server
uvicorn main:app --reload

# Send request (in another terminal)
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "secret": "your_secret",
    "url": "https://quiz-url.com"
  }'
```

Response:
```json
{
  "status": "completed",
  "url": "https://quiz-url.com",
  "quiz_results": {
    "total_questions": 3,
    "correct_answers": 2,
    "total_time": 45.2,
    "questions": [...],
    "errors": [],
    "success": true
  }
}
```

### Features

- **Timeout handling**: Stops gracefully before timeout (default: 180s)
- **Multi-question support**: Follows URL chains automatically
- **Comprehensive logging**: Detailed logs at each step
- **Error resilience**: Continues on errors when possible
- **Result tracking**: Detailed per-question results

## Troubleshooting

1. **Import errors**: Make sure you've activated the conda environment and installed all dependencies
2. **Environment variable errors**: Ensure `.env` file exists and contains `STUDENT_SECRET`
3. **Port already in use**: Change the port in the command: `uvicorn main:app --port 8001`
4. **ChromeDriver issues**:
   - First run will download ChromeDriver automatically
   - Make sure Chrome browser is installed on your system
   - On macOS, you may need to allow ChromeDriver in Security & Privacy settings
5. **Browser timeout errors**: Increase timeout in `browser_handler.py` if pages load slowly
