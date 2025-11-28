from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import os
import logging
from browser_handler import extract_task_from_url
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


class QuizRequest(BaseModel):
    email: EmailStr
    secret: str
    url: str


class ErrorResponse(BaseModel):
    error: str


class SuccessResponse(BaseModel):
    status: str
    url: str
    extracted_content: dict = None
    quiz_results: dict = None


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
        # Solve the quiz (with 3 minute timeout)
        quiz_results = await solve_quiz_func(
            initial_url=request.url,
            email=request.email,
            secret=request.secret,
            timeout_seconds=180
        )

        logger.info(f"Quiz solver completed")
        logger.info(f"Total questions: {quiz_results.get('total_questions', 0)}")
        logger.info(f"Correct answers: {quiz_results.get('correct_answers', 0)}")

        # Return results
        return {
            "status": "completed",
            "url": request.url,
            "quiz_results": {
                "total_questions": quiz_results.get("total_questions", 0),
                "correct_answers": quiz_results.get("correct_answers", 0),
                "total_time": quiz_results.get("total_time", 0),
                "questions": quiz_results.get("questions", []),
                "errors": quiz_results.get("errors", []),
                "success": quiz_results.get("correct_answers", 0) > 0
            }
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
