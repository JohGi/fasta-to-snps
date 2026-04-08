configfile: "CONFIG/config.yaml"

from pathlib import Path
import csv


wildcard_constraints:
    sample="[^/]+"


def resolve_path(path_str: str | None, optional: bool = False) -> Path | None:
    """Resolve a path relative to the workflow base directory.

    If optional=True and path_str is empty or None, return None.
    """
    if not path_str:
        if optional:
            return None
        raise ValueError("Path is required but empty.")

    path = Path(path_str)
    if path.is_absolute():
        return path

    return Path(workflow.current_basedir) / path

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
            records.append(
                {
                    "fasta": str(resolve_path(fasta_path)),
                    "sample": sample_name,
                }
            )

    if not records:
        raise ValueError(f"Sample sheet {samples_file!r} is empty.")

    return records


def get_block_ids(_wildcards) -> list[str]:
    """Read block IDs after the checkpoint has completed."""
    block_list = checkpoints.collect_blocks.get().output[0]
    with open(block_list) as handle:
        return [line.strip() for line in handle if line.strip()]


def get_alignment_outputs(wildcards):
    """Return all expected alignment files."""
    return expand(
        ALIGN_DIR / "{block_id}.aln.fasta",
        block_id=get_block_ids(wildcards),
    )


SAMPLES = read_samples(resolve_path(config["samples"]))
SAMPLE_NAMES = [record["sample"] for record in SAMPLES]
FASTA_BY_SAMPLE = {record["sample"]: record["fasta"] for record in SAMPLES}

OUTDIR = Path(config["outdir"])
SCRIPTS_DIR = Path(workflow.current_basedir) / "workflow" / "scripts"

CLEAN_FASTA_DIR = OUTDIR / "01_clean_fasta"
SIBELIAZ_DIR = OUTDIR / "02_sibeliaz"
FILTERED_DIR = OUTDIR / "03_filtered_blocks"
BLOCK_LIST_DIR = OUTDIR / "04_block_lists"
BLOCK_FASTA_DIR = OUTDIR / "05_block_fastas"
MASKED_DIR = OUTDIR / "06_masked_block_fastas"
ALIGN_DIR = OUTDIR / "07_alignments"
LOG_DIR = OUTDIR / "logs"

CLEAN_FASTAS = expand(CLEAN_FASTA_DIR / "{sample}.fasta", sample=SAMPLE_NAMES)
SIBELIAZ_GFF = SIBELIAZ_DIR / "blocks_coords.gff"
FILTERED_GFF = FILTERED_DIR / "filtered_blocks.gff"
BLOCK_LIST = BLOCK_LIST_DIR / "kept_blocks.list"

NB_SAMPLES = len(SAMPLES)
TE_LIB = resolve_path(config.get("te_lib", ""), optional=True)
USE_MASKING = TE_LIB is not None


rule all:
    input:
        get_alignment_outputs


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

checkpoint collect_blocks:
    input:
        FILTERED_GFF
    output:
        BLOCK_LIST
    log:
        stderr=LOG_DIR / "write_kept_blocks_list" / "write_kept_blocks_list.stderr",
        stdout=LOG_DIR / "write_kept_blocks_list" / "write_kept_blocks_list.stdout"
    shell:
        r"""
        mkdir -p "{BLOCK_LIST_DIR}" "{LOG_DIR}/write_kept_blocks_list"
        bash "{SCRIPTS_DIR}/extract_block_ids.sh" \
            "{input}" \
            "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """

# rule extract_one_block_fasta:
#     input:
#         gff=FILTERED_GFF
#     output:
#         BLOCK_FASTA_DIR / "{block_id}.fasta"
#     log:
#         stderr=LOG_DIR / "extract_one_block_fasta" / "{block_id}.stderr",
#         stdout=LOG_DIR / "extract_one_block_fasta" / "{block_id}.stdout"
#     params:
#         fasta_paths=lambda wildcards: " ".join(
#             f'"{FASTA_BY_SAMPLE[sample]}"' for sample in SAMPLE_NAMES
#         ),
#         sample_names=lambda wildcards: " ".join(
#             f'"{sample}"' for sample in SAMPLE_NAMES
#         )
#     shell:
#         r"""
#         mkdir -p "{BLOCK_FASTA_DIR}" "{LOG_DIR}/extract_one_block_fasta"
#         bash "{SCRIPTS_DIR}/extract_block_fasta.sh" \
#             --block-id "{wildcards.block_id}" \
#             --gff "{input.gff}" \
#             --output "{output}" \
#             --samples {params.sample_names} \
#             --fastas {params.fasta_paths} \
#             1> "{log.stdout}" \
#             2> "{log.stderr}"
#         """

rule extract_one_block_fasta:
    input:
        gff=FILTERED_GFF,
        fastas=expand(CLEAN_FASTA_DIR / "{sample}.fasta", sample=SAMPLE_NAMES)
    output:
        BLOCK_FASTA_DIR / "{block_id}.fasta"
    log:
        stderr=LOG_DIR / "extract_one_block_fasta" / "{block_id}.stderr",
        stdout=LOG_DIR / "extract_one_block_fasta" / "{block_id}.stdout"
    params:
        sample_names=lambda wildcards: " ".join(f'"{sample}"' for sample in SAMPLE_NAMES),
        fasta_paths=lambda wildcards, input: " ".join(f'"{fasta}"' for fasta in input.fastas)
    shell:
        r"""
        mkdir -p "{BLOCK_FASTA_DIR}" "{LOG_DIR}/extract_one_block_fasta"
        bash "{SCRIPTS_DIR}/extract_block_fasta.sh" \
            --block-id "{wildcards.block_id}" \
            --gff "{input.gff}" \
            --output "{output}" \
            --samples {params.sample_names} \
            --fastas {params.fasta_paths} \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """

rule mask_one_block_fasta:
    input:
        fasta=BLOCK_FASTA_DIR / "{block_id}.fasta"
    output:
        MASKED_DIR / "{block_id}.fasta.masked"
    log:
        stderr=LOG_DIR / "mask_one_block_fasta" / "{block_id}.stderr",
        stdout=LOG_DIR / "mask_one_block_fasta" / "{block_id}.stdout"
    threads: 1
    params:
        te_lib=TE_LIB,
        outdir=str(MASKED_DIR)
    shell:
        r"""
        mkdir -p "{MASKED_DIR}" "{LOG_DIR}/mask_one_block_fasta"
        bash "{SCRIPTS_DIR}/mask_repeats.sh" \
            --fasta "{input.fasta}" \
            --te-lib "{params.te_lib}" \
            --outdir "{params.outdir}" \
            --threads {threads} \
            --output "{output}" \
            1> "{log.stdout}" \
            2> "{log.stderr}"
        """


def alignment_input(wildcards):
    """Choose masked or unmasked FASTA depending on config."""
    if USE_MASKING:
        return MASKED_DIR / f"{wildcards.block_id}.fasta.masked"
    return BLOCK_FASTA_DIR / f"{wildcards.block_id}.fasta"


rule align_one_block:
    input:
        alignment_input
    output:
        ALIGN_DIR / "{block_id}.aln.fasta"
    log:
        stderr=LOG_DIR / "align_one_block" / "{block_id}.stderr"
    threads: 1
    shell:
        r"""
        mkdir -p "{ALIGN_DIR}" "{LOG_DIR}/align_one_block"
        mafft --thread {threads} "{input}" \
            > "{output}" \
            2> "{log.stderr}"
        """
