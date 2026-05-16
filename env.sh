#!/usr/bin/env bash
# Shared server-specific paths and environment settings for DiffuAgent jobs.
# Per-checkout jobs should set BFCL_ROOT before sourcing this file.

DIFFUAGENT_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${DIFFUAGENT_ENV_DIR}/env.local.sh" ]]; then
    source "${DIFFUAGENT_ENV_DIR}/env.local.sh"
fi

export RESEARCH_ROOT="${RESEARCH_ROOT:-/home/ilju/research}"
export DIFFUAGENT_ROOT="${DIFFUAGENT_ROOT:-${RESEARCH_ROOT}/DiffuAgent}"
export FAST_DLLM_LLADA_PATH="${FAST_DLLM_LLADA_PATH:-${RESEARCH_ROOT}/Fast-dLLM/v1/llada}"

export QWEN_ENV_NAME="${QWEN_ENV_NAME:-qwen3}"
export LLADA_ENV_NAME="${LLADA_ENV_NAME:-llada8b}"
export LLADA21_ENV_NAME="${LLADA21_ENV_NAME:-llada2.1}"

export CONDA_SH="${CONDA_SH:-/home/ilju/miniconda3/etc/profile.d/conda.sh}"
export QWEN_PYTHON="${QWEN_PYTHON:-/home/ilju/miniconda3/envs/${QWEN_ENV_NAME}/bin/python}"
export LLADA_PYTHON="${LLADA_PYTHON:-/home/ilju/miniconda3/envs/${LLADA_ENV_NAME}/bin/python}"
export LLADA21_PYTHON="${LLADA21_PYTHON:-/home/ilju/miniconda3/envs/${LLADA21_ENV_NAME}/bin/python}"

export MAIN_AGENT_MODEL_PATH="${MAIN_AGENT_MODEL_PATH:-/data/ilju/Qwen3-8B}"
export LLADA_MODEL_PATH="${LLADA_MODEL_PATH:-/data/ilju/LLaDA-8B-Instruct}"
export LLADA21_MODEL_PATH="${LLADA21_MODEL_PATH:-/data/ilju/LLaDA2.1-mini}"

# Match the original DiffuAgent REQUEST_DLLM LLaDA defaults.
export LLADA_BLOCK_LENGTH="${LLADA_BLOCK_LENGTH:-32}"
export LLADA_THRESHOLD="${LLADA_THRESHOLD:-0.9}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1}"
