#!/bin/bash
# Daily auto-publish pipeline for Daniks.AI blog
# Runs Claude Code in headless mode to write, generate image, publish, and commit
#
# Setup:
#   1. chmod +x scripts/daily-publish.sh
#   2. Set environment variables (or add to .env)
#   3. Schedule via launchd or crontab
#
# Required env vars:
#   FAL_KEY - fal.ai API key for image generation
#
# Claude Code authenticates via your subscription (launchd runs as your user).
#
# Optional env vars:
#   DAILY_PUBLISH_LOG - log file path (default: logs/daily-publish.log)

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WEBSITE_DIR="/Users/ync/poryadok/sources/daniks-ai-ads"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="${DAILY_PUBLISH_LOG:-$LOG_DIR/daily-publish-$(date +%Y-%m-%d).log}"

# --- Setup ---
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/published"
mkdir -p "$PROJECT_DIR/topics"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "================================================"
echo "Daily Publish Pipeline - $(date)"
echo "================================================"
echo ""

# Load environment variables from .env files
if [ -f "$PROJECT_DIR/data_sources/config/.env" ]; then
    set -a
    source "$PROJECT_DIR/data_sources/config/.env"
    set +a
fi

if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Check env vars
if [ -z "${FAL_KEY:-}" ]; then
    echo "WARNING: FAL_KEY not set - images will not be generated"
fi

# --- Pre-flight checks ---
echo "Checking prerequisites..."

# Ensure claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: claude CLI not found in PATH"
    echo "PATH: $PATH"
    exit 1
fi

# Ensure website repo is clean or stash changes
cd "$WEBSITE_DIR"
if [ -n "$(git status --porcelain)" ]; then
    echo "Website repo has uncommitted changes - stashing..."
    git stash push -m "daily-publish-auto-stash-$(date +%Y%m%d)"
    STASHED=true
else
    STASHED=false
fi
cd "$PROJECT_DIR"

echo "Prerequisites OK"
echo ""

# --- Run the pipeline ---
echo "Starting Claude Code pipeline..."
echo ""

cd "$PROJECT_DIR"

PROMPT="Run the /daily-publish command. This is an automated run - do NOT ask any questions. Make all decisions autonomously. Follow every step in the daily-publish command exactly. Key reminders: 1. Pick a topic from target-keywords.md that has not been covered yet. 2. Write a full 2000-3000 word article following all guidelines. 3. Generate the featured image with the image_generator.py script. 4. Update ALL three website files (routes.ts, Blog.tsx, BlogPost.tsx). 5. Commit and push the website changes. 6. Move draft to published/ and update internal-links-map.md."

unset CLAUDECODE
claude -p "$PROMPT" \
  --allowedTools "Read,Write,Edit,Glob,Grep,Bash(python*),Bash(cd*),Bash(git*),Bash(mv*),Bash(mkdir*),Bash(ls*),Bash(cat*),Bash(cp*)" \
  --max-turns 100 \
  --output-format text \
  2>&1

PIPELINE_EXIT=$?

echo ""
echo "Pipeline exited with code: $PIPELINE_EXIT"

# --- Post-pipeline ---

# Restore stashed changes if we stashed earlier
if [ "$STASHED" = true ]; then
    echo "Restoring stashed website repo changes..."
    cd "$WEBSITE_DIR"
    git stash pop || echo "WARNING: Could not pop stash - manual intervention needed"
    cd "$PROJECT_DIR"
fi

# --- Done ---
echo ""
echo "================================================"
echo "Pipeline finished at $(date)"
echo "Log: $LOG_FILE"
echo "================================================"

exit $PIPELINE_EXIT
