from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_seconds: int
    retries: int
    cost_model: str
    provenance_required: bool = True
    authorization_policy: str = "server-side agent runtime only"


TOOL_REGISTRY = {
    item.name: item
    for item in [
        ToolDefinition(
            "mireye.fetch_context",
            "Fetch normalized physical context through Mireye MCP",
            {"type": "object", "required": ["latitude", "longitude"]},
            {"type": "object"},
            60,
            2,
            "provider-reported",
        ),
        ToolDefinition(
            "mireye.quote_request",
            "Quote a Mireye field request before execution",
            {"type": "object", "required": ["latitude", "longitude", "fields"]},
            {"type": "object"},
            30,
            1,
            "provider-reported",
        ),
        ToolDefinition(
            "mireye.fetch_batch_context",
            "Fetch multiple Mireye contexts using provider batching when available",
            {"type": "object", "required": ["coordinates"]},
            {"type": "array"},
            90,
            2,
            "provider-reported",
        ),
        ToolDefinition(
            "agriculture.get_crop_history",
            "Fetch USDA CDL observations",
            {"type": "object", "required": ["latitude", "longitude", "years"]},
            {"type": "object"},
            45,
            2,
            "free/public",
        ),
        ToolDefinition(
            "agriculture.get_soil_context",
            "Fetch USDA SSURGO soil context",
            {"type": "object", "required": ["latitude", "longitude"]},
            {"type": "object"},
            45,
            2,
            "free/public",
        ),
        ToolDefinition(
            "market.get_benchmark",
            "Fetch configured agricultural value benchmark",
            {"type": "object"},
            {"type": "object"},
            45,
            1,
            "provider-specific",
        ),
        ToolDefinition(
            "market.find_comparables",
            "Fetch traceable comparable agricultural transactions",
            {"type": "object"},
            {"type": "object"},
            45,
            1,
            "provider-specific",
        ),
    ]
}


def validate_tool_call(name: str, arguments: dict[str, Any]) -> None:
    definition = TOOL_REGISTRY.get(name)
    if not definition:
        raise ValueError(f"Unknown tool: {name}")
    missing = set(definition.input_schema.get("required", [])) - set(arguments)
    if missing:
        raise ValueError(f"Missing tool arguments: {', '.join(sorted(missing))}")
