#!/bin/bash

# VoiceVibe4 Installation Script for macOS
# Optimized for Apple Silicon (M1/M2/M3)

set -e

echo "🎤 VoiceVibe4 - Installation Script"
echo "===================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment
echo ""
echo "🔧 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping..."
else
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install PyTorch with MPS support (Apple Silicon)
echo ""
echo "🔥 Installing PyTorch with MPS support (Apple Silicon)..."
pip install torch torchaudio

# Install other dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check Ollama
echo ""
echo "🤖 Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed"
    echo "📥 Make sure you have the qwen2.5 model:"
    echo "   Run: ollama pull qwen2.5"
else
    echo "⚠️  Ollama is not installed."
    echo "   Install it with: brew install ollama"
    echo "   Then run: ollama pull qwen2.5"
fi

# Create .env file if it doesn't exist
echo ""
echo "⚙️  Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "   Please edit .env with your settings"
else
    echo "⚠️  .env file already exists. Skipping..."
fi

# Note about Moshi
echo ""
echo "📝 Note about Moshi:"
echo "   Moshi integration needs to be configured based on the actual package."
echo "   Check the Moshi documentation and update src/audio_engine.py accordingly."

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 To start the application:"
echo "   1. Activate the virtual environment: source .venv/bin/activate"
echo "   2. Run: python main.py"
echo ""
echo "📚 For more information, see README.md"

