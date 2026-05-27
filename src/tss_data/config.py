"""Configuration loading for the GCF-only TSS/promoter pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_INCLUDE_FILES = ("genome", "gff3", "gtf", "gbff", "rna", "seq-report")
REQUIRED_ORGANISM_TYPE_RULES = ("Eukaryota", "Bacteria", "Archaea", "Viruses")
ALLOWED_ORGANISM_TYPES = ("eukaryote", "prokaryote", "exclude")
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

    include_files = _validate_include_files(raw.get("include_files"))
    upstream_window = _validate_upstream_window(raw.get("upstream_window"))
    organism_type_rules = _validate_organism_type_rules(raw.get("organism_type_rules"))

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
        include_files=include_files,
        upstream_window=upstream_window,
        organism_type_rules=organism_type_rules,
        paths=paths,
        config_path=config_path,
        project_root=project_root,
    )


def _validate_include_files(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("include_files must be a list of strings")
    duplicates = sorted({item for item in value if value.count(item) > 1})
    if duplicates:
        raise ValueError(f"include_files contains duplicate entries: {', '.join(duplicates)}")
    missing = [item for item in REQUIRED_INCLUDE_FILES if item not in value]
    unknown = [item for item in value if item not in REQUIRED_INCLUDE_FILES]
    if missing:
        raise ValueError(f"include_files missing required entries: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"include_files contains unsupported entries: {', '.join(unknown)}")
    return tuple(value)


def _validate_upstream_window(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("upstream_window must be a mapping")
    required = ("prokaryote", "eukaryote")
    missing = [key for key in required if key not in value]
    unknown = [key for key in value if key not in required]
    if missing:
        raise ValueError(f"upstream_window missing required entries: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"upstream_window contains unsupported entries: {', '.join(unknown)}")

    normalized_windows: dict[str, int] = {}
    for key in required:
        window = value.get(key)
        if not isinstance(window, int) or window <= 0:
            raise ValueError(f"upstream_window.{key} must be a positive integer")
        normalized_windows[key] = window
    return normalized_windows


def _validate_organism_type_rules(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("organism_type_rules must be a mapping")
    missing = [key for key in REQUIRED_ORGANISM_TYPE_RULES if key not in value]
    unknown = [key for key in value if key not in REQUIRED_ORGANISM_TYPE_RULES]
    if missing:
        raise ValueError(f"organism_type_rules missing required entries: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"organism_type_rules contains unsupported entries: {', '.join(unknown)}")

    normalized_rules: dict[str, str] = {}
    for key in REQUIRED_ORGANISM_TYPE_RULES:
        organism_type = value[key]
        if organism_type not in ALLOWED_ORGANISM_TYPES:
            raise ValueError(
                f"organism_type_rules.{key} must be one of: {', '.join(ALLOWED_ORGANISM_TYPES)}"
            )
        normalized_rules[key] = organism_type
    return normalized_rules


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
