configfile: "CONFIG/config.yaml"

from pathlib import Path
import csv


wildcard_constraints:
    sample="[^/]+"


def read_samples(samples_file: str) -> list[dict[str, str]]:
    """Read a sample sheet with 2 or 3 tab-separated columns.

    Only the first two columns are used:
        1. FASTA path
        2. Sample name
    """
    records = []
    with open(samples_file, newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if len(row) not in {2, 3}:
                raise ValueError(
                    f"Invalid line in sample sheet {samples_file!r}: "
                    f"expected 2 or 3 tab-separated columns, got {len(row)} -> {row!r}"
                )
            fasta_path, sample_name = row[:2]
            records.append({"fasta": fasta_path, "sample": sample_name})

    if not records:
        raise ValueError(f"Sample sheet {samples_file!r} is empty.")

    return records


SAMPLES = read_samples(config["samples"])
SAMPLE_NAMES = [record["sample"] for record in SAMPLES]
FASTA_BY_SAMPLE = {record["sample"]: record["fasta"] for record in SAMPLES}

OUTDIR = Path(config["outdir"])
SCRIPTS_DIR = Path(workflow.current_basedir) / "workflow" / "scripts"

CLEAN_FASTA_DIR = OUTDIR / "01_clean_fasta"
SIBELIAZ_DIR = OUTDIR / "02_sibeliaz"
FILTERED_DIR = OUTDIR / "03_filtered_blocks"
EXTRACT_DIR = OUTDIR / "04_extracted_sequences"
LOG_DIR = OUTDIR / "logs"

CLEAN_FASTAS = expand(CLEAN_FASTA_DIR / "{sample}.fasta", sample=SAMPLE_NAMES)
MULTIFASTA = CLEAN_FASTA_DIR / "multifasta" / "all_genomes.fasta"
SIBELIAZ_GFF = SIBELIAZ_DIR / "blocks_coords.gff"
FILTERED_GFF = FILTERED_DIR / "filtered_blocks.gff"
BLOCKS_FASTA = EXTRACT_DIR / "blocks_seq.fasta"

NB_SAMPLES = len(SAMPLES)


rule all:
    input:
      BLOCKS_FASTA


rule rename_fasta_header:
    input:
        lambda wildcards: FASTA_BY_SAMPLE[wildcards.sample]
    output:
        CLEAN_FASTA_DIR / "{sample}.fasta"
    log:
        stdout=LOG_DIR / "rename_fasta_header" / "{sample}.stdout",
        stderr=LOG_DIR / "rename_fasta_header" / "{sample}.stderr"
    shell:
        r"""
        mkdir -p "{CLEAN_FASTA_DIR}" "{LOG_DIR}/rename_fasta_header"
        bash "{SCRIPTS_DIR}/rename_fasta_header.sh" \
            --fasta "{input}" \
            --name "{wildcards.sample}" \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """


rule build_multifasta:
    input:
        CLEAN_FASTAS
    output:
        MULTIFASTA
    log:
        stdout=LOG_DIR / "build_multifasta" / "build_multifasta.stdout",
        stderr=LOG_DIR / "build_multifasta" / "build_multifasta.stderr"
    shell:
        r"""
        mkdir -p "{CLEAN_FASTA_DIR}/multifasta" "{LOG_DIR}/build_multifasta"
        cat {input} > "{output}" 2> "{log.stderr}"
        """


rule run_sibeliaz:
    input:
        CLEAN_FASTAS
    output:
        SIBELIAZ_GFF
    log:
        stdout=LOG_DIR / "run_sibeliaz" / "run_sibeliaz.stdout",
        stderr=LOG_DIR / "run_sibeliaz" / "run_sibeliaz.stderr"
    params:
        outdir=str(SIBELIAZ_DIR),
        min_block_len=config["sibeliaz"]["min_block_len"]
    shell:
        r"""
        mkdir -p "{params.outdir}" "{LOG_DIR}/run_sibeliaz"
        sibeliaz \
            -n \
            -f {params.min_block_len} \
            -o "{params.outdir}" \
            {input} \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """


rule filter_sibeliaz_blocks:
    input:
        SIBELIAZ_GFF
    output:
        FILTERED_GFF
    log:
        stdout=LOG_DIR / "filter_sibeliaz_blocks" / "filter_sibeliaz_blocks.stdout",
        stderr=LOG_DIR / "filter_sibeliaz_blocks" / "filter_sibeliaz_blocks.stderr"
    params:
        nb_samples=NB_SAMPLES,
        min_len=config["filtering"]["min_len"]
    shell:
        r"""
        mkdir -p "{FILTERED_DIR}" "{LOG_DIR}/filter_sibeliaz_blocks"
        bash "{SCRIPTS_DIR}/filter_sibeliaz_blocks.sh" \
            --gff "{input}" \
            --nb_samples {params.nb_samples} \
            --min_len {params.min_len} \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """

rule extract_block_sequences:
    input:
        fasta=MULTIFASTA,
        gff=FILTERED_GFF
    output:
        BLOCKS_FASTA
    log:
        stdout=LOG_DIR / "extract_block_sequences" / "extract_block_sequences.stdout",
        stderr=LOG_DIR / "extract_block_sequences" / "extract_block_sequences.stderr"
    shell:
        r"""
        mkdir -p "{EXTRACT_DIR}" "{LOG_DIR}/extract_block_sequences"
        bedtools getfasta \
            -fi "{input.fasta}" \
            -bed "{input.gff}" \
            -fo "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """
