#!/bin/bash
# Тестовые запросы к оркестратору

BASE_URL="http://localhost:8000"
CLIENT_TOKEN="test-client-token"

echo "=========================================="
echo "Testing Orchestrator API"
echo "=========================================="
echo ""

# 1. Создаём job
echo "1. Creating a new job..."
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/jobs" \
    -H "Authorization: Bearer $CLIENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "blueprint": "test_workflow",
        "data": {
            "input": "Hello, World!"
        }
    }')

echo "Response: $JOB_RESPONSE"
echo ""

# Извлекаем job_id
JOB_ID=$(echo $JOB_RESPONSE | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo "ERROR: Failed to create job"
    exit 1
fi

echo "Created job: $JOB_ID"
echo ""

# 2. Проверяем статус job
echo "2. Checking job status..."
sleep 1

STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/$JOB_ID" \
    -H "Authorization: Bearer $CLIENT_TOKEN")

echo "Job status: $STATUS_RESPONSE"
echo ""

# 3. Ждём пока воркер обработает задачу
echo "3. Waiting for worker to process the task..."
echo "   (Make sure worker_client.py is running in another terminal)"
echo ""

for i in {1..10}; do
    sleep 2
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/$JOB_ID" \
        -H "Authorization: Bearer $CLIENT_TOKEN")
    
    STATE=$(echo $STATUS_RESPONSE | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    echo "   Attempt $i: state = $STATE"
    
    if [ "$STATE" == "completed" ] || [ "$STATE" == "failed" ]; then
        echo ""
        echo "Final result:"
        echo $STATUS_RESPONSE | python3 -m json.tool 2>/dev/null || echo $STATUS_RESPONSE
        break
    fi
done

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
