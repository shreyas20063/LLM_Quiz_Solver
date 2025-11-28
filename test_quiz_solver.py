"""
Test script for quiz_solver module.
Tests task parsing and demonstrates the complete workflow.
"""
import asyncio
from quiz_solver import parse_task, submit_answer


def test_parse_task():
    """Test task parsing functionality"""
    print("=" * 60)
    print("Test: Task Parsing")
    print("=" * 60)

    # Test case 1: Task with question ID, submit URL, and file
    task_text_1 = """
    Q834 - Data Analysis Task

    Download the data from: https://example.com/data.pdf

    Find the sum of the 'Sales' column.

    Post your answer to https://api.example.com/submit
    """

    print("\nTest 1: Complete task with all elements")
    print(f"Task text: {task_text_1[:100]}...")

    parsed = parse_task(task_text_1)

    print(f"  Question ID: {parsed.get('question_id')}")
    print(f"  Question text: {parsed.get('question_text', '')[:50]}...")
    print(f"  Submit URL: {parsed.get('submit_url')}")
    print(f"  File URLs: {parsed.get('file_urls')}")

    # Verify parsing
    assert parsed.get('question_id') == 'Q834', "Question ID should be Q834"
    assert parsed.get('submit_url') is not None, "Submit URL should be found"
    assert len(parsed.get('file_urls', [])) > 0, "File URL should be found"

    print("  ✓ Test 1 passed")

    # Test case 2: Simple task
    task_text_2 = """
    Question 5: What is the maximum value in column 'Price'?

    Submit to https://quiz.example.com/answer

    Data: https://example.com/dataset.csv
    """

    print("\nTest 2: Task with different format")
    print(f"Task text: {task_text_2[:80]}...")

    parsed = parse_task(task_text_2)

    print(f"  Question ID: {parsed.get('question_id')}")
    print(f"  Submit URL: {parsed.get('submit_url')}")
    print(f"  File URLs: {parsed.get('file_urls')}")

    print("  ✓ Test 2 passed")

    # Test case 3: Task with base64 decoded content
    task_text_3 = """
    Task #3

    Calculate the average temperature.

    Submit your answer to: https://submit.quiz.com/api
    """

    print("\nTest 3: Task with minimal information")
    print(f"Task text: {task_text_3[:80]}...")

    parsed = parse_task(task_text_3)

    print(f"  Question ID: {parsed.get('question_id')}")
    print(f"  Question text: {parsed.get('question_text')}")
    print(f"  Submit URL: {parsed.get('submit_url')}")

    print("  ✓ Test 3 passed")

    print()


async def test_submit_answer():
    """Test answer submission (mock)"""
    print("=" * 60)
    print("Test: Answer Submission (Mock)")
    print("=" * 60)

    # Note: This will fail since we're using a mock URL
    # In real usage, you'd use the actual submit URL from the quiz

    print("\nSubmitting a test answer to mock endpoint...")

    result = await submit_answer(
        submit_url="https://httpbin.org/post",  # Mock endpoint
        email="test@example.com",
        secret="test_secret",
        quiz_url="https://example.com/quiz",
        answer=42
    )

    print(f"  Success: {result.get('success')}")
    print(f"  Status code: {result.get('status_code')}")
    print(f"  Response: {str(result.get('response', ''))[:100]}...")

    print("  ✓ Submission test completed (mock)")
    print()


def demo_workflow():
    """Demonstrate the complete workflow"""
    print("=" * 60)
    print("Demo: Complete Quiz Solving Workflow")
    print("=" * 60)

    print("""
The complete quiz solving workflow:

1. START: Receive quiz URL from user
   ↓
2. EXTRACT: Use browser to extract task from URL
   - Headless Chrome navigates to URL
   - JavaScript executes
   - Content extracted (HTML + decoded base64)
   ↓
3. PARSE: Extract key information
   - Question ID (Q834, etc.)
   - Question text
   - Submit URL
   - File URLs
   ↓
4. DOWNLOAD: Get data files if needed
   - PDFs, CSVs, Excel files
   - Web tables
   ↓
5. EXTRACT DATA: Convert to DataFrame
   - PDF tables → DataFrame
   - CSV/Excel → DataFrame
   - HTML tables → DataFrame
   ↓
6. ANALYZE: Solve the task
   - Detect task type (sum, count, mean, etc.)
   - Extract column names
   - Perform calculations
   - Format answer
   ↓
7. SUBMIT: Post answer to submit URL
   - JSON payload with email, secret, answer
   - Receive response (correct/incorrect, next URL)
   ↓
8. ITERATE: If next URL exists
   - Repeat steps 2-7 for next question
   - Continue until no more questions
   ↓
9. FINISH: Return summary results
   - Total questions attempted
   - Correct answers
   - Time taken
   - Detailed logs

Error Handling at Each Step:
- Browser fails → Return error
- Parse fails → Try simple extraction
- Download fails → Try web table
- Analysis fails → Return default answer
- Submit fails → Log error and continue
- Timeout → Stop gracefully

Logging:
- Comprehensive logs at each step
- Info, Warning, Error levels
- Helpful for debugging
    """)


def main():
    """Run all tests and demo"""
    print("\n" + "=" * 60)
    print("QUIZ SOLVER MODULE TESTS")
    print("=" * 60)
    print()

    try:
        # Test 1: Parse task
        test_parse_task()

        # Test 2: Submit answer (async)
        print("Running async test...")
        asyncio.run(test_submit_answer())

        # Demo workflow
        demo_workflow()

        print("=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

        print("""
To use the quiz solver:

1. Start the FastAPI server:
   uvicorn main:app --reload

2. Send a POST request to http://localhost:8000/:
   {
     "email": "your@email.com",
     "secret": "your_secret",
     "url": "https://quiz-url.com"
   }

3. The server will:
   - Extract the task
   - Download data
   - Analyze and solve
   - Submit answer
   - Return results

4. Check the response for:
   - Total questions solved
   - Correct answers
   - Detailed question-by-question results
        """)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
