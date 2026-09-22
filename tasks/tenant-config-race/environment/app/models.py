from typing import Any

from pydantic import BaseModel


class RoutingConfig(BaseModel):
    tenant_id: str
    generation: int
    model: str
    prompt_version: str
    tool_policy: dict[str, Any]
    fallback_chain: list[str]
    limits: dict[str, Any]


class ConfigUpdate(BaseModel):
    expected_generation: int
    model: str
    prompt_version: str
    tool_policy: dict[str, Any]
    fallback_chain: list[str]
    limits: dict[str, Any]
