rule write_summary_stats:
    input:
        block_coords=BLOCK_COORDINATES_TSV,
        snp_positions=SNP_POS_WIDE_TSV,
        clean_fastas=CLEAN_FASTAS
    output:
        json=SUMMARY_STATS_JSON,
        txt=SUMMARY_STATS_TXT
    benchmark:
        BENCHMARK_DIR / "write_summary_stats.tsv"
    log:
        stdout=LOG_DIR / "write_summary_stats" / "write_summary_stats.stdout",
        stderr=LOG_DIR / "write_summary_stats" / "write_summary_stats.stderr"
    shell:
        r"""
        mkdir -p "{SUMMARY_STATS_DIR}" "$(dirname "{log.stdout}")"
        python3 "{SCRIPTS_DIR}/write_summary_stats.py" \
            --block-coords "{input.block_coords}" \
            --snp-positions "{input.snp_positions}" \
            --clean-fastas {input.clean_fastas} \
            --json-output "{output.json}" \
            --txt-output "{output.txt}" \
            > "{log.stdout}" \
            2> "{log.stderr}"
        """
