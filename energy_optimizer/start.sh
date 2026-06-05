#!/bin/bash
# Energy Optimizer Agent — Phase 1 Startup
# Usage: ./start.sh

echo "Starting Energy Optimizer Agent (Phase 1 — Local)..."
echo "Contract: CON-004 | Domain: Energy & ESG"
echo ""

cd "$(dirname "$0")/.."
python -m uvicorn energy_optimizer.main:app --host 0.0.0.0 --port 8000 --reload
