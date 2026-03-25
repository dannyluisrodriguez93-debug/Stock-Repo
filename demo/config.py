"""Demo / simulation mode configuration constants."""

from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Capital & position sizing
# ---------------------------------------------------------------------------
STARTING_CAPITAL: float = 1_000.0
MAX_POSITION_PCT: float = 0.20          # 20 % of portfolio per trade
WHOLE_SHARES_ONLY: bool = True          # no fractional shares

# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
WATCHLIST: list[str] = [
    "SPY", "AAPL", "MSFT", "NVDA", "TSLA",
    "AMD", "META", "AMZN", "GOOGL",
    "BA", "LMT", "RTX", "GD", "NOC",
]

# ---------------------------------------------------------------------------
# Pattern Day Trader (PDT) rule
# ---------------------------------------------------------------------------
PDT_THRESHOLD: float = 25_000.0        # accounts below this are restricted
PDT_MAX_DAY_TRADES: int = 3            # max day trades per rolling window
PDT_ROLLING_WINDOW_DAYS: int = 5       # 5 business days

# ---------------------------------------------------------------------------
# Regulatory fees
# ---------------------------------------------------------------------------
SEC_FEE_RATE: float = 0.0000278        # per dollar of sell proceeds
FINRA_TAF_RATE: float = 0.000166       # per share sold
FINRA_TAF_CAP: float = 8.30            # max TAF per trade

# ---------------------------------------------------------------------------
# Slippage & execution
# ---------------------------------------------------------------------------
SLIPPAGE_MIN_PCT: float = 0.0001       # 0.01 %
SLIPPAGE_MAX_PCT: float = 0.0005       # 0.05 %
EXEC_DELAY_MIN_MS: int = 50
EXEC_DELAY_MAX_MS: int = 200

# ---------------------------------------------------------------------------
# T+1 settlement
# ---------------------------------------------------------------------------
SETTLEMENT_BUSINESS_DAYS: int = 1      # proceeds locked for 1 business day

# ---------------------------------------------------------------------------
# Market hours (US Eastern)
# ---------------------------------------------------------------------------
MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MINUTE: int = 30
MARKET_CLOSE_HOUR: int = 16
MARKET_CLOSE_MINUTE: int = 0

# ---------------------------------------------------------------------------
# Demo polling intervals (faster than production)
# ---------------------------------------------------------------------------
SIGNAL_SCAN_INTERVAL_SEC: float = 15.0    # scan for new setups every 15 s
VOLUME_CHECK_INTERVAL_SEC: float = 10.0   # volume confirmation every 10 s
POSITION_POLL_INTERVAL_SEC: float = 30.0  # price check on open positions every 30 s

# ---------------------------------------------------------------------------
# Technical thresholds used by SignalSimulator
# ---------------------------------------------------------------------------
RSI_OVERSOLD: float = 30.0
RSI_OVERBOUGHT: float = 70.0
VOLUME_SPIKE_RATIO: float = 2.0        # current vol / 20-day avg
