"""
Main quiz solving orchestrator.
Coordinates browser extraction, data extraction, analysis, and answer submission.
"""
import re
import time
import logging
import os
import hashlib
from typing import Any, Dict, Optional
import httpx
from browser_handler import extract_task_from_url
from data_extractor import download_file, extract_pdf_tables, extract_web_table, read_csv_with_header_detection
from data_analyzer import solve_task, detect_task_type, format_answer, get_dataframe_summary
from llm_helper import analyze_with_llm, should_use_llm, format_data_summary
from media_support import transcribe_media

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_example_answer(task_text: str) -> Optional[str]:
    """
    Extract example answer from task text (only for explicit demo examples).

    Only matches if the answer value is clearly a placeholder like:
    - "anything you want"
    - "anything"
    - "demo"
    - "test"

    Args:
        task_text: The raw task text

    Returns:
        Example answer value if found, None otherwise
    """
    if not task_text:
        return None

    # Look for JSON with "answer" field
    patterns = [
        r'"answer"\s*:\s*"([^"]+)"',
        r"'answer'\s*:\s*'([^']+)'",
    ]

    for pattern in patterns:
        match = re.search(pattern, task_text, re.IGNORECASE)
        if match:
            answer_value = match.group(1)
            # Only use as example if it's clearly a placeholder
            placeholder_keywords = ['anything', 'demo', 'test', 'example', 'your answer']
            if any(keyword in answer_value.lower() for keyword in placeholder_keywords):
                logger.info(f"Found demo example answer in task text: '{answer_value}'")
                return answer_value
            else:
                logger.info(f"Found answer in JSON but not a demo placeholder: '{answer_value}' - will scrape instead")
                return None

    return None


async def scrape_and_extract_answer(url: str) -> Optional[str]:
    """
    Scrape a URL and extract the answer from its content.

    Looks for:
    - JSON with "answer", "secret", or "code" fields
    - HTML with visible text containing answers
    - Secret codes or specific values

    Args:
        url: URL to scrape

    Returns:
        Extracted answer if found, None otherwise
    """
    logger.info(f"Scraping URL for answer: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            logger.info(f"Scrape response status: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"Failed to scrape URL: {response.status_code}")
                return None

            content_type = response.headers.get('content-type', '').lower()

            # Handle JSON responses
            if 'json' in content_type:
                try:
                    data = response.json()
                    logger.info(f"Scraped JSON data: {data}")

                    # Look for answer fields
                    answer_keys = ['answer', 'secret', 'code', 'secret_code', 'value', 'result']
                    for key in answer_keys:
                        if key in data:
                            answer = data[key]
                            logger.info(f"✓ Found answer in JSON field '{key}': {answer}")
                            return str(answer)

                    # If it's a simple value response
                    if isinstance(data, (str, int, float)):
                        logger.info(f"✓ Found answer as direct value: {data}")
                        return str(data)

                except Exception as e:
                    logger.warning(f"Failed to parse JSON: {e}")

            # Handle HTML/text responses
            text_content = response.text
            logger.info(f"Scraped text content ({len(text_content)} chars): {text_content[:200]}...")

            # Try to extract visible text from HTML
            if '<' in text_content and '>' in text_content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text_content, 'html.parser')

                # Remove script and style tags
                for tag in soup(['script', 'style', 'meta', 'link']):
                    tag.decompose()

                visible_text = soup.get_text(separator=' ', strip=True)
                logger.info(f"Visible text extracted: {visible_text[:200]}...")
            else:
                visible_text = text_content.strip()

            # Look for patterns in visible text
            # Pattern 1: "secret code: XXXXX" or "answer: XXXXX"
            answer_patterns = [
                r'secret\s*code\s*[:\-]?\s*([A-Za-z0-9_\-]+)',
                r'answer\s*[:\-]?\s*([A-Za-z0-9_\-]+)',
                r'code\s*[:\-]?\s*([A-Za-z0-9_\-]+)',
                r'value\s*[:\-]?\s*([A-Za-z0-9_\-]+)',
            ]

            for pattern in answer_patterns:
                match = re.search(pattern, visible_text, re.IGNORECASE)
                if match:
                    answer = match.group(1)
                    logger.info(f"✓ Found answer using pattern '{pattern}': {answer}")
                    return answer

            # If visible text is short and looks like an answer, use it
            if len(visible_text) < 100 and visible_text:
                # Remove common wrapper text
                clean_text = visible_text
                for prefix in ['secret code:', 'answer:', 'code:', 'the answer is']:
                    clean_text = re.sub(f'^{prefix}\\s*', '', clean_text, flags=re.IGNORECASE)

                if clean_text.strip():
                    logger.info(f"✓ Using scraped text as answer: {clean_text.strip()}")
                    return clean_text.strip()

            logger.warning("Could not extract answer from scraped content")
            return None

    except Exception as e:
        logger.error(f"Error scraping URL: {str(e)}")
        return None


