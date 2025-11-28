"""
Test script for data_analyzer module.
Tests task detection, data analysis, and answer formatting.
"""
import pandas as pd
import numpy as np
from data_analyzer import (
    detect_task_type,
    extract_column_name,
    extract_page_number,
    analyze_dataframe,
    format_answer,
    get_dataframe_summary,
    solve_task
)


def test_detect_task_type():
    """Test task type detection"""
    print("=" * 60)
    print("Test 1: Task Type Detection")
    print("=" * 60)

    test_cases = [
        ("Find the sum of sales", "sum"),
        ("What is the total revenue?", "sum"),
        ("Count how many items", "count"),
        ("How many rows are there?", "count"),
        ("Calculate the average price", "mean"),
        ("Find the maximum value", "max"),
        ("What is the minimum temperature?", "min"),
        ("Filter where status is active", "filter"),
        ("Extract the product name", "extract"),
    ]

    passed = 0
    for task_text, expected in test_cases:
        result = detect_task_type(task_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{task_text[:40]}...' -> {result} (expected: {expected})")
        if result == expected:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    print()


def test_extract_column_name():
    """Test column name extraction"""
    print("=" * 60)
    print("Test 2: Column Name Extraction")
    print("=" * 60)

    test_cases = [
        ("Find the sum of 'Sales'", "Sales"),
        ("Count the Price column", "Price"),
        ("What is the total 'Revenue'?", "Revenue"),
        ("Average of Temperature", "Temperature"),
    ]

    for task_text, expected in test_cases:
        result = extract_column_name(task_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{task_text}' -> {result} (expected: {expected})")

    print()


def test_extract_page_number():
    """Test page number extraction"""
    print("=" * 60)
    print("Test 3: Page Number Extraction")
    print("=" * 60)

    test_cases = [
        ("Extract from page 2", 1),  # 0-indexed
        ("Data on page 5", 4),
        ("Find values from page 1", 0),
    ]

    for task_text, expected in test_cases:
        result = extract_page_number(task_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{task_text}' -> {result} (expected: {expected})")

    print()


def test_analyze_dataframe():
    """Test DataFrame analysis"""
    print("=" * 60)
    print("Test 4: DataFrame Analysis")
    print("=" * 60)

    # Create sample DataFrame
    df = pd.DataFrame({
        'Product': ['Apple', 'Banana', 'Orange', 'Grape'],
        'Price': [1.50, 0.75, 1.25, 2.00],
        'Quantity': [100, 150, 80, 60],
        'Sales': [150.0, 112.5, 100.0, 120.0]
    })

    print("Sample DataFrame:")
    print(df)
    print()

    # Test cases
    test_cases = [
        ("sum", "Find the sum of 'Sales'", 482.5),
        ("count", "Count the rows", 4),
        ("mean", "Average of 'Price'", 1.375),
        ("max", "Maximum 'Quantity'", 150),
        ("min", "Minimum 'Price'", 0.75),
    ]

    for task_type, task_text, expected in test_cases:
        result = analyze_dataframe(df, task_type, task_text)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        print(f"{status} {task_type.upper()}: {task_text}")
        print(f"   Result: {result} (expected: {expected})")

    print()


def test_format_answer():
    """Test answer formatting"""
    print("=" * 60)
    print("Test 5: Answer Formatting")
    print("=" * 60)

    test_cases = [
        (42, 42, "int"),
        (3.14, 3.14, "float"),
        ("hello", "hello", "str"),
        (True, True, "bool"),
        (np.int64(100), 100, "numpy int"),
        (np.float64(2.5), 2.5, "numpy float"),
        ([1, 2, 3], [1, 2, 3], "list"),
        ({"a": 1, "b": 2}, {"a": 1, "b": 2}, "dict"),
    ]

    for value, expected, description in test_cases:
        result = format_answer(value)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}: {value} -> {result}")

    # Test DataFrame formatting
    df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    result = format_answer(df)
    expected = [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
    status = "✓" if result == expected else "✗"
    print(f"{status} DataFrame: converted to list of dicts")

    print()


def test_get_dataframe_summary():
    """Test DataFrame summary generation"""
    print("=" * 60)
    print("Test 6: DataFrame Summary")
    print("=" * 60)

    df = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Age': [25, 30, 35],
        'Salary': [50000.0, 60000.0, 70000.0],
        'City': ['NY', 'LA', 'SF']
    })

    summary = get_dataframe_summary(df)

    print("Summary:")
    print(f"  Shape: {summary['shape']}")
    print(f"  Columns: {summary['columns']}")
    print(f"  Numeric columns: {summary['numeric_columns']}")
    print(f"  Sample data (first 3 rows):")
    for i, row in enumerate(summary['sample_data'], 1):
        print(f"    {i}. {row}")

    print()


def test_solve_task():
    """Test complete task solving pipeline"""
    print("=" * 60)
    print("Test 7: Complete Task Solving")
    print("=" * 60)

    # Create sample data
    df = pd.DataFrame({
        'Product': ['Laptop', 'Mouse', 'Keyboard', 'Monitor'],
        'Price': [1200.0, 25.0, 75.0, 350.0],
        'Stock': [15, 100, 50, 30]
    })

    print("Sample DataFrame:")
    print(df)
    print()

    # Test different tasks
    tasks = [
        "Find the total 'Price'",
        "Count how many products",
        "What is the average 'Stock'?",
        "Maximum 'Price'",
        "Minimum 'Stock'",
    ]

    for task_text in tasks:
        print(f"Task: {task_text}")
        result = solve_task(df, task_text)

        print(f"  Type: {result['task_type']}")
        print(f"  Answer: {result['formatted_answer']}")
        print(f"  Success: {result['success']}")
        print()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DATA ANALYZER MODULE TESTS")
    print("=" * 60)
    print()

    try:
        test_detect_task_type()
        test_extract_column_name()
        test_extract_page_number()
        test_analyze_dataframe()
        test_format_answer()
        test_get_dataframe_summary()
        test_solve_task()

        print("=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nMake sure you have installed numpy:")
    print("  pip install numpy\n")

    main()
