rule compute_masked_block_n_stats:
    input:
        get_masked_chunk_done_outputs
    output:
        MASKED_BLOCK_N_STATS_TSV
    benchmark:
        BENCHMARK_DIR / "compute_masked_block_n_stats.tsv"
    log:
        stdout=LOG_DIR / "compute_masked_block_n_stats" / "compute_masked_block_n_stats.stdout",
        stderr=LOG_DIR / "compute_masked_block_n_stats" / "compute_masked_block_n_stats.stderr"
    shell:
        r"""
        mkdir -p "{BLOCK_STATS_DIR}" "$(dirname "{log.stdout}")"
        bash "{SCRIPTS_DIR}/write_masked_block_n_stats.sh" \
            --masked-dir "{MASKED_DIR}" \
            --output "{output}" \
            > "{log.stdout}" \
            2> "{log.stderr}"
        """
