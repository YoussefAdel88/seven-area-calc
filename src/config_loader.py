import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_json_config(filename: str) -> Dict[str, Any]:
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_measurement_rules() -> Dict[str, Any]:
    data = load_json_config("seven_measurement_rules.json")
    if not isinstance(data, dict) or "measurement_rules" not in data:
        raise ValueError("Invalid measurement rule configuration: missing 'measurement_rules'.")
    if "void_measurement_rules" not in data:
        raise ValueError("Invalid measurement rule configuration: missing 'void_measurement_rules'.")
    if "wall_classification_rules" not in data:
        raise ValueError("Invalid measurement rule configuration: missing 'wall_classification_rules'.")
    return data


def load_parts() -> Dict[str, Any]:
    data = load_json_config("seven_parts.json")
    if not isinstance(data, dict) or "parts" not in data:
        raise ValueError("Invalid part configuration: missing 'parts'.")
    return data


def build_rule_lookup() -> Dict[str, Dict[str, Any]]:
    data = load_measurement_rules()
    lookup: Dict[str, Dict[str, Any]] = {}
    for section in ("measurement_rules", "void_measurement_rules", "wall_classification_rules"):
        for item in data.get(section, []):
            rule_id = item.get("id")
            if not rule_id:
                raise ValueError(f"Measurement rule in section '{section}' is missing an 'id'.")
            if rule_id in lookup:
                raise ValueError(f"Duplicate measurement rule id found: {rule_id}")
            lookup[rule_id] = item
    return lookup


def build_part_lookup() -> Dict[str, Dict[str, Any]]:
    data = load_parts()
    lookup: Dict[str, Dict[str, Any]] = {}
    for item in data.get("parts", []):
        part_id = item.get("id")
        if not part_id:
            raise ValueError("Part definition missing 'id'.")
        if part_id in lookup:
            raise ValueError(f"Duplicate part id found: {part_id}")
        lookup[part_id] = item
    return lookup
