"""
Data analysis engine for solving common quiz tasks.
Provides functions to detect task types, analyze data, and format answers.
"""
import re
import logging
from typing import Any, Optional, Union
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def detect_task_type(task_text: str) -> str:
    """
    Detect the type of task from the task description.

    Analyzes task text using keyword matching to determine what operation
    is being requested.

    Args:
        task_text: The task description text

    Returns:
        str: One of "sum", "count", "filter", "mean", "max", "min",
             "extract", "unknown"

    Examples:
        >>> detect_task_type("Find the sum of sales")
        'sum'
        >>> detect_task_type("Count how many items")
        'count'
    """
    if not task_text:
        logger.warning("Empty task text provided")
        return "unknown"

    # Convert to lowercase for case-insensitive matching
    text_lower = task_text.lower()

    # Define keywords for each task type
    # Order matters - check more specific patterns first

    # Sum/Total
    if any(word in text_lower for word in ['sum', 'total', 'add up', 'sum up', 'summation']):
        logger.info("Detected task type: sum")
        return "sum"

    # Average/Mean
    if any(word in text_lower for word in ['average', 'mean', 'avg']):
        logger.info("Detected task type: mean")
        return "mean"

    # Count
    if any(word in text_lower for word in ['count', 'how many', 'number of', 'num of']):
        logger.info("Detected task type: count")
        return "count"

    # Maximum
    if any(word in text_lower for word in ['maximum', 'max', 'highest', 'largest', 'biggest', 'greatest']):
        logger.info("Detected task type: max")
        return "max"

    # Minimum
    if any(word in text_lower for word in ['minimum', 'min', 'lowest', 'smallest', 'least']):
        logger.info("Detected task type: min")
        return "min"

    # Filter/Find
    if any(word in text_lower for word in ['filter', 'where', 'find', 'select', 'get', 'which']):
        logger.info("Detected task type: filter")
        return "filter"

    # Extract
    if any(word in text_lower for word in ['extract', 'pull', 'get value']):
        logger.info("Detected task type: extract")
        return "extract"

    logger.warning(f"Could not detect task type from: {task_text[:100]}...")
    return "unknown"


def extract_column_name(task_text: str) -> Optional[str]:
    """
    Extract column name from task text.

    Looks for patterns like:
    - "sum of 'Sales'"
    - "column 'Price'"
    - "Sales column"
    - quoted strings

    Args:
        task_text: The task description text

    Returns:
        Column name if found, None otherwise

    Examples:
        >>> extract_column_name("Find the sum of 'Sales'")
        'Sales'
        >>> extract_column_name("Count the Price column")
        'Price'
    """
    if not task_text:
        return None

    # Pattern 1: Text in single or double quotes
    quote_pattern = r'["\']([^"\']+)["\']'
    matches = re.findall(quote_pattern, task_text)
    if matches:
        column_name = matches[0]
        logger.info(f"Extracted column name from quotes: {column_name}")
        return column_name

    # Pattern 2: "column_name column" or "column column_name"
    column_pattern = r'(?:column\s+)?(\w+)(?:\s+column)?'
    matches = re.findall(column_pattern, task_text, re.IGNORECASE)
    if matches:
        # Filter out common words
        common_words = {'the', 'of', 'in', 'a', 'an', 'column', 'sum', 'count', 'mean', 'max', 'min'}
        for match in matches:
            if match.lower() not in common_words and len(match) > 1:
                logger.info(f"Extracted column name from pattern: {match}")
                return match

    logger.warning("Could not extract column name from task text")
    return None


def extract_page_number(task_text: str) -> Optional[int]:
    """
    Extract page number from task text.

    Looks for patterns like:
    - "page 2"
    - "on page 5"
    - "from page 3"

    Args:
        task_text: The task description text

    Returns:
        Page number (0-indexed) if found, None otherwise

    Examples:
        >>> extract_page_number("Extract from page 2")
        1  # Returns 0-indexed (page 2 = index 1)
        >>> extract_page_number("Data on page 5")
        4
    """
    if not task_text:
        return None

    # Pattern: "page" followed by a number
    page_pattern = r'page\s+(\d+)'
    matches = re.findall(page_pattern, task_text.lower())

    if matches:
        # Convert to 0-indexed (page 1 = index 0)
        page_num = int(matches[0]) - 1
        logger.info(f"Extracted page number: {page_num} (0-indexed)")
        return page_num

    return None


