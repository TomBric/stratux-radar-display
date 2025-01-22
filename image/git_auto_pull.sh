#!/bin/bash

REPO_DIR="/home/pi/stratux-radar-display"
COMMAND="$1"
if [ -z "$COMMAND" ]; then
    echo "No command provided. Usage: $0 '<command>'"
    exit 1
fi
# change to local repo dir
cd "$REPO_DIR" || { echo "GitAutoPull Error: no such directory"; exit 1; }
while true; do
    git fetch origin
    # check if new commits exist
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/$(git rev-parse --abbrev-ref HEAD))
    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "Git changes detected. Pulling ..."
        git pull
        echo "Executing command: $COMMAND"
        eval "$COMMAND"
    else
        echo "No git changes detected."
    fi
    sleep 10
done