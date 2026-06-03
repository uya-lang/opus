#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf '%s\n' "usage: tools/diff_decode.sh CORPUS_DIR" >&2
}

if [[ $# -ne 1 ]]; then
    usage
    exit 2
fi

corpus_dir=$1
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/.." && pwd)
runner="$repo_root/tools/vector_runner.py"
generator="$repo_root/tools/generate_actual_decode.py"

if [[ ! -d "$corpus_dir" ]]; then
    printf '%s\n' "error: corpus directory not found: $corpus_dir" >&2
    exit 2
fi

manifest="$corpus_dir/manifest.json"
if [[ ! -f "$manifest" ]]; then
    printf '%s\n' "error: missing manifest: $manifest" >&2
    exit 2
fi

python3 "$runner" validate "$manifest" --corpus-root "$corpus_dir"

case_count=$(python3 "$runner" list "$manifest" | awk 'END { print NR + 0 }')
if [[ "$case_count" == "0" ]]; then
    printf '%s\n' "ok: empty decoder vector corpus: $corpus_dir"
    exit 0
fi

decoder_cmd=${UOPUS_DECODE_CMD:-}
actual_dir=${UOPUS_DIFF_ACTUAL_DIR:-}
if [[ -n "$decoder_cmd" ]]; then
    if [[ -z "$actual_dir" ]]; then
        actual_dir="$repo_root/build/vectors/actual"
    fi
    mkdir -p "$actual_dir"
    python3 "$generator" "$manifest" --corpus-root "$corpus_dir" --actual-dir "$actual_dir" --decoder "$decoder_cmd"
elif [[ -z "$actual_dir" ]]; then
    printf '%s\n' \
        "error: non-empty decoder corpus requires UOPUS_DIFF_ACTUAL_DIR with pre-generated <case id>.s16le files or UOPUS_DECODE_CMD to generate them" >&2
    exit 2
elif [[ ! -d "$actual_dir" ]]; then
    printf '%s\n' "error: actual PCM directory not found: $actual_dir" >&2
    exit 2
fi

python3 "$runner" diff "$manifest" --corpus-root "$corpus_dir" --actual-dir "$actual_dir"
