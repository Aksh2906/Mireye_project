from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_api_key: str | None = None
    database_url: str = "sqlite+pysqlite:///./mireye.sqlite3"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-sol"
    openai_reasoning_effort: str = "medium"
    mireye_api_url: str | None = None
    mireye_api_token: str | None = None
    mireye_mcp_url: str | None = None
    mireye_mcp_token: str | None = None
    geocoder_base_url: str = "https://nominatim.openstreetmap.org"
    cdl_service_url: str = "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLValue"
    ssurgo_service_url: str = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
    nass_quickstats_base_url: str = "https://quickstats.nass.usda.gov/api/api_GET/"
    nass_quickstats_api_key: str | None = None
    market_benchmark_url: str | None = None
    market_comparables_url: str | None = None
    max_agent_turns: int = 12
    max_tool_calls: int = 30
    max_external_requests: int = 30
    max_wall_clock_seconds: int = 180
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