def extract_filter_value(task_text: str) -> Optional[str]:
    """
    Extract filter value from task text.

    Looks for patterns after "where", "equals", "is", etc.

    Args:
        task_text: The task description text

    Returns:
        Filter value if found, None otherwise
    """
    if not task_text:
        return None

    # Pattern: text after "where", "equals", "is", "=="
    patterns = [
        r'where\s+.*?[=<>]\s*["\']?([^"\']+)["\']?',
        r'equals?\s+["\']?([^"\']+)["\']?',
        r'is\s+["\']?([^"\']+)["\']?',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, task_text.lower())
        if matches:
            value = matches[0].strip()
            logger.info(f"Extracted filter value: {value}")
            return value

    return None


def analyze_dataframe(
    df: pd.DataFrame,
    task_type: str,
    task_text: str
) -> Any:
    """
    Analyze DataFrame based on task type and return result.

    Performs the appropriate analysis operation on the DataFrame
    based on the detected task type.

    Args:
        df: pandas DataFrame to analyze
        task_type: Type of task ("sum", "count", "mean", "max", "min", "filter", "extract")
        task_text: Original task description for extracting parameters

    Returns:
        Analysis result (int, float, str, bool, dict, or DataFrame)

    Examples:
        >>> df = pd.DataFrame({'Sales': [100, 200, 300]})
        >>> analyze_dataframe(df, 'sum', "sum of 'Sales'")
        600
    """
    logger.info(f"Analyzing DataFrame with task type: {task_type}")
    logger.info(f"DataFrame shape: {df.shape}")

    if df.empty:
        logger.warning("Empty DataFrame provided")
        return None

    try:
        # SUM: Sum a specific column
        if task_type == "sum":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                result = df[column_name].sum()
                logger.info(f"Sum of '{column_name}': {result}")
                return result
            else:
                # Try to sum first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    result = df[numeric_cols[0]].sum()
                    logger.info(f"Sum of first numeric column '{numeric_cols[0]}': {result}")
                    return result
                else:
                    logger.error("No numeric columns found for sum")
                    return None

        # COUNT: Count rows or specific values
        elif task_type == "count":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                # Count non-null values in column
                result = df[column_name].count()
                logger.info(f"Count of '{column_name}': {result}")
                return result
            else:
                # Count total rows
                result = len(df)
                logger.info(f"Total row count: {result}")
                return result

        # MEAN: Calculate average
        elif task_type == "mean":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                result = df[column_name].mean()
                logger.info(f"Mean of '{column_name}': {result}")
                return result
            else:
                # Mean of first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    result = df[numeric_cols[0]].mean()
                    logger.info(f"Mean of '{numeric_cols[0]}': {result}")
                    return result
                else:
                    logger.error("No numeric columns found for mean")
                    return None

        # MAX: Find maximum value
        elif task_type == "max":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                result = df[column_name].max()
                logger.info(f"Max of '{column_name}': {result}")
                return result
            else:
                # Max of first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    result = df[numeric_cols[0]].max()
                    logger.info(f"Max of '{numeric_cols[0]}': {result}")
                    return result
                else:
                    logger.error("No numeric columns found for max")
                    return None

        # MIN: Find minimum value
        elif task_type == "min":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                result = df[column_name].min()
                logger.info(f"Min of '{column_name}': {result}")
                return result
            else:
                # Min of first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    result = df[numeric_cols[0]].min()
                    logger.info(f"Min of '{numeric_cols[0]}': {result}")
                    return result
                else:
                    logger.error("No numeric columns found for min")
                    return None

        # FILTER: Filter DataFrame and return result
        elif task_type == "filter":
            column_name = extract_column_name(task_text)
            filter_value = extract_filter_value(task_text)

            if column_name and column_name in df.columns:
                if filter_value:
                    # Filter by value
                    filtered = df[df[column_name].astype(str).str.contains(filter_value, case=False, na=False)]
                    logger.info(f"Filtered {len(filtered)} rows where '{column_name}' contains '{filter_value}'")
                    return filtered
                else:
                    # Return the column
                    result = df[column_name].tolist()
                    logger.info(f"Returning column '{column_name}' with {len(result)} values")
                    return result
            else:
                logger.warning("Could not extract filter parameters")
                return df.head(10)  # Return first 10 rows as fallback

        # EXTRACT: Extract specific value or column
        elif task_type == "extract":
            column_name = extract_column_name(task_text)

            if column_name and column_name in df.columns:
                # Return first value from column
                result = df[column_name].iloc[0] if len(df) > 0 else None
                logger.info(f"Extracted first value from '{column_name}': {result}")
                return result
            else:
                # Return first row as dict
                result = df.iloc[0].to_dict() if len(df) > 0 else None
                logger.info("Extracted first row")
                return result

        # UNKNOWN: Return basic statistics
        else:
            logger.warning(f"Unknown task type: {task_type}")
            # Return basic info about the DataFrame
            return {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "head": df.head(5).to_dict(orient='records')
            }

    except Exception as e:
        logger.error(f"Error analyzing DataFrame: {str(e)}", exc_info=True)
        return None


