#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f ".venv_dating_gui/bin/python" ]; then
    echo "[ERROR] .venv_dating_gui was not found."
    echo "Please run the setup steps in dating_assistant/README.md first."
    exit 1
fi

echo "Starting dating_assistant GUI..."
echo ""
echo "Checking for stale dating_assistant Streamlit processes..."
stale_pids=$(pgrep -f "streamlit.*dating_assistant.*gui_streamlit_app\.py" 2>/dev/null || true)
if [ -n "$stale_pids" ]; then
    echo "$stale_pids" | xargs kill 2>/dev/null || true
    echo "Stopped stale dating_assistant Streamlit process(es)."
else
    echo "No stale dating_assistant Streamlit process found."
fi

echo ""
echo "Running GUI import preflight..."
if ! ".venv_dating_gui/bin/python" tools/check_dating_gui_imports.py; then
    echo ""
    echo "[ERROR] GUI import preflight failed. Streamlit was not started."
    echo "Please check the missing import shown above."
    exit 1
fi

echo ""
echo "If the browser does not open automatically, open:"
echo "http://localhost:8501"
echo ""

".venv_dating_gui/bin/python" -m streamlit run dating_assistant/gui_streamlit_app.py

echo ""
echo "dating_assistant GUI has stopped."
