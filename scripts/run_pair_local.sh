#!/usr/bin/env bash
set -euo pipefail

# Local wrapper to run pair benchmark in your own terminal session.
# Usage:
#   ./scripts/run_pair_local.sh MODEL_A MODEL_B [MAX_TASKS]
#
# Example:
#   ./scripts/run_pair_local.sh gpt-4o-mini gpt-4.1-mini 20

MODEL_A="${1:-}"
MODEL_B="${2:-}"
MAX_TASKS="${3:-20}"
REQUEST_INTERVAL_S="${REQUEST_INTERVAL_S:-1.5}"
MAX_RETRIES="${MAX_RETRIES:-8}"
MAX_TOKENS="${MAX_TOKENS:-700}"

if [[ -z "${MODEL_A}" || -z "${MODEL_B}" ]]; then
  echo "Usage: ./scripts/run_pair_local.sh MODEL_A MODEL_B [MAX_TASKS]"
  exit 1
fi

# Provider selection:
# - If model looks like Gemini and GEMINI_API_KEY is set, force Gemini endpoint.
# - Otherwise prefer OPENAI_API_KEY if present.
# - Else fallback to OPENROUTER_API_KEY for OpenRouter convenience.
# - Else fallback to GEMINI_API_KEY.
MODEL_HINT="$(printf "%s %s" "${MODEL_A}" "${MODEL_B}" | tr '[:upper:]' '[:lower:]')"
if [[ "${MODEL_HINT}" == *"gemini"* && -n "${GEMINI_API_KEY:-}" ]]; then
  API_KEY_TO_USE="${GEMINI_API_KEY}"
  BASE_URL_TO_USE="${OPENAI_BASE_URL:-https://generativelanguage.googleapis.com/v1beta/openai}"
  PROVIDER_NAME="gemini"
elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
  API_KEY_TO_USE="${OPENAI_API_KEY}"
  BASE_URL_TO_USE="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
  PROVIDER_NAME="openai-compatible"
elif [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
  API_KEY_TO_USE="${OPENROUTER_API_KEY}"
  BASE_URL_TO_USE="${OPENAI_BASE_URL:-https://openrouter.ai/api/v1}"
  PROVIDER_NAME="openrouter"
elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
  API_KEY_TO_USE="${GEMINI_API_KEY}"
  BASE_URL_TO_USE="${OPENAI_BASE_URL:-https://generativelanguage.googleapis.com/v1beta/openai}"
  PROVIDER_NAME="gemini"
else
  echo "No API key found."
  echo "Set one of:"
  echo "  export OPENAI_API_KEY=\"YOUR_KEY\""
  echo "  export OPENROUTER_API_KEY=\"YOUR_KEY\""
  echo "  export GEMINI_API_KEY=\"YOUR_KEY\""
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_JSON="${TASKS_JSON:-${ROOT_DIR}/tasks/generated_practical_loop_tasks_hard.json}"
OUT_DIR="${ROOT_DIR}/results/pair_runs"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python runtime not found: ${PYTHON_BIN}"
  echo "Set PYTHON_BIN explicitly, for example:"
  echo "  PYTHON_BIN=/opt/homebrew/bin/python3 ./scripts/run_pair_local.sh \"${MODEL_A}\" \"${MODEL_B}\" ${MAX_TASKS}"
  exit 1
fi

if [[ ! -f "${TASKS_JSON}" ]]; then
  echo "Tasks file not found: ${TASKS_JSON}"
  echo "Generate practical loop tasks first, for example:"
  echo "  python scripts/build_practical_loop_tasks.py --input_json tasks/generated_practical_loop_tasks.json --output_json tasks/generated_practical_loop_tasks_hard.json --max_tasks 80 --hard_mode"
  exit 1
fi

echo "Running pair benchmark..."
echo "  model_a   : ${MODEL_A}"
echo "  model_b   : ${MODEL_B}"
echo "  max_tasks : ${MAX_TASKS}"
echo "  tasks_json: ${TASKS_JSON}"
echo "  interval  : ${REQUEST_INTERVAL_S}s"
echo "  retries   : ${MAX_RETRIES}"
echo "  max_tokens: ${MAX_TOKENS}"
echo "  provider  : ${PROVIDER_NAME}"
echo "  base_url  : ${BASE_URL_TO_USE}"
echo

OPENAI_API_KEY="${API_KEY_TO_USE}" OPENAI_BASE_URL="${BASE_URL_TO_USE}" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/run_openai_compatible_pair.py" \
  --tasks_json "${TASKS_JSON}" \
  --model_a "${MODEL_A}" \
  --model_b "${MODEL_B}" \
  --max_tasks "${MAX_TASKS}" \
  --request_interval_s "${REQUEST_INTERVAL_S}" \
  --max_retries "${MAX_RETRIES}" \
  --max_tokens "${MAX_TOKENS}" \
  --validate_models \
  --output_dir "${OUT_DIR}"

LATEST_SUMMARY="$(ls -t "${OUT_DIR}"/*_summary.csv 2>/dev/null | head -n 1 || true)"
if [[ -z "${LATEST_SUMMARY}" ]]; then
  echo "No summary CSV found under ${OUT_DIR}"
  exit 1
fi

echo
echo "Latest summary: ${LATEST_SUMMARY}"
echo "Analyzing..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/analyze_pair_summary.py" \
  --summary_csv "${LATEST_SUMMARY}" \
  --model_a "${MODEL_A}" \
  --model_b "${MODEL_B}"

echo
echo "Done."
