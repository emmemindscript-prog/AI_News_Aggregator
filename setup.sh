#!/bin/bash
# AI News Aggregator - Setup Script
set -e

echo "🤖 AI News Aggregator - Setup"
echo "=============================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "→ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "→ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "→ Installing dependencies..."
pip install -q -r requirements.txt

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    echo "→ Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env with your API keys!"
fi

# Create data directory
mkdir -p data

# Initialize database
echo "→ Initializing database..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from app.models.database import init_database
init_database()
print('✓ Database initialized')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: python -m uvicorn app.main:app --reload"
echo "  3. Visit: http://localhost:8000/docs"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
