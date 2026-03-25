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
# Minimum hold time — prevents unrealistic instant exits
# ---------------------------------------------------------------------------
MIN_HOLD_SEC: float = 300.0              # 5 minutes minimum in real-sim mode
DEMO_MIN_HOLD_STEPS: int = 12            # 12 cycles (~48-90 simulated minutes)
DEMO_SIM_MINUTES_PER_STEP: tuple[int, int] = (4, 8)  # each step = 4-8 sim minutes
DEMO_CYCLE_SLEEP: tuple[float, float] = (4.0, 8.0)   # real seconds between cycles
DEMO_MAX_POSITIONS: int = 3               # max open positions (realistic for $1K)
DEMO_PRICE_DRIFT: tuple[float, float] = (-0.010, 0.010)  # symmetric, no bias

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_RETENTION: int = 500                 # keep last 500 log entries (up from 200)
TRADE_LOG_FILE: str = "demo_trade_log.jsonl"  # append-only JSONL for optimization

# ---------------------------------------------------------------------------
# Insider / Congressional signal parameters
# ---------------------------------------------------------------------------
INSIDER_SCAN_ENABLED: bool = True        # enable insider signal source
INSIDER_COOLDOWN_MIN: int = 30           # min minutes between signals for same ticker
INSIDER_BUY_PROBABILITY: float = 0.70    # 70% of insider signals are buys
CONGRESSIONAL_BUY_PROBABILITY: float = 0.65

# Max hold times for insider-driven positions (longer — these are informed)
INSIDER_MAX_HOLD_SEC: int = 96 * 3600    # 4 days
CONGRESSIONAL_MAX_HOLD_SEC: int = 120 * 3600  # 5 days

# ---------------------------------------------------------------------------
# Technical thresholds used by SignalSimulator
# ---------------------------------------------------------------------------
RSI_OVERSOLD: float = 30.0
RSI_OVERBOUGHT: float = 70.0
VOLUME_SPIKE_RATIO: float = 2.0        # current vol / 20-day avg
