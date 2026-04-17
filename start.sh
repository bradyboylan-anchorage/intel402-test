#!/bin/bash
pip install "x402[evm]" --quiet
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
