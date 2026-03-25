"""Configuration constants for the trading signal system.

Fee structure modeled on E*Trade (Morgan Stanley) retail accounts.
All regulatory fees match current SEC/FINRA rates. Designed to be
swapped out for real broker API configuration when going live.
"""

from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Broker profile — E*Trade (Morgan Stanley) retail account
# ---------------------------------------------------------------------------
BROKER_NAME: str = "E*Trade"

# Commission: $0 for online US-listed stock trades
COMMISSION_PER_TRADE: float = 0.00       # $0 commission (standard since 2019)

# Options: $0.65 per contract ($0.50 for 30+ trades/quarter)
OPTIONS_PER_CONTRACT: float = 0.65
OPTIONS_PER_CONTRACT_ACTIVE: float = 0.50  # 30+ trades/quarter discount

# ---------------------------------------------------------------------------
# Regulatory fees (pass-through, charged on SELLS only)
# These are charged by every broker — not broker-specific
# Rates updated to 2026 schedule
# ---------------------------------------------------------------------------
# SEC Section 31 Transaction Fee: $20.60 per million of sell proceeds
# (effective April 4, 2026 — was $0.00 from mid-2025 to Apr 3, 2026)
# Rate: 0.00206% = $0.0000206 per $1 of sell proceeds
SEC_FEE_RATE: float = 0.0000206

# FINRA Trading Activity Fee (TAF): $0.000195 per share sold, max $9.79
# (increased from $0.000166 / $8.30 cap effective Jan 1, 2026)
FINRA_TAF_RATE: float = 0.000195
FINRA_TAF_CAP: float = 9.79

# FINRA Consolidated Audit Trail (CAT) fee
# $0.000009 per executed equivalent share (both buys and sells)
FINRA_CAT_FEE: float = 0.000009

# Options Regulatory Fee (ORF): ~$0.01 per contract aggregate (sells)
# Sum of exchange-level ORFs (Cboe $0.0023, NYSE $0.0026, MIAX $0.0014, etc.)
OPTIONS_ORF: float = 0.01

# FINRA TAF on options (sells): $0.00329 per contract (2026 rate)
OPTIONS_TAF: float = 0.00329

# ---------------------------------------------------------------------------
# Capital & position sizing
# ---------------------------------------------------------------------------
STARTING_CAPITAL: float = 1_000.0
MAX_POSITION_PCT: float = 0.20          # 20% of portfolio per trade
WHOLE_SHARES_ONLY: bool = True          # no fractional shares
MAX_OPEN_POSITIONS: int = 5             # max concurrent positions

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
# Slippage & execution (simulated)
# ---------------------------------------------------------------------------
SLIPPAGE_MIN_PCT: float = 0.0001       # 0.01%
SLIPPAGE_MAX_PCT: float = 0.0005       # 0.05%
EXEC_DELAY_MIN_MS: int = 50            # order execution delay
EXEC_DELAY_MAX_MS: int = 200

# ---------------------------------------------------------------------------
# T+1 settlement (equities, since May 2024)
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

# Extended hours (E*Trade sessions — limit orders only, no market orders)
# Overnight:    4:00 AM - 7:00 AM ET (no $25 surcharge)
# Pre-market:   7:00 AM - 9:30 AM ET
# Regular:      9:30 AM - 4:00 PM ET
# After-hours:  4:00 PM - 8:00 PM ET
EXTENDED_HOURS_ENABLED: bool = False    # disabled by default (wider spreads)
OVERNIGHT_OPEN_HOUR: int = 4
OVERNIGHT_OPEN_MINUTE: int = 0
PRE_MARKET_OPEN_HOUR: int = 7
PRE_MARKET_OPEN_MINUTE: int = 0
AFTER_HOURS_CLOSE_HOUR: int = 20
AFTER_HOURS_CLOSE_MINUTE: int = 0

# ---------------------------------------------------------------------------
# Production polling intervals
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
LOG_RETENTION: int = 500                 # keep last 500 log entries
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

# ---------------------------------------------------------------------------
# Production broker API configuration (for real trading)
# Set these in .env or environment variables when going live
# ---------------------------------------------------------------------------
# E*Trade API (OAuth 1.0a)
# ETRADE_CONSUMER_KEY: str = ""         # from E*Trade developer portal
# ETRADE_CONSUMER_SECRET: str = ""      # from E*Trade developer portal
# ETRADE_ACCOUNT_ID: str = ""           # trading account ID
# ETRADE_SANDBOX: bool = True           # True = paper trading, False = live
#
# Alpaca API (alternative broker, REST-based)
# ALPACA_API_KEY: str = ""
# ALPACA_SECRET_KEY: str = ""
# ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"  # paper trading
#
# To switch from simulation to live:
# 1. Set broker credentials in .env
# 2. Run: python -m demo.run --live
# 3. System will use real broker API for order execution
# 4. All other layers (scanner, signals, alerts) work the same
