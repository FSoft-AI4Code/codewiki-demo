#!/bin/bash
# Prepare repository for GitHub Pages deployment
# This script copies actual files instead of using symlinks

set -e

echo "🚀 Preparing CodeWiki Demo for Deployment"
echo "=========================================="
echo ""

# Configuration
SOURCE_DOCS="/home/anhnh/CodeWiki/output/docs"
TARGET_DOCS="./docs"

# Check if source exists
if [ ! -d "$SOURCE_DOCS" ]; then
    echo "❌ Error: Source docs directory not found at $SOURCE_DOCS"
    exit 1
fi

# Remove existing docs (symlink or directory)
if [ -L "$TARGET_DOCS" ]; then
    echo "📝 Removing existing symlink..."
    rm "$TARGET_DOCS"
elif [ -d "$TARGET_DOCS" ]; then
    echo "📝 Removing existing docs directory..."
    rm -rf "$TARGET_DOCS"
fi

# Copy documentation
echo "📦 Copying documentation from $SOURCE_DOCS..."
cp -r "$SOURCE_DOCS" "$TARGET_DOCS"

# Check if copy was successful
if [ ! -d "$TARGET_DOCS" ]; then
    echo "❌ Error: Failed to copy documentation"
    exit 1
fi

# Count projects
PROJECT_COUNT=$(find "$TARGET_DOCS" -maxdepth 1 -type d | wc -l)
PROJECT_COUNT=$((PROJECT_COUNT - 1))  # Subtract 1 for the docs folder itself

echo "✅ Copied $PROJECT_COUNT project(s)"
echo ""

# Generate projects.json
echo "🔄 Generating projects.json..."
node generate-projects.js

if [ ! -f "projects.json" ]; then
    echo "❌ Error: Failed to generate projects.json"
    exit 1
fi

echo ""
echo "=========================================="
echo "✨ Preparation complete!"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git add . && git commit -m 'Prepare for deployment'"
echo "  3. Push: git push origin main"
echo "  4. Enable GitHub Pages in repository settings"
echo ""
echo "Your site will be available at:"
echo "  https://fsoft-ai4code.github.io/codewiki-demo/"
echo ""
