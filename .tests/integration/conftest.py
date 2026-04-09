from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def integration_cases_dir(repo_root: Path) -> Path:
    """Return the root directory containing integration test cases."""
    return repo_root / ".tests" / "integration" / "cases"


@pytest.fixture
def integration_config_dir(repo_root: Path) -> Path:
    """Return the directory containing shared integration test configuration."""
    return repo_root / ".tests" / "integration" / "config"
