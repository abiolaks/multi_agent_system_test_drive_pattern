#!/usr/bin/env bash
# Serves Qwen3-32B-AWQ locally via vLLM for fabric_qa (see docs/kb-setup.md's
# sibling LLM setup and fabric_qa/adapters/llm_client.py).
#
# Flags were arrived at by trial on this machine's RTX 5090 Laptop GPU
# (24GB VRAM) - see the memory-allocation writeup in the project history:
#   --enforce-eager           no CUDA graph capture buffers; frees VRAM
#                              that would otherwise be needed for the KV
#                              cache pool. This machine has no CUDA
#                              Toolkit/nvcc, so compiled mode wasn't an
#                              option to compare against anyway.
#   VLLM_USE_FLASHINFER_SAMPLER=0
#                              disables FlashInfer's JIT-compiled sampler,
#                              which also needs nvcc; falls back to a
#                              native PyTorch sampler.
#   --enable-auto-tool-choice
#   --tool-call-parser hermes forced by Qwen3's chat template, which
#                              emits Hermes-style <tool_call> tags; without
#                              these two flags any tool-using agent request
#                              is rejected with a 400.
#   --reasoning-parser qwen3   Qwen3 emits a <think>...</think> block before
#                              its answer. Without this, that block is part
#                              of the plain `content` field and leaks into
#                              Report.summary verbatim. With it, vLLM splits
#                              thinking into a separate `reasoning_content`
#                              field that agent_framework_openai's client
#                              never reads - content comes back clean, no
#                              fabric_qa code changes needed.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

MODEL_PATH="${MODEL_PATH:-/home/aiser/models/Qwen3-32B-AWQ}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3-32b-awq}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.95}"

if pgrep -f "vllm serve" > /dev/null; then
    echo "A vLLM server is already running:" >&2
    pgrep -af "vllm serve" >&2
    echo "Stop it first (kill the PID above) before starting a new one - VRAM is too tight on this GPU for two instances." >&2
    exit 1
fi

exec env VLLM_USE_FLASHINFER_SAMPLER=0 .venv-vllm/bin/vllm serve "$MODEL_PATH" \
    --served-model-name "$SERVED_MODEL_NAME" \
    --dtype float16 \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --reasoning-parser qwen3 \
    --port "$PORT"
