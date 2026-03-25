"""Centralized configuration using Pydantic BaseSettings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


def _load_yaml_config() -> dict[str, Any]:
    config_path = Path(__file__).parent / "settings.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = _load_yaml_config()


class ScannerSettings(BaseModel):
    poll_interval_sec: int = 45
    sources: list[str] = [
        "reuters_rss", "ap_rss", "google_news_rss",
        "defense_news_rss", "sec_edgar", "twitter", "bloomberg",
    ]


class DedupSettings(BaseModel):
    ttl_hours: int = 24


class ClassifierSettings(BaseModel):
    model: str = "gpt-4o"
    red_flag_magnitude: int = 3
    red_flag_confidence: float = 0.6
    yellow_flag_magnitude: int = 2


class DeepDiveSettings(BaseModel):
    lookback_days: int = 30
    volume_spike_threshold: float = 2.5
    volume_window_minutes: int = 30
    volume_poll_interval_sec: int = 60


class TechnicalSettings(BaseModel):
    rsi_period: int = 14
    vwap_enabled: bool = True
    atr_period: int = 14
    atr_stop_multiplier: float = 1.0
    entry_proximity_pct: float = 1.0


class ScaledExitLevel(BaseModel):
    pct: float
    sell_fraction: float


class ExitSettings(BaseModel):
    trailing_stop_pct: float = 1.5
    scaled_exit_threshold_pct: float = 6.0
    scaled_exit_levels: list[ScaledExitLevel] = [
        ScaledExitLevel(pct=6.0, sell_fraction=0.5),
        ScaledExitLevel(pct=8.0, sell_fraction=0.25),
        ScaledExitLevel(pct=10.0, sell_fraction=1.0),
    ]
    volume_divergence_candles: int = 3


class TimeDecaySettings(BaseModel):
    geopolitical_hours: int = 4
    earnings_surprise_hours: int = 48
    contract_win_hours: int = 72
    regulatory_shift_hours: int = 168

    def hours_for_catalyst(self, catalyst_type: str) -> int:
        mapping = {
            "geopolitical": self.geopolitical_hours,
            "earnings": self.earnings_surprise_hours,
            "earnings_surprise": self.earnings_surprise_hours,
            "contract_win": self.contract_win_hours,
            "contract": self.contract_win_hours,
            "regulatory": self.regulatory_shift_hours,
            "regulatory_shift": self.regulatory_shift_hours,
        }
        return mapping.get(catalyst_type.lower(), self.contract_win_hours)


class AlertSettings(BaseModel):
    primary_channel: str = "telegram"
    approval_timeout_sec: int = 300
    fallback_channel: str = "sms"


class ExecutionSettings(BaseModel):
    broker: str = "alpaca"
    paper_trading: bool = True


class DatabaseSettings(BaseModel):
    path: str = "data/trades.db"


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_output: bool = True


class Settings(BaseSettings):
    # API keys from environment
    openai_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_to_number: str = ""
    twitter_bearer_token: str = ""
    discord_webhook_url: str = ""

    # Subsections from YAML
    scanner: ScannerSettings = ScannerSettings(**_yaml.get("scanner", {}))
    dedup: DedupSettings = DedupSettings(**_yaml.get("dedup", {}))
    classifier: ClassifierSettings = ClassifierSettings(**_yaml.get("classifier", {}))
    deepdive: DeepDiveSettings = DeepDiveSettings(**_yaml.get("deepdive", {}))
    technical: TechnicalSettings = TechnicalSettings(**_yaml.get("technical", {}))
    exit: ExitSettings = ExitSettings(**_yaml.get("exit", {}))
    time_decay: TimeDecaySettings = TimeDecaySettings(**_yaml.get("time_decay", {}))
    alert: AlertSettings = AlertSettings(**_yaml.get("alert", {}))
    execution: ExecutionSettings = ExecutionSettings(**_yaml.get("execution", {}))
    database: DatabaseSettings = DatabaseSettings(**_yaml.get("database", {}))
    logging: LoggingSettings = LoggingSettings(**_yaml.get("logging", {}))

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
