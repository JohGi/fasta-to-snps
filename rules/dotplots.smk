rule write_pairwise_highlight_tsv:
    input:
        FILTERED_GFF
    output:
        DOTPLOT_HIGHLIGHT_DIR / "{pair_id}.tsv"
    benchmark:
        BENCHMARK_DIR / "write_pairwise_highlight_tsv" / "{pair_id}.tsv"
    log:
        stdout=LOG_DIR / "write_pairwise_highlight_tsv" / "{pair_id}.stdout",
        stderr=LOG_DIR / "write_pairwise_highlight_tsv" / "{pair_id}.stderr"
    params:
        sample_a=get_pair_sample_a,
        sample_b=get_pair_sample_b,
        color="#FF6666"
    shell:
        r"""
        mkdir -p "{DOTPLOT_HIGHLIGHT_DIR}" "$(dirname "{log.stdout}")"
        python3 "{SCRIPTS_DIR}/write_pairwise_highlight_tsv.py" \
            --gff "{input}" \
            --sample-a "{params.sample_a}" \
            --sample-b "{params.sample_b}" \
            --color "{params.color}" \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """


rule run_pairwise_minimap2:
    input:
        fasta_a=lambda wildcards: CLEAN_FASTA_DIR / f"{get_pair_sample_a(wildcards)}.fasta",
        fasta_b=lambda wildcards: CLEAN_FASTA_DIR / f"{get_pair_sample_b(wildcards)}.fasta"
    output:
        DOTPLOT_PAF_DIR / "{pair_id}.paf"
    benchmark:
        BENCHMARK_DIR / "run_pairwise_minimap2" / "{pair_id}.tsv"
    log:
        LOG_DIR / "run_pairwise_minimap2" / "{pair_id}.stderr"
    threads: 1
    shell:
        r"""
        mkdir -p "{DOTPLOT_PAF_DIR}" "$(dirname "{log}")"
        minimap2 \
            -x asm5 \
            -c \
            -t {threads} \
            "{input.fasta_a}" \
            "{input.fasta_b}" \
            > "{output}" \
            2> "{log}"
        """

rule format_pairwise_paf_for_blastn2dotplots:
    input:
        DOTPLOT_PAF_DIR / "{pair_id}.paf"
    output:
        DOTPLOT_FORMATTED_DIR / "{pair_id}.tsv"
    benchmark:
        BENCHMARK_DIR / "format_pairwise_paf_for_blastn2dotplots" / "{pair_id}.tsv"
    log:
        LOG_DIR / "format_pairwise_paf_for_blastn2dotplots" / "{pair_id}.stderr"
    params:
        converter=SCRIPTS_DIR / "blastn2dotplots_utilities/paf2blastn-fmt6.pl"
    shell:
        r"""
        mkdir -p "{DOTPLOT_FORMATTED_DIR}" "$(dirname "{log}")"
        perl "{params.converter}" "{input}" > "{output}" 2> "{log}"
        """

rule run_pairwise_blastn2dotplots:
    input:
        formatted=DOTPLOT_FORMATTED_DIR / "{pair_id}.tsv",
        highlight=DOTPLOT_HIGHLIGHT_DIR / "{pair_id}.tsv",
        fasta_a=lambda wildcards: CLEAN_FASTA_DIR / f"{get_pair_sample_a(wildcards)}.fasta",
        fasta_b=lambda wildcards: CLEAN_FASTA_DIR / f"{get_pair_sample_b(wildcards)}.fasta"
    output:
        simple=DOTPLOT_IMAGE_DIR / "{pair_id}.simple.pdf",
        # highlight_crossed=DOTPLOT_IMAGE_DIR / "{pair_id}.highlight_crossed.pdf"
    benchmark:
        BENCHMARK_DIR / "run_pairwise_blastn2dotplots" / "{pair_id}.tsv"
    log:
        stdout=LOG_DIR / "run_pairwise_blastn2dotplots" / "{pair_id}.stdout",
        stderr=LOG_DIR / "run_pairwise_blastn2dotplots" / "{pair_id}.stderr"
    params:
        db_name=get_pair_sample_a,
        query_name=get_pair_sample_b,
        simple_prefix=lambda wildcards: DOTPLOT_IMAGE_DIR / f"{wildcards.pair_id}.simple",
        highlight_prefix=lambda wildcards: DOTPLOT_IMAGE_DIR / f"{wildcards.pair_id}.highlight_crossed"
    shell:
        r"""
        mkdir -p "{DOTPLOT_IMAGE_DIR}" "$(dirname "{log.stdout}")"

        pixi run -e dotplot bash "{SCRIPTS_DIR}/run_pairwise_blastn2dotplots.sh" \
            --blastn-tsv "{input.formatted}" \
            --highlight-tsv "{input.highlight}" \
            --db-name "{params.db_name}" \
            --query-name "{params.query_name}" \
            --simple-prefix "{params.simple_prefix}" \
            --highlight-prefix "{params.highlight_prefix}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """
