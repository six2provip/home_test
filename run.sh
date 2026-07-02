#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f .env ]; then
    echo "[run] Loading .env file"
    set -a
    # shellcheck source=/dev/null
    . .env
    set +a
fi

# Verify required variables
MISSING=0
for var in OPENAI_API_KEY OPENAI_VECTOR_STORE_ID OPENAI_ASSISTANT_ID OPTISIGNS_BASE_URL MARKDOWN_DIR STATE_FILE LOG_FILE; do
    if [ -z "${!var:-}" ]; then
        echo "[run] ERROR: $var is not set. Copy .env.example to .env and fill in the values."
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    exit 1
fi

# Ensure output directories exist
mkdir -p "$MARKDOWN_DIR" "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"

# Install dependencies if not already installed
if [ ! -d .venv ]; then
    echo "[run] Creating virtual environment..."
    python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo "[run] Installing dependencies..."
pip install -q -r requirements.txt

echo "[run] Starting synchronization..."
python -m app.main
exit_code=$?
echo "[run] Done (exit code: $exit_code)"
exit $exit_code
