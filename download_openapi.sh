#!/bin/bash

COMMIT_HASH=$1
CONTAINER_NAME="openapi_temp_server"

if [ -z "$COMMIT_HASH" ]; then
  echo "❌ Please provide a commit hash as the first argument."
  exit 1
fi

# Get commit date
COMMIT_DATE=$(git show -s --format=%cs "$COMMIT_HASH")
OUT_FILE="openapi_${COMMIT_HASH}_${COMMIT_DATE}.json"

# Start the server using Dockerfile at specified commit
start_server() {
  echo "Checking out $COMMIT_HASH..."
  git checkout "$COMMIT_HASH" --quiet

  echo "Building Docker image..."
  docker build -t openapi-server -f Dockerfile .

  echo "Running container..."
  docker run -d --rm --name "$CONTAINER_NAME" -p 8766:8766 openapi-server

  echo -n "Waiting for server to be ready"
  until curl -s http://localhost:8766/openapi.json >/dev/null; do
    echo -n "."
    sleep 1
  done
  echo " ✅"
}

# Stop the running container
stop_server() {
  echo "Stopping container..."
  docker stop "$CONTAINER_NAME" >/dev/null
}

# Fetch openapi.json
fetch_openapi_json() {
  start_server

  echo "Fetching openapi.json from commit $COMMIT_HASH..."
  curl -s http://localhost:8766/openapi.json -o "$OUT_FILE"

  stop_server
}

# Main
fetch_openapi_json

# Restore previous branch
git checkout - >/dev/null

echo "✅ openapi.json saved as $OUT_FILE"
