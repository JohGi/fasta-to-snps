rule write_gff_tracks_json:
    input:
        gff_files=GFF_TRACK_FILES
    output:
        GFF_TRACKS_JSON
    benchmark:
        BENCHMARK_DIR / "write_gff_tracks_json.tsv"
    log:
        stdout=LOG_DIR / "write_gff_tracks_json" / "write_gff_tracks_json.stdout",
        stderr=LOG_DIR / "write_gff_tracks_json" / "write_gff_tracks_json.stderr"
    run:
        import json

        output_path = Path(output[0])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(GFF_TRACKS, handle, indent=2)
            handle.write("\n")

rule generate_region_viewer:
    input:
        samples_tsv=SAMPLES_TSV,
        block_coords_tsv=BLOCK_COORDINATES_TSV,
        snp_long=SNP_POS_LONG_TSV,
        fastas=CLEAN_FASTAS,
        stats_json=SUMMARY_STATS_JSON,
        mash_dists_tsv=MASHTREE_MATRIX,
        n_stats_tsv=MASKED_BLOCK_N_STATS_TSV,
        align_sentinels=get_align_chunk_sentinels,
        distmat_sentinels=get_distmat_chunk_sentinels,
        gff_tracks_json=GFF_TRACKS_JSON,
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
            --masked-align-dir "{ALIGN_DIR}" \
            --masked-block-n-stats "{input.n_stats_tsv}" \
            --gff-tracks-json "{input.gff_tracks_json}" \
            --config-yaml "{workflow.configfiles[0]}" \
            --title "{PROJECT_TITLE}" \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """
