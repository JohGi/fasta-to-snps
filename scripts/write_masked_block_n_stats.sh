#!/usr/bin/env bash
# Author: Johanna Girodolle

set -euo pipefail

usage() {
    cat <<EOF
Usage:
  write_masked_block_n_stats.sh \
    --masked-dir <dir> \
    --output <path>

Description:
  Aggregate N-content statistics for all masked block FASTA files in a directory.
EOF
}

parse_args() {
    MASKED_DIR=""
    OUTPUT=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --masked-dir)
                MASKED_DIR="$2"
                shift 2
                ;;
            --output)
                OUTPUT="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "[ERROR] Unknown argument: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done

    if [[ -z "${MASKED_DIR}" || -z "${OUTPUT}" ]]; then
        echo "[ERROR] Missing required arguments." >&2
        usage >&2
        exit 1
    fi
}

get_python_script_path() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PYTHON_SCRIPT="${script_dir}/compute_n_stats.py"
}

write_header() {
    local output_path="$1"
    printf "block_id\tsample\tlength_bp\tn_count\tn_pct\n" > "$output_path"
}

append_stats_for_all_fastas() {
    local masked_dir="$1"
    local python_script="$2"
    local output_path="$3"

    local fasta
    shopt -s nullglob
    for fasta in "${masked_dir}"/*.fasta.masked; do
        python3 "${python_script}" --input "$fasta" >> "$output_path"
    done
    shopt -u nullglob
}

main() {
    parse_args "$@"
    get_python_script_path

    local tmp_output
    tmp_output="${OUTPUT}.tmp"

    write_header "$tmp_output"
    append_stats_for_all_fastas "$MASKED_DIR" "$PYTHON_SCRIPT" "$tmp_output"

    mv "$tmp_output" "$OUTPUT"
}

main "$@"
