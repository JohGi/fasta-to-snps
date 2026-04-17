rule compute_mashtree_distances:
    input:
        CLEAN_FASTAS
    output:
        matrix=MASHTREE_MATRIX,
        tree=MASHTREE_TREE
    threads: 1
    log:
        stdout=LOG_DIR / "compute_mashtree_distances" / "compute_mashtree_distances.stdout",
        stderr=LOG_DIR / "compute_mashtree_distances" / "compute_mashtree_distances.stderr"
    benchmark:
        BENCHMARK_DIR / "compute_mashtree_distances.tsv"
    shell:
        r"""
        mkdir -p "{MASH_DISTANCES_DIR}" "$(dirname "{log.stdout}")"
        pixi run -e mashtree mashtree \
            --numcpus {threads} \
            --outmatrix "{output.matrix}" \
            --outtree "{output.tree}" \
            {input} \
            > "{log.stdout}" \
            2> "{log.stderr}"
        """
