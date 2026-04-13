#!/bin/bash
# =============================================================================
# MLX-LM Server for Intelligence Stack
# Runs an OpenAI-compatible server that dynamically loads MLX models
#
# Start:  ./mlx-server.sh
# Stop:   Ctrl+C (or: launchctl unload ~/Library/LaunchAgents/com.intelligence-stack.mlx-server.plist)
# Test:   curl http://localhost:5001/v1/models
#
# Available models (pass as "model" in API requests):
#   mlx-community/gemma-4-31b-it-4bit        
#   mlx-community/gemma-4-26b-a4b-it-4bit    
#   mlx-community/Qwen3-30B-A3B-4bit         
#   mlx-community/Qwen2.5-Coder-32B-Instruct-4bit
#
# The server auto-swaps models based on the request.
# Only one model is loaded in memory at a time.
# =============================================================================

python3 -m mlx_lm server \
  --model mlx-community/gemma-4-31b-it-4bit \
  --chat-template-arg '{"enable_thinking":false}' \
  --prompt-cache-size 8 \
  --host 0.0.0.0 \
  --port 5001 \
  --log-level INFO
