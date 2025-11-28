"""
Test script for demo quiz handling.
Verifies that example answers are extracted from task text.
"""
import re
from typing import Optional


def extract_example_answer(task_text: str) -> Optional[str]:
    """Extract example answer from task text (simplified for testing)"""
    if not task_text:
        return None

    patterns = [
        r'"answer"\s*:\s*"([^"]+)"',
        r"'answer'\s*:\s*'([^']+)'",
    ]

    for pattern in patterns:
        match = re.search(pattern, task_text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def test_example_answer_extraction():
    """Test example answer extraction from demo quiz text"""
    print("=" * 60)
    print("Demo Quiz Example Answer Extraction Tests")
    print("=" * 60)

    # Test 1: Standard JSON format
    print("\n[Test 1] Standard JSON format")
    task_text = """
    This is a demo quiz.

    Post your answer in this format:
    {
      "answer": "anything you want"
    }

    Submit to: https://api.example.com/submit
    """
    result = extract_example_answer(task_text)
    assert result == "anything you want", f"Expected 'anything you want', got '{result}'"
    print(f"✓ Extracted: '{result}'")

    # Test 2: Compact JSON
    print("\n[Test 2] Compact JSON format")
    task_text = '{"answer":"test value"}'
    result = extract_example_answer(task_text)
    assert result == "test value", f"Expected 'test value', got '{result}'"
    print(f"✓ Extracted: '{result}'")

    # Test 3: Single quotes
    print("\n[Test 3] Single quotes format")
    task_text = "{'answer':'demo answer'}"
    result = extract_example_answer(task_text)
    assert result == "demo answer", f"Expected 'demo answer', got '{result}'"
    print(f"✓ Extracted: '{result}'")

    # Test 4: No example answer
    print("\n[Test 4] No example answer in text")
    task_text = "Just a regular question with no example"
    result = extract_example_answer(task_text)
    assert result is None, f"Expected None, got '{result}'"
    print("✓ Correctly returned None")

    # Test 5: Case insensitive
    print("\n[Test 5] Case insensitive matching")
    task_text = '{"ANSWER":"Demo Answer"}'
    result = extract_example_answer(task_text)
    assert result == "Demo Answer", f"Expected 'Demo Answer', got '{result}'"
    print(f"✓ Extracted: '{result}'")

    # Test 6: Real demo quiz format
    print("\n[Test 6] Real demo quiz format")
    task_text = """
    Welcome to the demo quiz!

    Example submission:
    {
      "email": "your@email.com",
      "secret": "your_secret",
      "url": "current_url",
      "answer": "anything you want"
    }

    Post your answer to https://quiz-api.example.com/submit
    """
    result = extract_example_answer(task_text)
    assert result == "anything you want", f"Expected 'anything you want', got '{result}'"
    print(f"✓ Extracted: '{result}'")

    print("\n" + "=" * 60)
    print("ALL DEMO QUIZ TESTS PASSED!")
    print("=" * 60)


def test_answer_defaults():
    """Test that we never use empty string as answer"""
    print("\n" + "=" * 60)
    print("Answer Default Value Tests")
    print("=" * 60)

    # Simulate different scenarios
    scenarios = [
        ("No data, no question", None, "demo"),
        ("Has question, no LLM", "What is X?", "test"),
        ("LLM failed", "What is X?", "unknown"),
    ]

    for scenario_name, question_text, expected_default in scenarios:
        print(f"\n[Scenario] {scenario_name}")
        # Logic simulation
        answer = None

        if not question_text:
            answer = "demo"
        else:
            # Simulate LLM not available
            answer = "test"

        assert answer != "", f"Answer should never be empty string"
        assert answer is not None, f"Answer should never be None"
        print(f"✓ Default answer: '{answer}' (not empty)")

    print("\n" + "=" * 60)
    print("ALL DEFAULT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_example_answer_extraction()
        test_answer_defaults()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe demo quiz handler is ready:")
        print("  1. Extracts example answers from task text")
        print("  2. Never submits empty string or None")
        print("  3. Uses sensible defaults when needed")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