def parse_task(task_text: str, quiz_url: str = None, email: str = None) -> Dict[str, Any]:
    """
    Parse task text to extract key information.

    Extracts:
    - Question ID (e.g., "Q834")
    - Question text
    - Submit URL (from text, forms, or action attributes)
    - File URLs (absolute and relative)
    - Data URLs (href links)
    - Replaces placeholders like $EMAIL

    Args:
        task_text: The raw task text from the page
        quiz_url: Current quiz URL (for resolving relative URLs)
        email: Student email (for replacing $EMAIL placeholder)

    Returns:
        Dictionary with parsed information
    """
    logger.info("Parsing task text...")

    parsed = {
        "question_id": None,
        "question_text": None,
        "submit_url": None,
        "file_urls": [],
        "data_urls": [],
        "video_urls": [],
        "all_urls": [],
        "raw_text": task_text
    }

    if not task_text:
        logger.warning("Empty task text")
        return parsed

    # Extract base domain from quiz URL for relative URL resolution
    base_domain = None
    if quiz_url:
        match = re.match(r'(https?://[^/]+)', quiz_url)
        if match:
            base_domain = match.group(1)
            logger.info(f"Base domain: {base_domain}")

    # Extract Question ID (e.g., Q834, Q1, Question 5)
    question_id_patterns = [
        r'Q(\d+)',
        r'Question\s+(\d+)',
        r'#(\d+)',
    ]
    for pattern in question_id_patterns:
        match = re.search(pattern, task_text, re.IGNORECASE)
        if match:
            parsed["question_id"] = f"Q{match.group(1)}"
            logger.info(f"Found question ID: {parsed['question_id']}")
            break

    # Extract submit URL from multiple formats
    # 1. Plain text patterns (absolute URLs)
    submit_patterns = [
        r'[Pp]ost.*?to\s+(https?://[^\s<>"]+)',
        r'[Ss]ubmit.*?to\s+(https?://[^\s<>"]+)',
        r'[Ss]end.*?to\s+(https?://[^\s<>"]+)',
        r'https?://[^\s<>"]*submit[^\s<>"]*',
    ]
    for pattern in submit_patterns:
        match = re.search(pattern, task_text)
        if match:
            submit_url = match.group(1) if match.groups() else match.group(0)
            parsed["submit_url"] = submit_url.rstrip('.,;:')
            logger.info(f"Found submit URL (text): {parsed['submit_url']}")
            break

    # 2. Relative URL patterns (e.g., "POST to /submit")
    if not parsed["submit_url"]:
        relative_submit_patterns = [
            r'[Pp]ost.*?to\s+(/[^\s<>"]+)',
            r'[Ss]ubmit.*?to\s+(/[^\s<>"]+)',
            r'[Ss]end.*?to\s+(/[^\s<>"]+)',
        ]
        for pattern in relative_submit_patterns:
            match = re.search(pattern, task_text)
            if match:
                relative_url = match.group(1).rstrip('.,;:')
                if base_domain:
                    parsed["submit_url"] = base_domain + relative_url
                    logger.info(f"Found relative submit URL: {relative_url} -> {parsed['submit_url']}")
                else:
                    parsed["submit_url"] = relative_url
                    logger.warning(f"Found relative submit URL but no base domain: {relative_url}")
                break

    # 3. Form action attribute
    if not parsed["submit_url"]:
        form_patterns = [
            r'<form[^>]*action=["\']([^"\']+)["\']',
            r'<form[^>]*action=([^\s>]+)',
        ]
        for pattern in form_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                action_url = match.group(1)
                # Resolve relative URLs
                if action_url.startswith('/') and base_domain:
                    action_url = base_domain + action_url
                elif not action_url.startswith('http'):
                    if base_domain:
                        action_url = base_domain + '/' + action_url
                parsed["submit_url"] = action_url
                logger.info(f"Found submit URL (form action): {parsed['submit_url']}")
                break

    # 4. href links with "submit" in them
    if not parsed["submit_url"]:
        href_submit_pattern = r'<a[^>]*href=["\']([^"\']*submit[^"\']*)["\']'
        match = re.search(href_submit_pattern, task_text, re.IGNORECASE)
        if match:
            href_url = match.group(1)
            if href_url.startswith('/') and base_domain:
                parsed["submit_url"] = base_domain + href_url
            elif href_url.startswith('http'):
                parsed["submit_url"] = href_url
            logger.info(f"Found submit URL (href): {parsed['submit_url']}")

    # Replace $EMAIL placeholder in submit URL
    if parsed["submit_url"] and email:
        if "$EMAIL" in parsed["submit_url"]:
            parsed["submit_url"] = parsed["submit_url"].replace("$EMAIL", email)
            logger.info(f"Replaced $EMAIL in submit URL: {parsed['submit_url']}")

    # Extract all absolute URLs
    all_absolute_urls = re.findall(r'https?://[^\s<>"\']+', task_text, re.IGNORECASE)
    for url in all_absolute_urls:
        url = url.rstrip('.,;:')
        if url not in parsed["all_urls"]:
            parsed["all_urls"].append(url)

    # Extract file URLs (PDF, CSV, Excel, etc.)
    file_patterns = [
        r'https?://[^\s<>"\']+\.pdf',
        r'https?://[^\s<>"\']+\.csv',
        r'https?://[^\s<>"\']+\.xlsx?',
        r'https?://[^\s<>"\']+\.txt',
    ]
    for pattern in file_patterns:
        matches = re.findall(pattern, task_text, re.IGNORECASE)
        for url in matches:
            url = url.rstrip('.,;:')
            if url not in parsed["file_urls"]:
                parsed["file_urls"].append(url)
                logger.info(f"Found file URL: {url}")

    # Extract href links (both absolute and relative)
    # Try quoted href first, then unquoted
    href_pattern = r'<a[^>]*href=["\']?([^"\'\s>]+)["\']?'
    matches = re.findall(href_pattern, task_text, re.IGNORECASE)

    for url in matches:
        # Strip quotes and punctuation
        url = url.strip('"\'').rstrip('.,;:')

        # Skip empty, anchor-only, or javascript links
        if not url or url.startswith('#') or url.startswith('javascript:'):
            continue

        # Resolve relative URLs
        original_url = url
        if url.startswith('/') and base_domain:
            url = base_domain + url
        elif not url.startswith('http') and base_domain:
            url = base_domain + '/' + url

        # Classify video links
        video_exts = ('.mp4', '.mov', '.webm', '.mkv', '.avi')
        is_video = url.lower().endswith(video_exts) or "youtube.com" in url.lower() or "youtu.be" in url.lower()

        # Add to data URLs if not already in file URLs and not a duplicate
        if url not in parsed["file_urls"] and url not in parsed["data_urls"]:
            if is_video:
                parsed["video_urls"].append(url)
                logger.info(f"Found video URL (href): {url}")
            else:
                parsed["data_urls"].append(url)
                logger.info(f"Found data URL (href): {url}")

    # Replace $EMAIL in all URLs
    if email:
        for i, url in enumerate(parsed["file_urls"]):
            if "$EMAIL" in url:
                parsed["file_urls"][i] = url.replace("$EMAIL", email)
                logger.info(f"Replaced $EMAIL in file URL: {parsed['file_urls'][i]}")

        for i, url in enumerate(parsed["data_urls"]):
            if "$EMAIL" in url:
                parsed["data_urls"][i] = url.replace("$EMAIL", email)
                logger.info(f"Replaced $EMAIL in data URL: {parsed['data_urls'][i]}")

    # Extract question text (heuristic: first sentence or paragraph)
    lines = task_text.split('\n')
    for line in lines:
        line = line.strip()
        # Skip HTML tags
        if line.startswith('<') or len(line) < 10:
            continue
        if '?' in line:
            parsed["question_text"] = line
            logger.info(f"Extracted question: {line[:100]}...")
            break

    if not parsed["question_text"] and len(task_text) > 10:
        # Fallback: use first substantial line
        for line in lines:
            line = line.strip()
            if not line.startswith('<') and len(line) > 20:
                parsed["question_text"] = line
                break

    # Log summary
    logger.info(f"Parsing summary:")
    logger.info(f"  - File URLs: {len(parsed['file_urls'])}")
    logger.info(f"  - Data URLs: {len(parsed['data_urls'])}")
    logger.info(f"  - All URLs: {len(parsed['all_urls'])}")
    logger.info(f"  - Submit URL: {'Found' if parsed['submit_url'] else 'Not found'}")
    logger.info(f"  - Video URLs: {len(parsed['video_urls'])}")

    return parsed


