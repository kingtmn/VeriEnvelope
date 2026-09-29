"""Load and validate the published JSON Schemas."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError

from verienvelope.errors import MethodError, SchemaError, VeriEnvelopeError


def repo_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    if not (root / "CONSTITUTION.md").is_file():
        raise VeriEnvelopeError(
            "Reference runner could not find the VeriEnvelope checkout "
            f"(looked at {root}). Run it from this repository."
        )
    return root


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    path = repo_root() / "schemas" / schema_name
    if not path.is_file():
        raise SchemaError(f"schema file is missing: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
    except JsonSchemaError as exc:
        raise SchemaError(f"{schema_name} is not a valid schema: {exc.message}") from exc
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_instance(schema_name: str, instance: Any) -> None:
    errors = sorted(
        _validator(schema_name).iter_errors(instance),
        key=lambda item: list(item.path),
    )
    if not errors:
        return
    lines = []
    for err in errors:
        location = "/".join(str(part) for part in err.path) or "(root)"
        lines.append(f"{location}: {err.message}")
    raise SchemaError(schema_name + " rejected the object:\n" + "\n".join(lines))


def load_json(path: Path) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{path} is not valid JSON: {exc}") from exc
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MethodError(f"method file is missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MethodError(f"{path} did not contain a mapping")
    return data


def dump_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
