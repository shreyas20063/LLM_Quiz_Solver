#!/bin/bash

# Start server script for LLM Quiz Solver
# Make sure you've activated your conda environment first: conda activate quiz-solver

echo "Starting LLM Quiz Solver FastAPI Server..."
echo "=========================================="
echo ""
echo "Make sure you have:"
echo "1. Activated conda environment: conda activate quiz-solver"
echo "2. Installed dependencies: pip install -r requirements.txt"
echo "3. Created .env file with STUDENT_SECRET"
echo ""
echo "Server will start at: http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
