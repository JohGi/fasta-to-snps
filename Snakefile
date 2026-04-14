configfile: "config/config.yaml"

include: "rules/common.smk"
include: "rules/blocks.smk"
include: "rules/snps.smk"
include: "rules/coordinate_mapping.smk"

rule all:
    input:
        SNP_POS_LONG_TSV,
        SNP_POS_WIDE_TSV
