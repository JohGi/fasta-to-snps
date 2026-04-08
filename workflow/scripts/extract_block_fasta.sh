#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Extract all sequences belonging to one SibeliaZ block using bedtools getfasta.

Usage:
  extract_block_fasta.sh \
    --block-id BLOCK_ID \
    --gff filtered_blocks.gff \
    --output block.fasta \
    --samples sample1 sample2 ... \
    --fastas fasta1 fasta2 ...

Notes:
  - The number of samples and FASTA paths must match.
  - FASTA files must contain sequence names matching the GFF seqnames.
  - Coordinates are converted from GFF (1-based inclusive) to BED (0-based, end-exclusive).
  - Strand is ignored on purpose.
EOF
}

block_id=""
gff=""
output=""
sample_names=()
fasta_paths=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --block-id)
            block_id="${2:-}"
            shift 2
            ;;
        --gff)
            gff="${2:-}"
            shift 2
            ;;
        --output)
            output="${2:-}"
            shift 2
            ;;
        --samples)
            shift
            while [[ $# -gt 0 && "$1" != "--fastas" ]]; do
                sample_names+=("$1")
                shift
            done
            ;;
        --fastas)
            shift
            while [[ $# -gt 0 ]]; do
                fasta_paths+=("$1")
                shift
            done
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument '$1'." >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$block_id" || -z "$gff" || -z "$output" ]]; then
    echo "ERROR: missing required arguments." >&2
    usage >&2
    exit 1
fi

if [[ ! -s "$gff" ]]; then
    echo "ERROR: GFF '$gff' not found or empty." >&2
    exit 1
fi

if [[ ${#sample_names[@]} -eq 0 ]]; then
    echo "ERROR: no sample names were provided." >&2
    exit 1
fi

if [[ ${#sample_names[@]} -ne ${#fasta_paths[@]} ]]; then
    echo "ERROR: number of samples and FASTA paths does not match." >&2
    exit 1
fi

for fasta in "${fasta_paths[@]}"; do
    if [[ ! -s "$fasta" ]]; then
        echo "ERROR: FASTA '$fasta' not found or empty." >&2
        exit 1
    fi
done

mkdir -p "$(dirname "$output")"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

coord_table="$tmp_dir/block_coords.tsv"

awk -F'\t' -v block_id="$block_id" '
    $0 !~ /^#/ {
        found = 0
        n = split($9, attrs, ";")
        for (i = 1; i <= n; i++) {
            if (attrs[i] == "ID=" block_id) {
                found = 1
            }
        }
        if (found) {
            print $1 "\t" $4 "\t" $5
        }
    }
' "$gff" > "$coord_table"

if [[ ! -s "$coord_table" ]]; then
    echo "ERROR: block ID '$block_id' was not found in '$gff'." >&2
    exit 1
fi

: > "$output"

for i in "${!sample_names[@]}"; do
    sample="${sample_names[$i]}"
    fasta="${fasta_paths[$i]}"
    bed_file="$tmp_dir/${sample}.bed"
    fasta_tmp="$tmp_dir/${sample}.fasta"

    awk -F'\t' -v sample="$sample" '
        $1 == sample {
            start0 = $2 - 1
            end1 = $3
            print $1 "\t" start0 "\t" end1 "\t" $1 ":" $2 "-" $3
        }
    ' "$coord_table" > "$bed_file"

    if [[ ! -s "$bed_file" ]]; then
        continue
    fi

    bedtools getfasta \
        -fi "$fasta" \
        -bed "$bed_file" \
        -nameOnly \
        -fo "$fasta_tmp"

    cat "$fasta_tmp" >> "$output"
done

if [[ ! -s "$output" ]]; then
    echo "ERROR: no sequence was extracted for block '$block_id'." >&2
    exit 1
fi
