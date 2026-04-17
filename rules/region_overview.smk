rule plot_region_overview:
    input:
        samples_tsv=SAMPLES_TSV,
        block_coords_tsv=BLOCK_COORDINATES_TSV,
        snp_long=SNP_POS_LONG_TSV,
        fastas=CLEAN_FASTAS
    output:
        REGION_TRACK_HTML
    benchmark:
        BENCHMARK_DIR / "plot_region_overview.tsv"
    log:
        stdout=LOG_DIR / "plot_region_overview" / "plot_region_overview.stdout",
        stderr=LOG_DIR / "plot_region_overview" / "plot_region_overview.stderr"
    shell:
        r"""
        mkdir -p "{REGION_TRACK_DIR}" "$(dirname "{log.stdout}")"
        python3 "{SCRIPTS_DIR}/plot_region_overview.py" \
            --samples-tsv "{input.samples_tsv}" \
            --block-coords-tsv "{input.block_coords_tsv}" \
            --snp-long "{input.snp_long}" \
            --fasta-dir "{CLEAN_FASTA_DIR}" \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """
