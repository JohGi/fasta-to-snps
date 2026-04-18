rule generate_region_viewer:
    input:
        samples_tsv=SAMPLES_TSV,
        block_coords_tsv=BLOCK_COORDINATES_TSV,
        snp_long=SNP_POS_LONG_TSV,
        fastas=CLEAN_FASTAS,
        stats_json=SUMMARY_STATS_JSON,
        mash_dists_tsv=MASHTREE_MATRIX,
        n_stats_tsv=MASKED_BLOCK_N_STATS_TSV,
        distmat_sentinels=get_distmat_chunk_sentinels
    output:
        REGION_TRACK_HTML
    benchmark:
        BENCHMARK_DIR / "generate_region_viewer.tsv"
    log:
        stdout=LOG_DIR / "generate_region_viewer" / "generate_region_viewer.stdout",
        stderr=LOG_DIR / "generate_region_viewer" / "generate_region_viewer.stderr"
    shell:
        r"""
        mkdir -p "{REGION_TRACK_DIR}" "$(dirname "{log.stdout}")"
        python3 "{SCRIPTS_DIR}/generate_region_viewer.py" \
            --samples-tsv "{input.samples_tsv}" \
            --block-coords-tsv "{input.block_coords_tsv}" \
            --snp-long "{input.snp_long}" \
            --fasta-dir "{CLEAN_FASTA_DIR}" \
            --summary-stats-json "{input.stats_json}" \
            --mash-matrix "{input.mash_dists_tsv}" \
            --kimura2p-distmat-dir "{KIMURA2P_DISTMAT_MATRIX_DIR}" \
            --masked-block-n-stats "{input.n_stats_tsv}" \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """
