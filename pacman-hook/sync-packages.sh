#!/bin/bash
# Generates lists of explicit pacman and AUR packages and commits them.

# Get explicitly installed pacman packages (excluding AUR)
pacman -Qqen > /home/marc/LinuxConfig/pkglist-pacman.txt

# Get explicitly installed AUR packages
pacman -Qqem > /home/marc/LinuxConfig/pkglist-aur.txt

cd /home/marc/LinuxConfig
git add pkglist-pacman.txt pkglist-aur.txt

# Only commit if there are staged changes
if ! git diff --cached --quiet; then
    git commit -m "Auto-sync package lists via pacman hook"
    # git push  # Uncomment if you want it to push automatically too!
fi
