configfile: "config/config.yaml"

include: "rules/common.smk"
include: "rules/mash_dists.smk"
include: "rules/blocks.smk"
include: "rules/snps.smk"
include: "rules/coordinate_mapping.smk"
include: "rules/dotplots.smk"
include: "rules/summary_stats.smk"
include: "rules/block_stats.smk"
include: "rules/region_overview.smk"

rule all:
    input:
        SNP_POS_LONG_TSV,
        SNP_POS_WIDE_TSV,
        DOTPLOT_SIMPLE_PDFS,
        get_region_viewer_outputs(),
        DOTPLOT_GALLERY_HTML,
        SUMMARY_STATS_TXT
