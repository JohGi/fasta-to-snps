from __future__ import annotations

import filecmp
import shutil
import subprocess
from pathlib import Path


def copy_case_input(case_input_dir: Path, workdir: Path) -> None:
    """Copy one integration test input case into a temporary work directory."""
    shutil.copytree(case_input_dir, workdir, dirs_exist_ok=True)


def prepare_test_config(base_config: Path, workdir: Path) -> Path:
    """Copy the shared integration test config into the temporary work directory."""
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    shutil.copy2(base_config, config_path)

    return config_path


def run_snakemake(
    repo_root: Path,
    workdir: Path,
    target: str,
    configfile: Path,
) -> None:
    """Run Snakemake on one target in an isolated work directory."""
    subprocess.run(
        [
            "snakemake",
            "-s",
            str(repo_root / "Snakefile"),
            "--directory",
            str(workdir),
            "--configfile",
            str(configfile),
            "--cores",
            "1",
            target,
        ],
        check=True,
    )


def compare_directories(expected_dir: Path, observed_dir: Path) -> None:
    """Recursively compare two directories."""
    assert expected_dir.exists(), f"Missing expected directory: {expected_dir}"
    assert observed_dir.exists(), f"Missing observed directory: {observed_dir}"

    expected_files = sorted(
        path.relative_to(expected_dir)
        for path in expected_dir.rglob("*")
        if path.is_file()
    )
    observed_files = sorted(
        path.relative_to(observed_dir)
        for path in observed_dir.rglob("*")
        if path.is_file()
    )

    assert expected_files == observed_files, (
        f"File lists differ.\nExpected: {expected_files}\nObserved: {observed_files}"
    )

    for relative_path in expected_files:
        expected_file = expected_dir / relative_path
        observed_file = observed_dir / relative_path
        assert filecmp.cmp(expected_file, observed_file, shallow=False), (
            f"Files differ: {relative_path}"
        )
