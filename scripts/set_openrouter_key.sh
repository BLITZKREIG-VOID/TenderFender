#!/usr/bin/env bash
# Save your OpenRouter API key for the RAG decision writer (DECISION_MODE=llm).
# The key is stored OUTSIDE the repo, readable only by you, and never printed.
#
#   bash scripts/set_openrouter_key.sh          # prompts for the key (hidden input)
#   bash scripts/set_openrouter_key.sh --remove # deletes the saved key
#
# Used by: source ~/.config/tenderfender/openrouter.env && make decide DECISION_MODE=llm
# The deployed site does not need the key: it serves the cached decisions in artifacts/decisions/.
set -euo pipefail

dir="${XDG_CONFIG_HOME:-$HOME/.config}/tenderfender"
file="$dir/openrouter.env"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$file" && echo "Removed $file"
  exit 0
fi

read -rs -p "Paste your OpenRouter API key (input hidden): " key
echo
key="${key//[[:space:]]/}"
if [ -z "$key" ]; then
  echo "ERROR: no key entered; nothing saved." >&2
  exit 1
fi
case "$key" in
  sk-or-*) ;;
  *) echo "WARNING: key does not start with 'sk-or-'; saving anyway." >&2 ;;
esac

umask 077
mkdir -p "$dir"
chmod 700 "$dir"
printf 'export OPENROUTER_API_KEY=%q\n' "$key" > "$file"
chmod 600 "$file"
unset key
echo "Saved to $file (permissions 600). It is outside the repo and never committed."
echo "Use it with: source \"$file\" && make decide DECISION_MODE=llm"
