#!/usr/bin/env bash
# build.sh — Production build script for Render.com

# Exit on error
set -o errexit

echo "============================================================"
echo "    🚀 Accu Design — Render.com Production Build Script     "
echo "============================================================"

echo "📦 1. Installing Frontend (React/Vite) Dependencies..."
npm install

echo "🛠️ 2. Building Production React Application..."
npm run build

echo "🐍 3. Installing Backend (FastAPI/Python) Dependencies..."
# Render sets the working directory when executing pip, but we specify to be safe.
# Assuming the "Build Command" in Render is: ./build.sh
pip install -r backend/requirements.txt

echo "✅ Build Process Complete! The dist/ folder is ready for FastAPI."
