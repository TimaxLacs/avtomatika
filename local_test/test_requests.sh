#!/bin/bash
# Скрипт для тестовых запросов к Orchestrator
# Использование: ./local_test/test_requests.sh

BASE_URL="http://localhost:8080"
TOKEN="test-client-token"

echo "========================================"
echo "Testing Avtomatika Orchestrator"
echo "========================================"
echo ""

# 1. Проверка статуса
echo "1. Health check..."
curl -s "$BASE_URL/_public/status" | python3 -m json.tool
echo ""

# 2. Создание job'а
echo "2. Creating a job..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/jobs/test" \
  -H "Content-Type: application/json" \
  -H "X-Avtomatika-Token: $TOKEN" \
  -d '{"message": "Hello World", "multiply": 3}')

echo "$RESPONSE" | python3 -m json.tool

# Извлекаем job_id
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ -z "$JOB_ID" ]; then
  echo "ERROR: Could not get job_id"
  exit 1
fi

echo ""
echo "Job ID: $JOB_ID"
echo ""

# 3. Ждём немного
echo "3. Waiting 3 seconds for processing..."
sleep 3

# 4. Проверяем статус job'а
echo ""
echo "4. Checking job status..."
curl -s "$BASE_URL/api/v1/jobs/$JOB_ID" \
  -H "X-Avtomatika-Token: $TOKEN" | python3 -m json.tool
echo ""

# 5. Список воркеров
echo "5. Listing workers..."
curl -s "$BASE_URL/api/v1/workers" \
  -H "X-Avtomatika-Token: $TOKEN" | python3 -m json.tool
echo ""

echo "========================================"
echo "Test completed!"
echo "========================================"
