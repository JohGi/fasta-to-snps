#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Run blastn2dotplots for one pair, producing a simple and a highlight_crossed PDF.

Usage:
  run_pairwise_blastn2dotplots.sh \
    --blastn-tsv pair.tsv \
    --highlight-tsv pair.highlights.tsv \
    --db-name Target \
    --query-name Query \
    --simple-prefix out/simple_prefix \
    --highlight-prefix out/highlight_prefix
EOF
}

blastn_tsv=""
highlight_tsv=""
db_name=""
query_name=""
simple_prefix=""
highlight_prefix=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --blastn-tsv)
            blastn_tsv="${2:-}"
            shift 2
            ;;
        --highlight-tsv)
            highlight_tsv="${2:-}"
            shift 2
            ;;
        --db-name)
            db_name="${2:-}"
            shift 2
            ;;
        --query-name)
            query_name="${2:-}"
            shift 2
            ;;
        --simple-prefix)
            simple_prefix="${2:-}"
            shift 2
            ;;
        --highlight-prefix)
            highlight_prefix="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown argument '$1'." >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$blastn_tsv" || -z "$highlight_tsv" || -z "$db_name" || -z "$query_name" || -z "$simple_prefix" || -z "$highlight_prefix" ]]; then
    echo "Error: missing required arguments." >&2
    usage >&2
    exit 1
fi

if [[ ! -s "$blastn_tsv" ]]; then
    echo "Error: BLAST-like TSV '$blastn_tsv' not found or empty." >&2
    exit 1
fi

if [[ ! -s "$highlight_tsv" ]]; then
    echo "Error: highlight TSV '$highlight_tsv' not found or empty." >&2
    exit 1
fi

mkdir -p "$(dirname "$simple_prefix")"
mkdir -p "$(dirname "$highlight_prefix")"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

db_file="$tmp_dir/db.txt"
query_file="$tmp_dir/query.txt"

printf "%s\t%s\n" "$db_name" "$db_name" > "$db_file"
printf "%s\t%s\n" "$query_name" "$query_name" > "$query_file"

blastn2dotplots \
    -i1 "$db_file" \
    -i2 "$query_file" \
    --blastn "$blastn_tsv" \
    --out "$simple_prefix"

# blastn2dotplots \
#     -i1 "$db_file" \
#     -i2 "$query_file" \
#     --blastn "$blastn_tsv" \
#     --highlight_crossed "$highlight_tsv" \
#     --out "$highlight_prefix"
