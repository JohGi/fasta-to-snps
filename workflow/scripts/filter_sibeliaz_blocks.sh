#!/usr/bin/env bash
set -euo pipefail

# Filter GFF blocks in 2-pass awk:
# Keep blocks where:
#   - max feature length > min_len
#   - number of distinct samples >= nb_samples
#   - no paralogs within a samples
#
# Output: filtered GFF to stdout

usage() {
  cat <<'EOF'
Usage:
  filter_blocks_gff.sh --gff blocks.gff --nb_samples N [--min_len 500]

Arguments:
  --gff         Input GFF file
  --nb_samples  Required minimum number of distinct samples per block
  --min_len     Minimum max feature length per block (default: 500)
  --output      Output filtered GFF file
EOF
}

parse_args() {
  gff=""
  nb_samples=""
  min_len=500
  output=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --gff) gff="${2:-}"; shift 2 ;;
      --nb_samples) nb_samples="${2:-}"; shift 2 ;;
      --min_len) min_len="${2:-}"; shift 2 ;;
      --output) output="${2:-}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "ERROR: Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
  done

  if [[ -z "$gff" ]]; then
    echo "ERROR: --gff is required." >&2
    exit 2
  fi

  if [[ -z "$nb_samples" ]]; then
    echo "ERROR: --nb_samples is required." >&2
    exit 2
  fi

  if [[ -z "$output" ]]; then
      echo "ERROR: --output is required." >&2
      exit 2
    fi

  if [[ ! -f "$gff" ]]; then
    echo "ERROR: GFF not found: $gff" >&2
    exit 2
  fi
}

run_filter() {
  local gff="$1"
  local min_len="$2"
  local nb_samples="$3"
  local output="$4"

  awk -F'\t' -v min_len="$min_len" -v nb_samples="$nb_samples" '
    # ---- pass 1: collect stats per block ID ----
    FNR==NR {
      if (!match($9, /(^|;)ID=([^;]+)/, m)) next
      id = m[2]

      # samples = prefix before first underscore (Karur_..._... -> Karur)
      split($1, a, "_")
      sp = a[1]

      # feature length (1-based inclusive)
      len = $5 - $4 + 1
      if (len > maxlen[id]) maxlen[id] = len

      key = id SUBSEP sp
      cnt[key]++
      if (cnt[key] == 1) nspp[id]++

      # mark blocks with paralogs (any samples count > 1)
      if (cnt[key] > 1) has_paralog[id] = 1

      # Track strand consistency within each block.
      strand = $7
      if (!(id in first_strand)) {
        first_strand[id] = strand
      } else if (first_strand[id] != strand) {
        mixed_strand[id] = 1
      }

      next
    }

    # ---- pass 2: print only blocks that satisfy constraints ----
    {
      if (!match($9, /(^|;)ID=([^;]+)/, m)) next
      id = m[2]

      if (maxlen[id] <= min_len) next
      if (nspp[id] < nb_samples) next
      if (has_paralog[id]) next
      if (mixed_strand[id]) next

      print
    }
  ' "$gff" "$gff" > "$output"
}

main() {
  parse_args "$@"
  run_filter "$gff" "$min_len" "$nb_samples" "$output"
}

main "$@"
