#!/bin/bash
# Generates lists of explicit pacman and AUR packages and commits them.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Get explicitly installed pacman packages (excluding AUR)
pacman -Qqen > "$REPO_DIR/pkglist-pacman.txt"

# Get explicitly installed AUR packages
pacman -Qqem > "$REPO_DIR/pkglist-aur.txt"

cd "$REPO_DIR" || exit 1
git add pkglist-pacman.txt pkglist-aur.txt

# Only commit if there are staged changes
if ! git diff --cached --quiet; then
    git commit -m "Auto-sync package lists via pacman hook"
    # git push  # Uncomment if you want it to push automatically too!
fi
