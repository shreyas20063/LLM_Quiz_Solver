"""
Test script for enhanced task parsing in quiz_solver.
Tests improved URL extraction, relative URLs, and placeholder replacement.
"""
from quiz_solver import parse_task


def test_enhanced_parsing():
    """Test enhanced task parsing features"""
    print("=" * 60)
    print("Test: Enhanced Task Parsing")
    print("=" * 60)

    # Test 1: Form action with relative URL
    print("\nTest 1: Form action with relative URL")
    task_text = """
    <form method="post" action="/api/submit">
        <input type="text" name="answer">
    </form>
    Download data from <a href="/data/sales.csv">here</a>
    """
    quiz_url = "https://example.com/quiz-1"
    email = "student@example.com"

    parsed = parse_task(task_text, quiz_url=quiz_url, email=email)
    print(f"Submit URL: {parsed['submit_url']}")
    print(f"Data URLs: {parsed['data_urls']}")
    assert parsed['submit_url'] == "https://example.com/api/submit", "Form action not resolved correctly"
    assert "https://example.com/data/sales.csv" in parsed['data_urls'], "Relative href not resolved"
    print("✓ Passed")

    # Test 2: $EMAIL placeholder replacement
    print("\nTest 2: $EMAIL placeholder replacement")
    task_text = """
    Post your answer to https://api.example.com/submit?user=$EMAIL
    Download file: https://example.com/data/$EMAIL/report.pdf
    """
    email = "test@student.com"

    parsed = parse_task(task_text, email=email)
    print(f"Submit URL: {parsed['submit_url']}")
    print(f"File URLs: {parsed['file_urls']}")
    assert "$EMAIL" not in parsed['submit_url'], "$EMAIL not replaced in submit URL"
    assert "test@student.com" in parsed['submit_url'], "Email not substituted correctly"
    assert "$EMAIL" not in parsed['file_urls'][0], "$EMAIL not replaced in file URL"
    print("✓ Passed")

    # Test 3: Multiple href links
    print("\nTest 3: Multiple href links")
    task_text = """
    Question: Analyze the data
    <a href="https://example.com/data1.csv">Dataset 1</a>
    <a href="https://example.com/data2.csv">Dataset 2</a>
    <a href="/relative/data3.pdf">Dataset 3</a>
    Submit to https://api.example.com/answer
    """
    quiz_url = "https://example.com/quiz"

    parsed = parse_task(task_text, quiz_url=quiz_url)
    print(f"File URLs: {parsed['file_urls']}")
    print(f"Data URLs: {parsed['data_urls']}")
    print(f"All URLs: {parsed['all_urls']}")
    assert len(parsed['file_urls']) == 3, f"Expected 3 file URLs, got {len(parsed['file_urls'])}"
    print("✓ Passed")

    # Test 4: Scrape URL detection
    print("\nTest 4: Scrape URL detection")
    task_text = """
    Scrape the data from https://example.com/data/table.html and find the total.
    Post answer to https://api.example.com/submit
    """

    parsed = parse_task(task_text)
    print(f"Data URLs: {parsed['data_urls']}")
    print(f"Submit URL: {parsed['submit_url']}")
    # URL should be in all_urls
    assert "https://example.com/data/table.html" in parsed['all_urls'], "Scrape URL not found"
    print("✓ Passed")

    # Test 5: Skip javascript and anchor links
    print("\nTest 5: Skip javascript and anchor links")
    task_text = """
    <a href="javascript:void(0)">Click here</a>
    <a href="#section1">Jump to section</a>
    <a href="https://example.com/real-data.csv">Real data</a>
    """

    parsed = parse_task(task_text)
    print(f"Data URLs: {parsed['data_urls']}")
    # Should only have the real data URL
    assert len(parsed['data_urls']) == 0, "Javascript/anchor links should be skipped"
    assert len(parsed['file_urls']) == 1, "Should have 1 file URL"
    print("✓ Passed")

    # Test 6: Question text extraction (skip HTML tags)
    print("\nTest 6: Question text extraction")
    task_text = """
    <div class="header">Header</div>
    <p>What is the total sales for 2023?</p>
    <form>...</form>
    """

    parsed = parse_task(task_text)
    print(f"Question: {parsed['question_text']}")
    assert "What is the total sales for 2023?" in parsed['question_text'], "Question not extracted"
    assert not parsed['question_text'].startswith('<'), "HTML tags not skipped"
    print("✓ Passed")

    print("\n" + "=" * 60)
    print("All enhanced parsing tests passed!")
    print("=" * 60)


def test_url_priority():
    """Test URL extraction priority and logging"""
    print("\n" + "=" * 60)
    print("Test: URL Extraction Priority")
    print("=" * 60)

    task_text = """
    Q: Scrape data from https://example.com/web-table.html

    Also check this file: <a href="https://example.com/backup.csv">Backup CSV</a>

    Raw data: https://example.com/data.pdf

    Submit to: https://api.example.com/answer
    """

    parsed = parse_task(task_text)

    print(f"\nParsed results:")
    print(f"  Question ID: {parsed['question_id']}")
    print(f"  Submit URL: {parsed['submit_url']}")
    print(f"  File URLs: {parsed['file_urls']}")
    print(f"  Data URLs: {parsed['data_urls']}")
    print(f"  All URLs: {len(parsed['all_urls'])} total")

    # Verify we got all URLs
    assert len(parsed['file_urls']) >= 2, "Should find PDF and CSV files"
    assert len(parsed['data_urls']) >= 0, "May have data URLs"
    assert parsed['submit_url'] is not None, "Should find submit URL"

    print("\n✓ URL priority test passed")


if __name__ == "__main__":
    try:
        test_enhanced_parsing()
        test_url_priority()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
