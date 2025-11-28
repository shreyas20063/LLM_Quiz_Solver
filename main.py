import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from quiz_solver import solve_quiz as solve_quiz_func

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Quiz Solver")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Return HTTP 400 for malformed JSON bodies while preserving 422 for
    normal validation errors (e.g., missing fields, bad email).
    """
    errors = exc.errors()
    json_error = any(
        err.get("type", "").endswith("jsondecode")
        or err.get("type") == "json_invalid"
        or "JSON decode" in err.get("msg", "")
        for err in errors
    )
    status_code = status.HTTP_400_BAD_REQUEST if json_error else status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(status_code=status_code, content={"detail": errors})


class QuizRequest(BaseModel):
    email: EmailStr
    secret: str
    url: str


class ErrorResponse(BaseModel):
    error: str


class SuccessResponse(BaseModel):
    status: str
    url: str
    message: Optional[str] = None
    extracted_content: Optional[dict] = None
    quiz_results: Optional[dict] = None


@app.post("/", response_model=SuccessResponse, responses={
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def solve_quiz(request: QuizRequest):
    """
    Accept quiz solving requests with email, secret, and URL.
    Validates the secret against the STUDENT_SECRET environment variable.
    """
    # Get the student secret from environment
    student_secret = os.getenv("STUDENT_SECRET")

    if not student_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: STUDENT_SECRET not set"
        )

    # Validate the secret
    if request.secret != student_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Invalid secret"}
        )

    # Run the complete quiz solver
    logger.info(f"Starting quiz solver for URL: {request.url}")

    try:
        async def _run_solver() -> None:
            """Fire-and-forget task that solves the quiz within the time limit."""
            try:
                await solve_quiz_func(
                    initial_url=request.url,
                    email=request.email,
                    secret=request.secret,
                    timeout_seconds=180
                )
                logger.info("Background quiz solver finished")
            except Exception as exc:
                logger.error(f"Background quiz solver failed: {exc}", exc_info=True)

        # Start solver in the background so we can acknowledge immediately
        asyncio.create_task(_run_solver())

        # Return immediate acknowledgement (spec requires 200 when secret matches)
        return {
            "status": "received",
            "url": request.url,
            "message": "Quiz solving started in background",
            "quiz_results": None
        }

    except Exception as e:
        logger.error(f"Unexpected error in quiz solver: {str(e)}", exc_info=True)
        # Return error info
        return {
            "status": "error",
            "url": request.url,
            "quiz_results": {
                "error": f"Quiz solver error: {str(e)}",
                "total_questions": 0,
                "correct_answers": 0,
                "success": False
            }
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
