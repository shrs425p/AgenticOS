"""TypedDict definitions for configuration sections (static typing helpers).

These types are intentionally lightweight and `total=False` so they can be
used as hints without enforcing strict runtime checks. They improve IDE
completion and serve as a single place to document common config keys.
"""
from typing import TypedDict, Dict, Any


class NvidiaConfig(TypedDict, total=False):
    base_url: str
    model: str
    timeout: int
    temperature: float
    top_p: float
    max_tokens: int


class ProviderConfig(TypedDict, total=False):
    model: str
    base_url: str
    timeout: int
    temperature: float
    top_p: float
    max_tokens: int


class CloudConfig(TypedDict, total=False):
    nvidia: NvidiaConfig
    gemini: ProviderConfig
    groq: ProviderConfig
    openai: ProviderConfig
    openrouter: ProviderConfig
    github: ProviderConfig
    deepseek: ProviderConfig


class AgentConfig(TypedDict, total=False):
    provider: str
    workspace: str
    stream: bool
    default_model: str
    max_iterations: int


class ConfigDict(TypedDict, total=False):
    agent: AgentConfig
    cloud: CloudConfig
    tools: Dict[str, Any]
    performance: Dict[str, Any]
    logging: Dict[str, Any]
    memory: Dict[str, Any]
    policy: Dict[str, Any]
    autonomy: Dict[str, Any]
    heuristics: Dict[str, Any]
    prompts: Dict[str, Any]
