"""Pydantic configuration types and schema validation models."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict as PydanticConfigDict


class DictLikeModel(BaseModel):
    model_config = PydanticConfigDict(extra="allow")

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key) or getattr(self, key) is None:
            setattr(self, key, default)
        return getattr(self, key)

    def keys(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}.keys()

    def items(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}.items()

    def values(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}.values()


class NvidiaConfig(DictLikeModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class ProviderConfig(DictLikeModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    timeout: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class CloudConfig(DictLikeModel):
    nvidia: Optional[NvidiaConfig] = None
    gemini: Optional[ProviderConfig] = None
    groq: Optional[ProviderConfig] = None
    openai: Optional[ProviderConfig] = None
    openrouter: Optional[ProviderConfig] = None
    github: Optional[ProviderConfig] = None
    deepseek: Optional[ProviderConfig] = None


class AgentConfig(DictLikeModel):
    provider: Optional[str] = None
    workspace: Optional[str] = None
    stream: Optional[bool] = None
    default_model: Optional[str] = None
    max_iterations: Optional[int] = None


class ConfigDict(DictLikeModel):
    agent: Optional[AgentConfig] = None
    cloud: Optional[CloudConfig] = None
    ops: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None
    autonomy: Optional[Dict[str, Any]] = None
    heuristics: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