def format_answer(answer: Any) -> Any:
    """
    Format answer for JSON submission.

    Converts various Python types to JSON-serializable format.

    Args:
        answer: The answer to format (int, float, str, bool, dict, DataFrame, etc.)

    Returns:
        JSON-serializable value

    Examples:
        >>> format_answer(42)
        42
        >>> format_answer(pd.DataFrame({'a': [1, 2]}))
        [{'a': 1}, {'a': 2}]
    """
    logger.info(f"Formatting answer of type: {type(answer)}")

    # None
    if answer is None:
        return None

    # Basic types (already JSON-serializable)
    if isinstance(answer, (int, str, bool)):
        return answer

    # Float (handle NaN and infinity)
    if isinstance(answer, (float, np.floating)):
        if np.isnan(answer):
            return None
        if np.isinf(answer):
            return str(answer)
        return float(answer)

    # NumPy integer
    if isinstance(answer, np.integer):
        return int(answer)

    # List
    if isinstance(answer, list):
        return [format_answer(item) for item in answer]

    # Dictionary
    if isinstance(answer, dict):
        return {key: format_answer(value) for key, value in answer.items()}

    # pandas Series
    if isinstance(answer, pd.Series):
        return answer.tolist()

    # pandas DataFrame
    if isinstance(answer, pd.DataFrame):
        logger.info(f"Converting DataFrame ({answer.shape}) to dict")
        return answer.to_dict(orient='records')

    # Fallback: convert to string
    logger.warning(f"Unknown type {type(answer)}, converting to string")
    return str(answer)


def get_dataframe_summary(df: pd.DataFrame) -> dict:
    """
    Get a summary of the DataFrame.

    Provides basic information about the DataFrame structure and content.

    Args:
        df: pandas DataFrame

    Returns:
        Dictionary with summary information
    """
    logger.info("Generating DataFrame summary")

    try:
        summary = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict(),
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "sample_data": df.head(3).to_dict(orient='records')
        }

        logger.info(f"Summary generated for {df.shape[0]} rows × {df.shape[1]} columns")
        return summary

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return {
            "error": str(e),
            "shape": df.shape if hasattr(df, 'shape') else None
        }


def solve_task(df: pd.DataFrame, task_text: str) -> dict:
    """
    Complete pipeline to solve a task given a DataFrame and task description.

    Combines task detection, analysis, and answer formatting.

    Args:
        df: pandas DataFrame containing the data
        task_text: Description of the task to perform

    Returns:
        Dictionary with task_type, answer, and formatted_answer
    """
    logger.info(f"Solving task: {task_text[:100]}...")

    try:
        # Step 1: Detect task type
        task_type = detect_task_type(task_text)

        # Step 2: Analyze data
        answer = analyze_dataframe(df, task_type, task_text)

        # Step 3: Format answer
        formatted_answer = format_answer(answer)

        result = {
            "task_type": task_type,
            "answer": answer,
            "formatted_answer": formatted_answer,
            "success": answer is not None
        }

        logger.info(f"Task solved successfully: {task_type}")
        return result

    except Exception as e:
        logger.error(f"Error solving task: {str(e)}", exc_info=True)
        return {
            "task_type": "unknown",
            "answer": None,
            "formatted_answer": None,
            "success": False,
            "error": str(e)
        }
