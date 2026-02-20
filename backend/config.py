from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Oracle Autonomous Database
    oracle_dsn: str = ""
    oracle_user: str = "ADMIN"
    oracle_password: str = ""
    oracle_wallet_dir: str = ""

    # OCI General
    oci_config_file: str = "~/.oci/config"
    oci_compartment_id: str = ""

    # OCI Generative AI
    oci_genai_endpoint: str = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    oci_genai_model_id: str = "cohere.command-r-plus"

    # App
    scrape_interval_hours: int = 24
    similarity_threshold: float = 0.65

    class Config:
        env_file = (".env", "backend/.env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
