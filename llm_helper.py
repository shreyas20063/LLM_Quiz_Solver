"""
LLM helper for analyzing ambiguous tasks.
Uses AI Pipe API with Claude Sonnet 4.5 as a fallback when deterministic methods fail.
"""
import logging
from typing import Optional
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AI Pipe API configuration (OpenAI-compatible endpoint)
AIPIPE_API_ENDPOINT = "https://aipipe.org/openrouter/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def should_use_llm(task_type: str) -> bool:
    """
    Determine if LLM should be used based on task type.

    LLM is only used as a last resort when deterministic methods fail.

    Args:
        task_type: The detected task type from data_analyzer

    Returns:
        True only if task_type is "unknown", False otherwise
    """
    # Only use LLM for unknown tasks
    # Prefer deterministic analysis for all known task types
    use_llm = task_type == "unknown"

    if use_llm:
        logger.info("Task type is 'unknown' - LLM may be helpful")
    else:
        logger.info(f"Task type is '{task_type}' - using deterministic analysis")

    return use_llm


async def analyze_with_llm(
    task_text: str,
    data_summary: str,
    api_token: str
) -> Optional[str]:
    """
    Analyze task using Claude Sonnet 4.5 via AI Pipe API.

    This is a fallback method used only when deterministic analysis fails.

    Args:
        task_text: The task description
        data_summary: Summary of the data (columns, shape, sample rows)
        api_token: AI Pipe API token

    Returns:
        LLM response text, or None if API call fails

    Example:
        >>> result = await analyze_with_llm(
        ...     "What is the total?",
        ...     "DataFrame: 10 rows × 3 columns (Sales, Price, Quantity)",
        ...     "your_api_token"
        ... )
    """
    logger.info("Calling LLM via AI Pipe (OpenRouter-compatible) for task analysis...")

    if not api_token:
        logger.error("No API token provided - cannot use LLM")
        return None

    try:
        # Construct prompt: concise answer only
        prompt = (
            f"Task: {task_text}\n\n"
            f"Data Summary: {data_summary}\n\n"
            "Provide the answer as a single value (number, string, or boolean). No explanation."
        )

        logger.debug(f"LLM Prompt: {prompt[:200]}...")

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DEFAULT_MODEL,
            "max_tokens": 256,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        logger.info("Sending request to AI Pipe (OpenRouter-compatible) API...")
        logger.debug(f"Endpoint: {AIPIPE_API_ENDPOINT}")
        logger.debug(f"Model: {DEFAULT_MODEL}")

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                AIPIPE_API_ENDPOINT,
                headers=headers,
                json=payload
            )

            logger.info(f"API Response status: {response.status_code}")

            # Check for errors
            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                logger.error(error_msg)
                logger.error(f"Response: {response.text[:200]}")
                return None

            response_data = response.json()
            logger.debug(f"Response data: {response_data}")

            # OpenAI/OpenRouter chat format
            choices = response_data.get("choices", [])
            if not choices:
                logger.error("Unexpected response format - no choices found")
                return None

            message = choices[0].get("message", {})
            content = message.get("content")

            if isinstance(content, list):
                # Some providers return list of parts
                text_parts = [part.get("text", "") if isinstance(part, dict) else str(part) for part in content]
                content = " ".join(text_parts)

            if content:
                logger.info(f"LLM Response: {content}")
                return str(content).strip()

            logger.error("No content in LLM response")
            return None

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error calling LLM API: {e.response.status_code}"
        logger.error(error_msg)
        logger.error(f"Response: {e.response.text[:200]}")
        return None

    except httpx.RequestError as e:
        error_msg = f"Network error calling LLM API: {str(e)}"
        logger.error(error_msg)
        return None

    except KeyError as e:
        error_msg = f"Error parsing LLM response: missing key {e}"
        logger.error(error_msg)
        return None

    except Exception as e:
        error_msg = f"Unexpected error calling LLM: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None


async def analyze_with_llm_detailed(
    task_text: str,
    dataframe_dict: dict,
    api_token: str
) -> Optional[str]:
    """
    Analyze task with LLM using detailed DataFrame representation.

    Provides more context to the LLM including actual data samples.

    Args:
        task_text: The task description
        dataframe_dict: Dictionary representation of DataFrame (from df.to_dict())
        api_token: AI Pipe API token

    Returns:
        LLM response text, or None if API call fails
    """
    logger.info("Calling LLM with detailed data context via AI Pipe...")

    if not api_token:
        logger.error("No API token provided")
        return None

    try:
        # Create detailed data summary
        data_context = f"Data (first few rows):\n{str(dataframe_dict)[:500]}"

        # Construct detailed prompt
        prompt = f"""You are analyzing data to answer a question.

Task: {task_text}

{data_context}

Analyze the data and provide the answer as a single value (number, string, or boolean).
If the task requires a calculation, perform it.
If the task requires filtering or searching, do it.

Answer (single value only, no explanation):"""

        logger.debug(f"Detailed LLM Prompt: {prompt[:300]}...")

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DEFAULT_MODEL,
            "max_tokens": 512,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                AIPIPE_API_ENDPOINT,
                headers=headers,
                json=payload
            )

            logger.info(f"API Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None

            response_data = response.json()
            choices = response_data.get("choices", [])
            if not choices:
                logger.error("Unexpected response format - no choices found")
                return None

            message = choices[0].get("message", {})
            content = message.get("content")

            if isinstance(content, list):
                text_parts = [part.get("text", "") if isinstance(part, dict) else str(part) for part in content]
                content = " ".join(text_parts)

            if content:
                logger.info(f"LLM Detailed Response: {content}")
                return str(content).strip()

            logger.error("No content in LLM response")
            return None

    except Exception as e:
        logger.error(f"Error in detailed LLM analysis: {str(e)}", exc_info=True)
        return None


def format_data_summary(df_summary: dict) -> str:
    """
    Format DataFrame summary for LLM context.

    Args:
        df_summary: Summary dictionary from get_dataframe_summary()

    Returns:
        Formatted string summary
    """
    summary_parts = []

    if "shape" in df_summary:
        rows, cols = df_summary["shape"]
        summary_parts.append(f"DataFrame: {rows} rows × {cols} columns")

    if "columns" in df_summary:
        summary_parts.append(f"Columns: {', '.join(df_summary['columns'])}")

    if "numeric_columns" in df_summary:
        summary_parts.append(f"Numeric columns: {', '.join(df_summary['numeric_columns'])}")

    if "sample_data" in df_summary and df_summary["sample_data"]:
        summary_parts.append(f"\nSample data (first 3 rows):")
        for i, row in enumerate(df_summary["sample_data"][:3], 1):
            summary_parts.append(f"  Row {i}: {row}")

    return "\n".join(summary_parts)
