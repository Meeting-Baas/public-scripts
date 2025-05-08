#!/bin/bash

OLD_VERSION=$1
NEW_VERSION=$2
REPO_NAME=${3:-"speaking-bot"}  # Default to speaking-bot if not provided

OLD_FILE="openapi_old.json"
NEW_FILE="openapi_new.json"
OUTPUT_DIR="updates"

fetch_openapi_json() {
  VERSION=$1
  OUT_FILE=$2

  echo "Checking out $VERSION..."
  git checkout $VERSION --quiet

  echo "Waiting for API server to be ready..."
  sleep 3  # Adjust if needed

  echo "Fetching openapi.json for $VERSION..."
  curl -s http://localhost:8766/openapi.json -o $OUT_FILE
}

echo "Comparing OpenAPI specs between $OLD_VERSION and $NEW_VERSION"

fetch_openapi_json $OLD_VERSION $OLD_FILE
fetch_openapi_json $NEW_VERSION $NEW_FILE

git checkout -  # Return to original branch

# Run Python diff: concise to console, full to file
echo "Running structured JSON diff..."

# Output to console
python3 - << 'EOF'
import json
from deepdiff import DeepDiff

with open("openapi_old.json") as f1, open("openapi_new.json") as f2:
    old = json.load(f1)
    new = json.load(f2)

diff = DeepDiff(old, new, view='tree')

if not diff:
    print("✅ No differences found in OpenAPI specs.")
else:
    print("🔍 Differences found:\n")
    for change_type, changes in diff.items():
        print(f"{change_type.upper()}:")
        for change in changes:
            try:
                print(f"  {change.path()} -> {getattr(change, 't2', 'REMOVED')}")
            except Exception as e:
                print(f"  Error processing change: {e}")
EOF

# Output full details to file
python3 - << 'EOF' > openapi_diff.txt
import json
from deepdiff import DeepDiff

with open("openapi_old.json") as f1, open("openapi_new.json") as f2:
    old = json.load(f1)
    new = json.load(f2)

diff = DeepDiff(old, new, view='tree')

def get_by_path(data, path_list):
    for key in path_list:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list) and isinstance(key, int):
            data = data[key]
        else:
            return None
    return data

if not diff:
    print("✅ No differences found in OpenAPI specs.")
else:
    print("🔍 Detailed Differences:\n")
    for change_type, changes in diff.items():
        print(f"{change_type.upper()}:")
        for change in changes:
            path_str = change.path()
            path_parts = change.path(output_format='list')
            old_val = get_by_path(old, path_parts)
            new_val = get_by_path(new, path_parts)
            print(f"\n{path_str}:")
            print(f"  OLD: {json.dumps(old_val, indent=2)}")
            print(f"  NEW: {json.dumps(new_val, indent=2)}")
EOF

echo "Done. Diff saved to openapi_diff.txt"

# Run analysis
echo "Running OpenAPI schema analysis..."
python3 analyze_openapi_changes.py "$OLD_FILE" "$NEW_FILE" --output-dir "$OUTPUT_DIR" --repo-name "$REPO_NAME"

# Cleanup
rm -f "$OLD_FILE" "$NEW_FILE"