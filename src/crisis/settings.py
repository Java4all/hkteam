from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8080
    api_base_url: str = "http://127.0.0.1:8080"

    database_url: str = ""
    postgres_user: str = "crisis"
    postgres_password: str = "crisis"
    postgres_db: str = "crisis"
    simulation_mode: bool = True
    log_level: str = "INFO"

    nvidia_api_key: str = "x"
    nim_cloud_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_local_base_url: str = "http://127.0.0.1:8000/v1"
    llm_profile: str = "multimodel"
    crisis_use_mock_llm: bool = False
    crisis_llm_timeout: float = 120.0
    # Specialist draft calls (nemotron-nano on integrate API can be slow)
    crisis_specialist_llm_timeout: float = 120.0
    # Cap tokens for specialist draft_recommendation (faster cloud responses)
    crisis_specialist_max_tokens: int = 1536
    # On timeout, retry once with this profile (fast nemotron-mini)
    crisis_specialist_fallback_profile: str = "cloud_nemotron_mini"
    # Max nested subagent invocations from workflow "subagent" actions
    crisis_max_subagent_depth: int = 2
    # Force workflows: flood:flood_critical,utilities:utilities_hospital_priority
    crisis_agent_workflows: str = ""

    langfuse_enabled: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"
    langfuse_base_url: str = ""

    @field_validator("langfuse_public_key", "langfuse_secret_key", "nvidia_api_key", mode="before")
    @classmethod
    def _strip_secrets(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    configs_dir: Path = ROOT / "configs"
    data_dir: Path = ROOT / "data"

    @property
    def llm_config_path(self) -> Path:
        return self.configs_dir / "llm" / f"{self.llm_profile}.yaml"


settings = Settings()
