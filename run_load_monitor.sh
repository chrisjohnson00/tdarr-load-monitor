#!/bin/bash
cd "$(dirname "$0")"
uv sync
uv run python3 load_monitor.py
