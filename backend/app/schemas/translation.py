from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class ProviderConfig(BaseModel):
    provider: str = Field(
        default="ollama",
        description="Translation provider: 'ollama', 'gemini', or 'mock'"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="User-supplied API key for cloud services (held in memory only, never persisted)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Configured model name (e.g. 'gemini-1.5-flash', 'qwen2.5-coder:7b')"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Optional custom base URL for Ollama service"
    )
    consent_granted: bool = Field(
        default=False,
        description="Explicit user consent to transmit code to external cloud AI service"
    )


class TranslationRequest(BaseModel):
    source_lang: Language = Field(
        ...,
        description="Source programming language (python or javascript)"
    )
    target_lang: Language = Field(
        ...,
        description="Target programming language (python or javascript)"
    )
    code: str = Field(
        ...,
        min_length=1,
        max_length=65536,
        description="Source code snippet or file contents to translate"
    )
    instructions: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional guidance or constraints (e.g., 'use async/await')"
    )
    provider_config: Optional[ProviderConfig] = Field(
        default=None,
        description="Optional user-specified provider configuration"
    )

    @field_validator("code")
    @classmethod
    def validate_code_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Source code cannot be empty or contain only whitespace.")
        return v

    @field_validator("target_lang")
    @classmethod
    def validate_different_languages(cls, v: Language, info) -> Language:
        source_lang = info.data.get("source_lang")
        if source_lang and source_lang == v:
            raise ValueError(f"Source and target languages cannot be identical ('{v.value}').")
        return v


class ProviderInfo(BaseModel):
    provider: str
    model: str
    execution_time_ms: Optional[float] = None
    verified: bool = Field(
        default=False,
        description="Whether the generated code has been formally verified or executed (always False for AI-generated output)"
    )


class TranslationResponse(BaseModel):
    source_lang: Language
    target_lang: Language
    translated_code: str
    explanation: str
    warnings: List[str] = Field(default_factory=list)
    provider_info: ProviderInfo
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="Static preservation metrics and 'Know How?' analysis")


class ProviderStatusResponse(BaseModel):
    provider: str
    available: bool
    model: str
    details: str
    setup_instructions: Optional[str] = None


class ProviderTestRequest(BaseModel):
    provider: str = Field(..., description="'ollama', 'gemini', or 'mock'")
    api_key: Optional[str] = Field(default=None, description="API key to validate (if cloud provider)")
    model: Optional[str] = Field(default=None, description="Model to check")
    base_url: Optional[str] = Field(default=None, description="Custom base URL for Ollama")


class ModelOption(BaseModel):
    id: str
    label: str


class ProviderTestResponse(BaseModel):
    valid: bool
    provider: str
    model: str
    message: str
    details: Optional[str] = None
    error_type: Optional[str] = None
    available_models: Optional[List[ModelOption]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    app_name: str
