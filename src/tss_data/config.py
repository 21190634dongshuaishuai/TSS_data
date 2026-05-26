"""Configuration loading for the GCF-only TSS/promoter pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_INCLUDE_FILES = ("genome", "gff3", "gtf", "gbff", "rna", "seq-report")
REQUIRED_PATH_KEYS = (
    "input_accessions",
    "raw_dir",
    "interim_dir",
    "processed_dir",
    "log_dir",
)


@dataclass(frozen=True)
class PipelinePaths:
    input_accessions: Path
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    log_dir: Path


@dataclass(frozen=True)
class PipelineConfig:
    assembly_scope: str
    assembly_source: str
    include_files: tuple[str, ...]
    upstream_window: dict[str, int]
    organism_type_rules: dict[str, str]
    paths: PipelinePaths
    config_path: Path
    project_root: Path


def load_config(path: str | Path) -> PipelineConfig:
    """Load and validate a pipeline YAML config file."""

    config_path = Path(path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")

    assembly_scope = _require_str(raw, "assembly_scope")
    if assembly_scope != "GCF_only":
        raise ValueError("assembly_scope must be 'GCF_only'")

    assembly_source = _require_str(raw, "assembly_source")
    if assembly_source != "RefSeq":
        raise ValueError("assembly_source must be 'RefSeq'")

    include_files = raw.get("include_files")
    if not isinstance(include_files, list) or not all(isinstance(item, str) for item in include_files):
        raise ValueError("include_files must be a list of strings")
    missing = [item for item in REQUIRED_INCLUDE_FILES if item not in include_files]
    if missing:
        raise ValueError(f"include_files missing required entries: {', '.join(missing)}")

    upstream_window = raw.get("upstream_window")
    if not isinstance(upstream_window, dict):
        raise ValueError("upstream_window must be a mapping")
    normalized_windows: dict[str, int] = {}
    for key in ("prokaryote", "eukaryote"):
        value = upstream_window.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"upstream_window.{key} must be a positive integer")
        normalized_windows[key] = value

    organism_type_rules = raw.get("organism_type_rules")
    if not isinstance(organism_type_rules, dict):
        raise ValueError("organism_type_rules must be a mapping")
    normalized_rules = {str(key): str(value) for key, value in organism_type_rules.items()}

    paths_raw = raw.get("paths")
    if not isinstance(paths_raw, dict):
        raise ValueError("paths must be a mapping")
    missing_paths = [key for key in REQUIRED_PATH_KEYS if key not in paths_raw]
    if missing_paths:
        raise ValueError(f"paths missing required entries: {', '.join(missing_paths)}")

    project_root = config_path.parent.parent
    paths = PipelinePaths(
        input_accessions=_resolve_project_path(project_root, paths_raw["input_accessions"]),
        raw_dir=_resolve_project_path(project_root, paths_raw["raw_dir"]),
        interim_dir=_resolve_project_path(project_root, paths_raw["interim_dir"]),
        processed_dir=_resolve_project_path(project_root, paths_raw["processed_dir"]),
        log_dir=_resolve_project_path(project_root, paths_raw["log_dir"]),
    )

    return PipelineConfig(
        assembly_scope=assembly_scope,
        assembly_source=assembly_source,
        include_files=tuple(include_files),
        upstream_window=normalized_windows,
        organism_type_rules=normalized_rules,
        paths=paths,
        config_path=config_path,
        project_root=project_root,
    )


def _require_str(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _resolve_project_path(project_root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("Configured paths must be non-empty strings")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()
