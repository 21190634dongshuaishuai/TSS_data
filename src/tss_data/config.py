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
    "download_zip",
    "interim_dir",
    "processed_dir",
    "log_dir",
)

REQUIRED_INVENTORY_ELIGIBILITY_KEYS = (
    "require_gcf_prefix",
    "exclude_suppressed",
    "exclude_excluded_from_refseq",
    "exclude_genome_rep_partial",
    "allowed_groups",
    "excluded_groups",
)


@dataclass(frozen=True)
class PipelinePaths:
    input_accessions: Path
    raw_dir: Path
    download_zip: Path
    interim_dir: Path
    processed_dir: Path
    log_dir: Path


@dataclass(frozen=True)
class InventoryEligibilityRules:
    require_gcf_prefix: bool
    exclude_suppressed: bool
    exclude_excluded_from_refseq: bool
    exclude_genome_rep_partial: bool
    allowed_groups: tuple[str, ...]
    excluded_groups: tuple[str, ...]


@dataclass(frozen=True)
class InventoryConfig:
    source_url: str
    local_path: Path
    output_dir: Path
    allow_network: bool
    force_download: bool
    eligibility_rules: InventoryEligibilityRules


@dataclass(frozen=True)
class PipelineConfig:
    assembly_scope: str
    assembly_source: str
    include_files: tuple[str, ...]
    upstream_window: dict[str, int]
    organism_type_rules: dict[str, str]
    paths: PipelinePaths
    inventory: InventoryConfig
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
        download_zip=_resolve_download_zip(project_root, paths_raw["download_zip"]),
        interim_dir=_resolve_project_path(project_root, paths_raw["interim_dir"]),
        processed_dir=_resolve_project_path(project_root, paths_raw["processed_dir"]),
        log_dir=_resolve_project_path(project_root, paths_raw["log_dir"]),
    )
    inventory = _validate_inventory_config(raw.get("inventory"), project_root)

    return PipelineConfig(
        assembly_scope=assembly_scope,
        assembly_source=assembly_source,
        include_files=include_files,
        upstream_window=upstream_window,
        organism_type_rules=organism_type_rules,
        paths=paths,
        inventory=inventory,
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


def _validate_inventory_config(value: Any, project_root: Path) -> InventoryConfig:
    if not isinstance(value, dict):
        raise ValueError("inventory must be a mapping")

    source_url = _require_str(value, "source_url")
    local_path = _resolve_project_path(project_root, value.get("local_path"))
    output_dir = _resolve_project_path(project_root, value.get("output_dir"))
    allow_network = _require_bool(value, "allow_network")
    force_download = _require_bool(value, "force_download")
    rules = _validate_inventory_eligibility_rules(value.get("eligibility_rules"))

    return InventoryConfig(
        source_url=source_url,
        local_path=local_path,
        output_dir=output_dir,
        allow_network=allow_network,
        force_download=force_download,
        eligibility_rules=rules,
    )


def _validate_inventory_eligibility_rules(value: Any) -> InventoryEligibilityRules:
    if not isinstance(value, dict):
        raise ValueError("inventory.eligibility_rules must be a mapping")
    missing = [key for key in REQUIRED_INVENTORY_ELIGIBILITY_KEYS if key not in value]
    unknown = [key for key in value if key not in REQUIRED_INVENTORY_ELIGIBILITY_KEYS]
    if missing:
        raise ValueError(f"inventory.eligibility_rules missing required entries: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"inventory.eligibility_rules contains unsupported entries: {', '.join(unknown)}")

    return InventoryEligibilityRules(
        require_gcf_prefix=_require_bool(value, "require_gcf_prefix"),
        exclude_suppressed=_require_bool(value, "exclude_suppressed"),
        exclude_excluded_from_refseq=_require_bool(value, "exclude_excluded_from_refseq"),
        exclude_genome_rep_partial=_require_bool(value, "exclude_genome_rep_partial"),
        allowed_groups=_require_str_tuple(value, "allowed_groups"),
        excluded_groups=_require_str_tuple(value, "excluded_groups"),
    )


def _require_bool(config: dict[str, Any], key: str) -> bool:
    value = config.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _require_str_tuple(config: dict[str, Any], key: str) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{key} must be a non-empty list of strings")
    duplicates = sorted({item for item in value if value.count(item) > 1})
    if duplicates:
        raise ValueError(f"{key} contains duplicate entries: {', '.join(duplicates)}")
    return tuple(value)


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


def _resolve_download_zip(project_root: Path, value: Any) -> Path:
    path = _resolve_project_path(project_root, value)
    if path.suffix != ".zip":
        raise ValueError("paths.download_zip must point to a .zip file")
    if not _is_relative_to(path, project_root):
        raise ValueError("paths.download_zip must stay within the project directory")
    return path


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
