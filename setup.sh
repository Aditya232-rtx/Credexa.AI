#!/bin/bash
set -e

# Credexa AI — one-shot environment setup

echo "Running system installations..."
brew install node@20 python@3.11 tesseract tesseract-lang exiftool git || true

echo "Setting up virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate

echo "Upgrading pip tooling..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing Python packages..."
python -m pip install -r requirements.txt

echo "Downloading spaCy models..."
python -m pip install spacy
python -m spacy download en_core_web_sm || true
python -m spacy download xx_ent_wiki_sm || true

echo "Installing optional forensic utilities..."
python -m pip install git+https://github.com/jesparza/peepdf.git || true

echo "✓ Setup complete."
