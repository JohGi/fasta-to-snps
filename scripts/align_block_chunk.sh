#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Run MAFFT sequentially for all block FASTA files listed in one chunk.

Usage:
  align_block_chunk.sh \
    --chunk-list chunk_0000.list \
    --fasta-dir results/05_masked_block_fastas \
    --outdir results/06_alignments \
    --threads 1 \
    --mafft-extra-options "--auto"
EOF
}

chunk_list=""
fasta_dir=""
outdir=""
threads=""
mafft_extra_options=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --chunk-list)
            chunk_list="${2:-}"
            shift 2
            ;;
        --fasta-dir)
            fasta_dir="${2:-}"
            shift 2
            ;;
        --outdir)
            outdir="${2:-}"
            shift 2
            ;;
        --threads)
            threads="${2:-}"
            shift 2
            ;;
        --mafft-extra-options)
            mafft_extra_options="${2:-}"
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

if [[ -z "$chunk_list" || -z "$fasta_dir" || -z "$outdir" || -z "$threads" ]]; then
    echo "Error: missing required arguments." >&2
    usage >&2
    exit 1
fi

if [[ ! -s "$chunk_list" ]]; then
    echo "Error: chunk list '$chunk_list' not found or empty." >&2
    exit 1
fi

if [[ ! -d "$fasta_dir" ]]; then
    echo "Error: FASTA directory '$fasta_dir' not found." >&2
    exit 1
fi

mkdir -p "$outdir"

while read -r block_id; do
    [[ -z "$block_id" ]] && continue

    fasta_path=""
    if [[ -s "${fasta_dir}/${block_id}.fasta.masked" ]]; then
        fasta_path="${fasta_dir}/${block_id}.fasta.masked"
    elif [[ -s "${fasta_dir}/${block_id}.fasta" ]]; then
        fasta_path="${fasta_dir}/${block_id}.fasta"
    else
        echo "Error: no FASTA found for block '${block_id}' in '${fasta_dir}'." >&2
        exit 1
    fi

    output_path="${outdir}/${block_id}.aln.fasta"

    echo "[INFO] Aligning block '${block_id}'." >&2

    mafft --thread "$threads" $mafft_extra_options "$fasta_path" > "$output_path"
done < "$chunk_list"
