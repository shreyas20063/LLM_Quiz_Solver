#!/bin/bash

# Test script for the FastAPI quiz solver endpoint using curl
# Run this after starting the server with: uvicorn main:app --reload

BASE_URL="http://localhost:8000"

echo "======================================================================"
echo "Testing LLM Quiz Solver API"
echo "======================================================================"

# Test 1: Health check
echo ""
echo "1. Testing health check endpoint..."
echo "   Request: GET ${BASE_URL}/health"
RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "   Status: ${STATUS_CODE}"
echo "   Response: ${BODY}"
if [ "$STATUS_CODE" -eq 200 ]; then
    echo "   ✓ Health check passed"
else
    echo "   ✗ Health check failed"
fi

# Test 2: Valid request
echo ""
echo "2. Testing valid request..."
echo "   Request: POST ${BASE_URL}/"
PAYLOAD='{"email":"test@example.com","secret":"test_secret_123","url":"https://example.com/quiz"}'
echo "   Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "   Status: ${STATUS_CODE}"
echo "   Response: ${BODY}"
if [ "$STATUS_CODE" -eq 200 ]; then
    echo "   ✓ Valid request test passed"
else
    echo "   ✗ Valid request test failed"
fi

# Test 3: Invalid secret
echo ""
echo "3. Testing invalid secret..."
echo "   Request: POST ${BASE_URL}/"
PAYLOAD='{"email":"test@example.com","secret":"wrong_secret","url":"https://example.com/quiz"}'
echo "   Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "   Status: ${STATUS_CODE}"
echo "   Response: ${BODY}"
if [ "$STATUS_CODE" -eq 403 ]; then
    echo "   ✓ Invalid secret test passed"
else
    echo "   ✗ Invalid secret test failed"
fi

# Test 4: Malformed request (missing url field)
echo ""
echo "4. Testing malformed request (missing url field)..."
echo "   Request: POST ${BASE_URL}/"
PAYLOAD='{"email":"test@example.com","secret":"test_secret_123"}'
echo "   Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "   Status: ${STATUS_CODE}"
echo "   Response: ${BODY}"
if [ "$STATUS_CODE" -eq 422 ]; then
    echo "   ✓ Malformed request test passed (422 = validation error)"
else
    echo "   ✗ Malformed request test failed"
fi

# Test 5: Invalid email format
echo ""
echo "5. Testing invalid email format..."
echo "   Request: POST ${BASE_URL}/"
PAYLOAD='{"email":"not-an-email","secret":"test_secret_123","url":"https://example.com/quiz"}'
echo "   Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "   Status: ${STATUS_CODE}"
echo "   Response: ${BODY}"
if [ "$STATUS_CODE" -eq 422 ]; then
    echo "   ✓ Invalid email test passed (422 = validation error)"
else
    echo "   ✗ Invalid email test failed"
fi

echo ""
echo "======================================================================"
echo "Testing complete!"
echo "======================================================================"