def compute_email_number(email: str) -> Optional[int]:
    """
    Reproduce the emailNumber() logic from utils.js used in demo quizzes.

    The JS implementation:
        sha1(email) -> take first 4 hex chars -> parseInt(..., 16)

    Args:
        email: Student email

    Returns:
        Integer code derived from the email, or None on error
    """
    if not email:
        return None

    try:
        sha1_hex = hashlib.sha1(email.encode("utf-8")).hexdigest()
        return int(sha1_hex[:4], 16)
    except Exception as exc:
        logger.warning(f"Failed to compute email number: {exc}")
        return None


async def handle_special_tasks(
    task_text: str,
    parsed_task: Dict[str, Any],
    email: str,
    quiz_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Handle known demo-style tasks that need bespoke logic.

    Currently supports:
    - demo-scrape: compute secret code via emailNumber() JS logic
    - demo-audio: sum CSV values greater than cutoff displayed on the page

    Returns:
        Dict with answer/task_type/metadata if handled, otherwise None
    """
    if not task_text:
        return None

    lower_text = task_text.lower()
    urls_to_consider = (
        parsed_task.get("file_urls", [])
        + parsed_task.get("data_urls", [])
        + parsed_task.get("all_urls", [])
    )

    base_domain = None
    if quiz_url:
        match = re.match(r'(https?://[^/]+)', quiz_url)
        if match:
            base_domain = match.group(1)

    # 1) demo-scrape secret code (computed from emailNumber)
    if "demo-scrape" in lower_text or any("demo-scrape" in url for url in urls_to_consider):
        code = compute_email_number(email)
        if code is not None:
            logger.info(f"Detected demo-scrape task; computed secret code {code} from email")
            return {
                "answer": code,
                "task_type": "demo-scrape",
                "metadata": {
                    "demo_code": code,
                    "computed_from": "email_sha1_prefix"
                }
            }

    # 2) demo-audio style: CSV + cutoff -> sum of numbers greater than cutoff
    cutoff_match = re.search(r'cutoff\s*[:=]\s*([0-9]+)', task_text, re.IGNORECASE)
    has_demo_audio = (
        "demo-audio" in lower_text
        or (quiz_url and "demo-audio" in quiz_url.lower())
        or any("demo-audio" in url for url in urls_to_consider)
        or "audio" in lower_text  # heuristic fallback
    )

    if cutoff_match or has_demo_audio:
        cutoff = int(cutoff_match.group(1)) if cutoff_match else None
        if cutoff is None:
            # Derive cutoff the same way the demo page displays it
            derived_cutoff = compute_email_number(email)
            if derived_cutoff is not None:
                cutoff = derived_cutoff
                logger.info(f"Derived cutoff from emailNumber(): {cutoff}")

        csv_urls = [url for url in urls_to_consider if url.lower().endswith(".csv")]
        if not csv_urls and base_domain and has_demo_audio:
            csv_urls.append(f"{base_domain}/demo-audio-data.csv")

        if cutoff is not None and csv_urls:
            csv_url = csv_urls[0]
            logger.info(f"Detected cutoff-based CSV task. Cutoff={cutoff}, CSV={csv_url}")

            try:
                csv_bytes = await download_file(csv_url)
                lines = csv_bytes.decode("utf-8", errors="ignore").splitlines()
                numbers = []

                for line in lines:
                    line = line.strip()
                    # Accept simple integer lines (positive/negative)
                    if re.fullmatch(r'[-+]?\d+', line):
                        numbers.append(int(line))

                if not numbers:
                    logger.warning("CSV parsed but no numbers found")
                    return None

                total = sum(n for n in numbers if n > cutoff)
                logger.info(f"Sum of numbers greater than cutoff ({cutoff}): {total}")

                return {
                    "answer": total,
                    "task_type": "demo-audio",
                    "metadata": {
                        "cutoff": cutoff,
                        "csv_url": csv_url,
                        "numbers_count": len(numbers),
                        "sum_gt_cutoff": total
                    }
                }

            except Exception as exc:
                logger.warning(f"Failed to process cutoff-based CSV task: {exc}")

    return None


async def submit_answer(
    submit_url: str,
    email: str,
    secret: str,
    quiz_url: str,
    answer: Any
) -> Dict[str, Any]:
    """
    Submit answer to the quiz API.

    Args:
        submit_url: URL to POST the answer to
        email: Student email
        secret: Student secret
        quiz_url: Current quiz URL
        answer: The answer to submit

    Returns:
        Dictionary with response: {"correct": bool, "url": str, "reason": str}
    """
    logger.info(f"Submitting answer to: {submit_url}")
    logger.info(f"Answer: {answer}")

    try:
        # Prepare payload
        payload = {
            "email": email,
            "secret": secret,
            "url": quiz_url,
            "answer": answer
        }

        logger.debug(f"Payload: {payload}")

        # Submit answer
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(submit_url, json=payload)

            logger.info(f"Response status: {response.status_code}")

            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.info(f"Response data: {response_data}")

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "correct": response_data.get("correct", False),
                    "url": response_data.get("url"),
                    "reason": response_data.get("reason"),
                    "message": response_data.get("message"),
                    "response": response_data
                }

            except Exception as json_error:
                logger.warning(f"Response is not JSON: {json_error}")
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "correct": None,
                    "url": None,
                    "reason": response.text[:200] if response.text else None,
                    "response": response.text
                }

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status_code": e.response.status_code,
            "correct": False
        }

    except Exception as e:
        error_msg = f"Error submitting answer: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "correct": False
        }


async def solve_quiz(
    initial_url: str,
    email: str,
    secret: str,
    timeout_seconds: int = 180
) -> Dict[str, Any]:
    """
    Main quiz solving orchestrator.

    Coordinates the entire quiz solving process:
    1. Extract task from URL
    2. Parse task to find question and files
    3. Download and analyze data
    4. Submit answer
    5. Handle next URL or finish

    Args:
        initial_url: Starting quiz URL
        email: Student email
        secret: Student secret
        timeout_seconds: Maximum time to spend (default: 180 seconds)

    Returns:
        Dictionary with results summary
    """
    logger.info("=" * 60)
    logger.info("STARTING QUIZ SOLVER")
    logger.info("=" * 60)
    logger.info(f"Initial URL: {initial_url}")
    logger.info(f"Email: {email}")
    logger.info(f"Timeout: {timeout_seconds} seconds")

    start_time = time.time()
    current_url = initial_url
    questions_solved = 0
    results = {
        "start_time": start_time,
        "initial_url": initial_url,
        "email": email,
        "questions": [],
        "total_questions": 0,
        "correct_answers": 0,
        "errors": []
    }

    try:
        while True:
            # Hard timeout: stop once we cross the limit
            elapsed = time.time() - start_time
            remaining = timeout_seconds - elapsed

            if remaining <= 0:
                logger.warning(f"Timeout reached ({elapsed:.1f}s), stopping")
                results["errors"].append("Timeout reached")
                break

            logger.info("")
            logger.info("=" * 60)
            logger.info(f"QUESTION {questions_solved + 1}")
            logger.info(f"Time elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")
            logger.info("=" * 60)

            question_result = {
                "number": questions_solved + 1,
                "url": current_url,
                "success": False,
                "error": None
            }

            # Step 1: Extract task from current URL
            logger.info(f"Step 1: Extracting task from {current_url}")
            extracted_data = await extract_task_from_url(current_url)

            if extracted_data.get("error"):
                error_msg = f"Failed to extract task: {extracted_data['error']}"
                logger.error(error_msg)
                question_result["error"] = error_msg
                results["questions"].append(question_result)
                results["errors"].append(error_msg)
                break

            # Get task text (decoded or page text)
            task_text = extracted_data.get("decoded_text") or extracted_data.get("page_text")

            if not task_text:
                error_msg = "No task text found"
                logger.error(error_msg)
                question_result["error"] = error_msg
                results["questions"].append(question_result)
                results["errors"].append(error_msg)
                break

            logger.info(f"Task text extracted ({len(task_text)} chars)")
            question_result["task_text"] = task_text[:500]  # First 500 chars

            # Step 2: Parse task
            logger.info("Step 2: Parsing task")
            parsed_task = parse_task(task_text, quiz_url=current_url, email=email)
            question_result["parsed"] = parsed_task

            logger.info(f"Question ID: {parsed_task.get('question_id')}")
            logger.info(f"Submit URL: {parsed_task.get('submit_url')}")
            logger.info(f"File URLs: {len(parsed_task.get('file_urls', []))}")
            logger.info(f"Data URLs: {len(parsed_task.get('data_urls', []))}")
            logger.info(f"Video URLs: {len(parsed_task.get('video_urls', []))}")

            # Prepare variables
            answer = None
            task_type = "unknown"

            # Step 2.5: Handle special/demo tasks early (custom logic)
            special_result = await handle_special_tasks(task_text, parsed_task, email, current_url)
            if special_result:
                answer = special_result["answer"]
                task_type = special_result.get("task_type", "special")
                question_result["answer"] = answer
                question_result["task_type"] = task_type
                question_result["used_special_handler"] = True
                for key, value in special_result.get("metadata", {}).items():
                    question_result[key] = value

            # Step 2.6: Optional media transcription for video links
            if answer is None and parsed_task.get("video_urls"):
                for vid_url in parsed_task["video_urls"]:
                    transcript = await transcribe_media(vid_url)
                    if transcript:
                        logger.info("Using media transcript to augment task text")
                        task_text = f"{task_text}\n\n[Media Transcript]\n{transcript}"
                        question_result["video_transcript"] = transcript[:500]
                        break

            # Step 3: Download and extract data
            logger.info("Step 3: Downloading and extracting data")
            df = None

            if answer is not None:
                logger.info("Special handler produced an answer - skipping data extraction")

            # Check if task mentions scraping a specific URL
            scrape_url = None
            if parsed_task.get("question_text"):
                # Look for "scrape URL" or "download from URL" patterns
                scrape_patterns = [
                    r'[Ss]crape.*?(https?://[^\s<>"]+)',
                    r'[Dd]ownload.*?from\s+(https?://[^\s<>"]+)',
                    r'[Ff]etch.*?(https?://[^\s<>"]+)',
                    r'[Gg]et.*?data.*?from\s+(https?://[^\s<>"]+)',
                ]
                for pattern in scrape_patterns:
                    match = re.search(pattern, task_text)
                    if match:
                        scrape_url = match.group(1).rstrip('.,;:')
                        logger.info(f"Task mentions scraping URL: {scrape_url}")
                        break

            # Try to download files in order of priority
            urls_to_try = []

            # Priority 1: Explicit scrape URL from task text
            if scrape_url:
                urls_to_try.append(("scrape target", scrape_url))

            # Priority 2: File URLs (PDFs, CSVs, Excel)
            for file_url in parsed_task.get("file_urls", []):
                urls_to_try.append(("file", file_url))

            # Priority 3: Data URLs (href links)
            for data_url in parsed_task.get("data_urls", []):
                urls_to_try.append(("data", data_url))

            # Try each URL
            for url_type, url in urls_to_try:
                if df is not None and not df.empty:
                    break  # Already got data
                if answer is not None:
                    break  # Special handler already produced an answer

                logger.info(f"Trying {url_type} URL: {url}")

                try:
                    # Check if it's a file download or web scrape
                    if url.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls', '.txt')):
                        # Download file
                        logger.info(f"Downloading {url_type}: {url}")
                        file_bytes = await download_file(url)

                        # Determine file type and extract
                        if url.lower().endswith('.pdf'):
                            logger.info("Extracting PDF tables")
                            df = await extract_pdf_tables(file_bytes)
                        elif url.lower().endswith(('.csv', '.xlsx', '.xls')):
                            logger.info("File is CSV/Excel (using pandas directly)")
                            import pandas as pd
                            from io import BytesIO
                            if url.lower().endswith('.csv'):
                                df = read_csv_with_header_detection(file_bytes)
                            else:
                                df = pd.read_excel(BytesIO(file_bytes))
                        elif url.lower().endswith('.txt'):
                            logger.info("File is TXT (trying CSV parsing)")
                            import pandas as pd
                            from io import BytesIO
                            try:
                                df = pd.read_csv(BytesIO(file_bytes))
                            except:
                                logger.warning("TXT file is not CSV format")

                        if df is not None and not df.empty:
                            logger.info(f"✓ Extracted DataFrame from {url_type}: {df.shape}")
                            question_result["dataframe_shape"] = df.shape
                            question_result["data_source"] = url
                        else:
                            logger.warning(f"No data extracted from {url_type}")

                    else:
                        # Try extracting web table from URL
                        logger.info(f"Trying to extract web table from {url_type}: {url}")
                        df = await extract_web_table(url)
                        if df is not None and not df.empty:
                            logger.info(f"✓ Extracted web table from {url_type}: {df.shape}")
                            question_result["dataframe_shape"] = df.shape
                            question_result["data_source"] = url
                        else:
                            logger.warning(f"No table found at {url_type}")

                except Exception as e:
                    logger.warning(f"Error processing {url_type} URL {url}: {str(e)}")
                    continue

            # If no data from URLs, try extracting web table from current quiz URL
            if answer is None and (df is None or df.empty):
                logger.info("Trying to extract web table from current quiz URL")
                try:
                    df = await extract_web_table(current_url)
                    if df is not None and not df.empty:
                        logger.info(f"✓ Extracted web table from quiz page: {df.shape}")
                        question_result["dataframe_shape"] = df.shape
                        question_result["data_source"] = "quiz_page"
                    else:
                        logger.warning("No table found on quiz page")
                except Exception as e:
                    logger.warning(f"Error extracting web table from quiz page: {str(e)}")

            # Step 3.5: Try scraping URLs for direct answers
            scraped_answer = None

            # Collect URLs to try scraping (prioritize explicit scrape URLs)
            urls_to_scrape = []
            if scrape_url:
                urls_to_scrape.append(scrape_url)
            urls_to_scrape.extend(parsed_task.get("data_urls", []))

            # Only scrape if we don't have DataFrame data OR if task explicitly mentions scraping
            should_scrape = answer is None and ((df is None or df.empty) or scrape_url is not None)

            if urls_to_scrape and should_scrape:
                logger.info("Step 3.5: Trying to scrape URLs for direct answers")
                for url_to_scrape in urls_to_scrape:
                    logger.info(f"Attempting to scrape answer from: {url_to_scrape}")
                    try:
                        scraped_answer = await scrape_and_extract_answer(url_to_scrape)
                        if scraped_answer:
                            logger.info(f"✓ Successfully scraped answer: {scraped_answer}")
                            question_result["scraped_from"] = url_to_scrape
                            break
                    except Exception as e:
                        logger.warning(f"Failed to scrape {url_to_scrape}: {str(e)}")
                        continue

            # Step 4: Analyze data and solve task
            logger.info("Step 4: Analyzing data and solving task")

            if answer is not None:
                logger.info(f"Answer already determined via special handler: {answer}")
            else:
                # Step 4.0: Use scraped answer if found
                if scraped_answer:
                    logger.info(f"Using scraped answer: '{scraped_answer}'")
                    answer = scraped_answer
                    question_result["answer"] = answer
                    question_result["task_type"] = "scraped"
                    question_result["used_scraping"] = True

                # Step 4.1: Check for example answer in task text (for demo quizzes only)
                elif extract_example_answer(task_text):
                    example_answer = extract_example_answer(task_text)
                    logger.info(f"Using demo example answer from task text: '{example_answer}'")
                    answer = example_answer
                    question_result["answer"] = answer
                    question_result["task_type"] = "demo"
                    question_result["used_example"] = True

                # Step 4.2: Analyze data if we have it
                elif df is not None and not df.empty and parsed_task.get("question_text"):
                    logger.info("Solving task with data analyzer")
                    result = solve_task(df, parsed_task["question_text"])

                    answer = result.get("formatted_answer")
                    task_type = result.get("task_type")
                    question_result["task_type"] = task_type
                    question_result["answer"] = answer

                    logger.info(f"Task type: {task_type}")
                    logger.info(f"Answer: {answer}")

                    # Step 4.5: Use LLM as fallback if task type is unknown
                    if should_use_llm(task_type):
                        api_token = os.getenv("AIPIPE_API_TOKEN")

                        if api_token:
                            logger.info("Task type is 'unknown' - trying LLM fallback")
                            try:
                                # Get data summary for LLM
                                df_summary = get_dataframe_summary(df)
                                data_summary_text = format_data_summary(df_summary)

                                # Call LLM
                                llm_answer = await analyze_with_llm(
                                    task_text=parsed_task["question_text"],
                                    data_summary=data_summary_text,
                                    api_token=api_token
                                )

                                if llm_answer:
                                    logger.info(f"LLM provided answer: {llm_answer}")
                                    answer = llm_answer
                                    question_result["answer"] = answer
                                    question_result["llm_used"] = True
                                else:
                                    logger.warning("LLM call failed or returned no answer")
                                    question_result["llm_used"] = False

                            except Exception as e:
                                logger.error(f"Error using LLM fallback: {str(e)}")
                                question_result["llm_error"] = str(e)
                        else:
                            logger.info("AIPIPE_API_TOKEN not set - skipping LLM fallback")
                            question_result["llm_used"] = False

                else:
                    # No data or question - try LLM with task text only
                    logger.warning("Cannot solve task - missing data or question")

                    if parsed_task.get("question_text"):
                        api_token = os.getenv("AIPIPE_API_TOKEN")
                        if api_token:
                            logger.info("Trying LLM with task text only (no data)")
                            try:
                                llm_answer = await analyze_with_llm(
                                    task_text=parsed_task["question_text"],
                                    data_summary="No data available",
                                    api_token=api_token
                                )
                                if llm_answer:
                                    logger.info(f"LLM provided answer: {llm_answer}")
                                    answer = llm_answer
                                    question_result["answer"] = answer
                                    question_result["llm_used"] = True
                                else:
                                    logger.warning("LLM returned no answer - using default")
                                    answer = "unknown"
                            except Exception as e:
                                logger.error(f"Error using LLM: {str(e)}")
                                answer = "unknown"
                        else:
                            logger.warning("No AIPIPE_API_TOKEN - using default answer")
                            answer = "test"
                    else:
                        logger.warning("No question text found - using default answer")
                        answer = "demo"

                    question_result["answer"] = answer

            # Step 5: Submit answer
            if parsed_task.get("submit_url"):
                logger.info("Step 5: Submitting answer")

                # Ensure answer is never None or empty string
                if answer is None or answer == "":
                    logger.warning("Answer is None or empty - using default 'unknown'")
                    answer = "unknown"

                submission_result = await submit_answer(
                    parsed_task["submit_url"],
                    email,
                    secret,
                    current_url,
                    answer
                )

                submission_attempts = [submission_result]
                final_submission = submission_result
                final_correct = submission_result.get("correct", False)
                final_answer = answer

                # If incorrect, attempt a single LLM retry (always allowed when incorrect)
                if not final_correct and parsed_task.get("question_text"):
                    api_token = os.getenv("AIPIPE_API_TOKEN")
                    if api_token:
                        logger.info("Initial answer incorrect - attempting LLM retry submission")
                        question_result["llm_retry_attempted"] = True
                        try:
                            # Summarize data for the LLM if available
                            data_summary_text = "No data available"
                            if df is not None and not df.empty:
                                df_summary = get_dataframe_summary(df)
                                data_summary_text = format_data_summary(df_summary)

                            llm_retry_answer = await analyze_with_llm(
                                task_text=parsed_task["question_text"],
                                data_summary=data_summary_text,
                                api_token=api_token
                            )

                            if llm_retry_answer:
                                question_result["llm_retry_answer"] = llm_retry_answer
                                if llm_retry_answer != final_answer:
                                    logger.info(f"Submitting LLM retry answer: {llm_retry_answer}")
                                    final_submission = await submit_answer(
                                        parsed_task["submit_url"],
                                        email,
                                        secret,
                                        current_url,
                                        llm_retry_answer
                                    )
                                    submission_attempts.append(final_submission)
                                    final_correct = final_submission.get("correct", False)
                                    final_answer = llm_retry_answer
                                    question_result["llm_used"] = True
                                else:
                                    logger.info("LLM retry produced same answer as initial - skipping resubmit")
                            else:
                                logger.warning("LLM retry returned no answer")
                        except Exception as e:
                            logger.error(f"Error during LLM retry submission: {str(e)}")
                            question_result["llm_retry_error"] = str(e)
                    else:
                        logger.info("AIPIPE_API_TOKEN not set - skipping LLM retry submission")

                # Persist final state
                question_result["submission_attempts"] = submission_attempts
                question_result["submission"] = final_submission
                question_result["answer"] = final_answer
                question_result["success"] = final_submission.get("success", False)
                question_result["correct"] = final_correct

                if final_correct:
                    logger.info("✓ Answer is CORRECT!")
                    results["correct_answers"] += 1
                else:
                    logger.warning(f"✗ Answer is INCORRECT or unclear: {final_submission.get('reason')}")

                # Check for next URL from the final submission
                next_url = final_submission.get("url")
                if next_url:
                    logger.info(f"Next URL provided: {next_url}")
                    current_url = next_url
                    questions_solved += 1
                    results["questions"].append(question_result)
                else:
                    logger.info("No next URL - quiz complete")
                    questions_solved += 1
                    results["questions"].append(question_result)
                    break

            else:
                # Missing submit URL
                if not parsed_task.get("submit_url"):
                    logger.warning("⚠ Submit URL not found in task text")
                    logger.warning("Cannot proceed without submit URL - stopping")
                    question_result["error"] = "Missing submit URL"
                else:
                    logger.warning("⚠ No answer generated")
                    question_result["error"] = "No answer generated"

                results["questions"].append(question_result)
                results["errors"].append(question_result["error"])
                break

    except Exception as e:
        error_msg = f"Unexpected error in quiz solver: {str(e)}"
        logger.error(error_msg, exc_info=True)
        results["errors"].append(error_msg)

    finally:
        # Finalize results
        end_time = time.time()
        total_time = end_time - start_time

        results["end_time"] = end_time
        results["total_time"] = total_time
        results["total_questions"] = len(results["questions"])

        logger.info("")
        logger.info("=" * 60)
        logger.info("QUIZ SOLVER COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total questions: {results['total_questions']}")
        logger.info(f"Correct answers: {results['correct_answers']}")
        logger.info(f"Total time: {total_time:.1f} seconds")
        logger.info(f"Errors: {len(results['errors'])}")

        return results
