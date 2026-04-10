#!/usr/bin/env python3

import argparse


def read_list(path):
    """Read one value per line."""
    return [l.strip() for l in open(path) if l.strip()]


def parse_header(line):
    """Return column index mapping."""
    header = line.strip().split("\t")
    return {name: i for i, name in enumerate(header)}


def is_discriminant(fields, idx, group_a, group_b):
    """Return True if SNP discriminates the two groups."""
    vals_a = [fields[idx[s]] for s in group_a]
    vals_b = [fields[idx[s]] for s in group_b]

    return (
        len(set(vals_a)) == 1
        and len(set(vals_b)) == 1
        and vals_a[0] != vals_b[0]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--group-a-file", required=True)
    parser.add_argument("--group-b-file", required=True)
    args = parser.parse_args()

    group_a = read_list(args.group_a_file)
    group_b = read_list(args.group_b_file)

    with open(args.input) as fin, open(args.output, "w") as fout:
        for line in fin:
            if line.startswith("#CHROM"):
                idx = parse_header(line)
                fout.write(line)

            elif line.startswith("#"):
                fout.write(line)

            else:
                fields = line.strip().split("\t")

                if is_discriminant(fields, idx, group_a, group_b):
                    fout.write(line)


if __name__ == "__main__":
    main()
