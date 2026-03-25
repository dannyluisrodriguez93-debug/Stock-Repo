"""Core simulation engine - real market data, simulated execution.

Scans real yfinance data for technical setups, simulates order execution
with realistic constraints (PDT, T+1, fees, slippage, market hours).
"""

import asyncio
import random
import time
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from demo.config import (
    EXEC_DELAY_MAX_MS,
    EXEC_DELAY_MIN_MS,
    FINRA_TAF_CAP,
    FINRA_TAF_RATE,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_TZ,
    MAX_POSITION_PCT,
    MIN_HOLD_SEC,
    PDT_MAX_DAY_TRADES,
    PDT_ROLLING_WINDOW_DAYS,
    PDT_THRESHOLD,
    POSITION_POLL_INTERVAL_SEC,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SEC_FEE_RATE,
    SETTLEMENT_BUSINESS_DAYS,
    SIGNAL_SCAN_INTERVAL_SEC,
    SLIPPAGE_MAX_PCT,
    SLIPPAGE_MIN_PCT,
    STARTING_CAPITAL,
    VOLUME_CHECK_INTERVAL_SEC,
    VOLUME_SPIKE_RATIO,
    WATCHLIST,
    WHOLE_SHARES_ONLY,
)
from demo.dashboard_state import DashboardState
from demo.demo_signals import CATALYST_TEMPLATES, TICKER_SECTOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_et() -> datetime:
    return datetime.now(MARKET_TZ)


def _is_market_open() -> bool:
    now = _now_et()
    if now.weekday() >= 5:  # Sat / Sun
        return False
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0)
    return market_open <= now <= market_close


def _next_market_event() -> str:
    now = _now_et()
    today_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    today_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0)

    if _is_market_open():
        delta = today_close - now
        mins = int(delta.total_seconds() // 60)
        return f"Closes in {mins // 60}h {mins % 60}m"
    elif now < today_open and now.weekday() < 5:
        delta = today_open - now
        mins = int(delta.total_seconds() // 60)
        return f"Opens in {mins // 60}h {mins % 60}m"
    else:
        # Next business day
        days_ahead = 1
        nxt = now + timedelta(days=days_ahead)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        nxt = nxt.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
        delta = nxt - now
        hours = int(delta.total_seconds() // 3600)
        return f"Opens in {hours}h"


def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def _compute_vwap(df: pd.DataFrame) -> float:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    cumvol = df["Volume"].cumsum()
    cumtp = (tp * df["Volume"]).cumsum()
    vwap = cumtp / cumvol
    val = vwap.iloc[-1]
    return float(val) if not pd.isna(val) else float(df["Close"].iloc[-1])


# ---------------------------------------------------------------------------
# SimulatedAccount
# ---------------------------------------------------------------------------

class SimulatedAccount:
    """Paper trading account with real-world constraint enforcement."""

    def __init__(self, starting_cash: float = STARTING_CAPITAL) -> None:
        self.cash = starting_cash
        self.starting_capital = starting_cash
        self.positions: dict[str, dict] = {}   # ticker -> {qty, entry_price, entry_time}
        self.trade_history: list[dict] = []
        self.equity_history: list[tuple[str, float]] = []
        self._day_trades: deque = deque()       # timestamps of day trades
        self._unsettled: list[dict] = []        # {amount, available_at}

    @property
    def equity(self) -> float:
        pos_value = sum(
            p.get("current_price", p["entry_price"]) * p["qty"]
            for p in self.positions.values()
        )
        return self.cash + pos_value

    @property
    def unsettled_funds(self) -> float:
        now = datetime.utcnow()
        return sum(u["amount"] for u in self._unsettled if u["available_at"] > now)

    @property
    def available_cash(self) -> float:
        return self.cash - self.unsettled_funds

    @property
    def day_trades_remaining(self) -> int:
        if self.equity >= PDT_THRESHOLD:
            return 999  # unlimited
        self._prune_day_trades()
        return max(0, PDT_MAX_DAY_TRADES - len(self._day_trades))

    def _prune_day_trades(self) -> None:
        cutoff = datetime.utcnow() - timedelta(days=PDT_ROLLING_WINDOW_DAYS)
        while self._day_trades and self._day_trades[0] < cutoff:
            self._day_trades.popleft()

    def can_buy(self, price: float, qty: int) -> tuple[bool, str]:
        cost = price * qty
        if cost > self.available_cash:
            return False, f"Insufficient cash: need ${cost:.2f}, have ${self.available_cash:.2f}"
        if cost > self.equity * MAX_POSITION_PCT:
            return False, f"Position too large: ${cost:.2f} exceeds {MAX_POSITION_PCT*100:.0f}% of equity"
        return True, ""

    def can_day_trade(self) -> tuple[bool, str]:
        if self.equity >= PDT_THRESHOLD:
            return True, ""
        self._prune_day_trades()
        if len(self._day_trades) >= PDT_MAX_DAY_TRADES:
            return False, f"PDT limit reached: {len(self._day_trades)}/{PDT_MAX_DAY_TRADES} day trades used"
        return True, ""

    def compute_fees(self, price: float, qty: int, is_sell: bool) -> dict:
        """Compute all fees for a trade, matching E*Trade fee structure.

        Returns dict with breakdown for logging. Commission is $0 for
        online equity trades. Regulatory fees only apply to sells.
        """
        from demo.config import COMMISSION_PER_TRADE, FINRA_CAT_FEE

        commission = COMMISSION_PER_TRADE  # $0 for E*Trade equity trades
        sec_fee = 0.0
        finra_taf = 0.0
        # CAT fee applies to both buys and sells ($0.000009 per share)
        finra_cat = round(qty * FINRA_CAT_FEE, 6)

        if is_sell:
            proceeds = price * qty
            sec_fee = round(proceeds * SEC_FEE_RATE, 6)
            finra_taf = round(min(qty * FINRA_TAF_RATE, FINRA_TAF_CAP), 6)

        total = round(commission + sec_fee + finra_taf + finra_cat, 4)
        return {
            "total": total,
            "commission": commission,
            "sec_fee": round(sec_fee, 6),
            "finra_taf": round(finra_taf, 6),
            "finra_cat": round(finra_cat, 6),
        }

    def apply_slippage(self, price: float, is_buy: bool) -> float:
        slip_pct = random.uniform(SLIPPAGE_MIN_PCT, SLIPPAGE_MAX_PCT)
        if is_buy:
            return round(price * (1 + slip_pct), 2)
        return round(price * (1 - slip_pct), 2)

    def buy(self, ticker: str, price: float, qty: int) -> dict:
        fill_price = self.apply_slippage(price, is_buy=True)
        cost = fill_price * qty
        fee_breakdown = self.compute_fees(fill_price, qty, is_sell=False)
        fees = fee_breakdown["total"]
        total = cost + fees

        self.cash -= total
        self.positions[ticker] = {
            "qty": qty,
            "entry_price": fill_price,
            "entry_time": datetime.utcnow(),
            "current_price": fill_price,
        }

        return {
            "fill_price": fill_price,
            "slippage": round(fill_price - price, 4),
            "fees": fees,
            "fee_breakdown": fee_breakdown,
            "total_cost": round(total, 2),
        }

    def sell(self, ticker: str, price: float) -> dict | None:
        if ticker not in self.positions:
            return None

        pos = self.positions[ticker]
        qty = pos["qty"]
        fill_price = self.apply_slippage(price, is_buy=False)
        proceeds = fill_price * qty
        fee_breakdown = self.compute_fees(fill_price, qty, is_sell=True)
        fees = fee_breakdown["total"]
        net_proceeds = proceeds - fees

        # Check if this is a day trade
        is_day_trade = pos["entry_time"].date() == datetime.utcnow().date()
        if is_day_trade:
            self._day_trades.append(datetime.utcnow())

        # T+1 settlement
        available_at = datetime.utcnow() + timedelta(days=SETTLEMENT_BUSINESS_DAYS)
        self._unsettled.append({"amount": net_proceeds, "available_at": available_at})

        self.cash += net_proceeds

        pnl_gross = (fill_price - pos["entry_price"]) * qty
        pnl_net = pnl_gross - fees
        pnl_pct = (pnl_net / (pos["entry_price"] * qty)) * 100
        hold_secs = (datetime.utcnow() - pos["entry_time"]).total_seconds()

        result = {
            "ticker": ticker,
            "direction": "long",
            "qty": qty,
            "entry_price": pos["entry_price"],
            "entry_time": pos["entry_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "exit_price": fill_price,
            "exit_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "exit_slippage": round(price - fill_price, 4),
            "fees": fees,
            "fee_breakdown": fee_breakdown,
            "pnl_gross": round(pnl_gross, 2),
            "pnl_net": round(pnl_net, 2),
            "pnl_pct": round(pnl_pct, 2),
            "hold_duration_sec": round(hold_secs, 1),
            "is_day_trade": is_day_trade,
        }

        del self.positions[ticker]
        self.trade_history.append(result)
        return result

    def record_equity(self) -> None:
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self.equity_history.append((ts, round(self.equity, 2)))

    def max_shares(self, price: float) -> int:
        max_spend = min(self.available_cash, self.equity * MAX_POSITION_PCT)
        if price <= 0:
            return 0
        qty = int(max_spend / price)
        return max(0, qty)


# ---------------------------------------------------------------------------
# SignalSimulator - scans real data for technical setups
# ---------------------------------------------------------------------------

class SignalSimulator:
    """Scans real yfinance data for actionable technical setups."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = 60  # 1 min cache

    async def _get_data(self, ticker: str, period: str = "30d", interval: str = "1d") -> pd.DataFrame | None:
        key = f"{ticker}|{period}|{interval}"
        now = time.time()
        if key in self._cache:
            df, ts = self._cache[key]
            if now - ts < self._cache_ttl:
                return df

        try:
            stock = yf.Ticker(ticker)
            df = await asyncio.to_thread(stock.history, period=period, interval=interval)
            if df.empty:
                return None
            self._cache[key] = (df, now)
            return df
        except Exception:
            return None

    async def scan_ticker(self, ticker: str) -> dict | None:
        """Check a single ticker for a tradeable setup. Returns signal dict or None."""
        df_daily = await self._get_data(ticker, "30d", "1d")
        if df_daily is None or len(df_daily) < 20:
            return None

        close = df_daily["Close"]
        volume = df_daily["Volume"]
        current_price = float(close.iloc[-1])

        # RSI
        rsi = _compute_rsi(close)

        # Volume spike
        avg_vol = float(volume.tail(20).mean())
        current_vol = float(volume.iloc[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0

        # Support / resistance (simple pivot)
        recent_high = float(df_daily["High"].tail(10).max())
        recent_low = float(df_daily["Low"].tail(10).min())

        # SMA crossover
        sma_10 = float(close.tail(10).mean())
        sma_20 = float(close.tail(20).mean())

        # Determine if there's a setup
        signal = None

        # Bullish: RSI recovering from oversold + volume spike + price above SMA
        if rsi < 40 and vol_ratio >= VOLUME_SPIKE_RATIO and current_price > sma_20:
            signal = self._build_signal(ticker, "bullish", current_price, recent_low, recent_high, rsi, vol_ratio, 4)

        # Bullish breakout: price breaking above recent high on volume
        elif current_price >= recent_high * 0.99 and vol_ratio >= 1.5 and rsi < RSI_OVERBOUGHT:
            signal = self._build_signal(ticker, "bullish", current_price, recent_low, recent_high * 1.05, rsi, vol_ratio, 3)

        # Bearish: RSI overbought + volume spike + price below SMA
        elif rsi > RSI_OVERBOUGHT and vol_ratio >= VOLUME_SPIKE_RATIO and current_price < sma_10:
            signal = self._build_signal(ticker, "bearish", current_price, recent_high, recent_low, rsi, vol_ratio, 3)

        # Momentum: strong volume + SMA bullish crossover
        elif sma_10 > sma_20 and vol_ratio >= 1.8 and 40 < rsi < 65:
            signal = self._build_signal(ticker, "bullish", current_price, recent_low, recent_high, rsi, vol_ratio, 3)

        return signal

    def _build_signal(
        self, ticker: str, direction: str, price: float,
        support: float, resistance: float, rsi: float,
        vol_ratio: float, magnitude: int,
    ) -> dict:
        sector = TICKER_SECTOR.get(ticker, "technical")
        templates = CATALYST_TEMPLATES.get(sector, CATALYST_TEMPLATES["technical"])
        headline = random.choice(templates).format(ticker=ticker)
        confidence = min(0.95, 0.5 + (vol_ratio - 1.0) * 0.15 + (magnitude - 1) * 0.05)

        return {
            "ticker": ticker,
            "direction": direction,
            "catalyst_type": sector,
            "headline": headline,
            "magnitude": magnitude,
            "confidence": round(confidence, 2),
            "price": round(price, 2),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "rsi": round(rsi, 2),
            "volume_ratio": round(vol_ratio, 2),
            "flag_level": "RED" if magnitude >= 3 and confidence >= 0.6 else "YELLOW",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def scan_all(self) -> list[dict]:
        """Scan entire watchlist. Returns list of signal dicts."""
        tasks = [self.scan_ticker(t) for t in WATCHLIST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals = []
        for r in results:
            if isinstance(r, dict):
                signals.append(r)
        return signals


# ---------------------------------------------------------------------------
# DemoExecutor - manages positions with exit strategies
# ---------------------------------------------------------------------------

class DemoExecutor:
    """Simulates trade execution with real price tracking."""

    def __init__(self, account: SimulatedAccount, state: DashboardState) -> None:
        self.account = account
        self.state = state
        self._exit_tasks: dict[str, asyncio.Task] = {}

    async def execute_entry(self, signal: dict) -> bool:
        """Attempt to enter a position based on signal."""
        ticker = signal["ticker"]
        price = signal["price"]

        if ticker in self.account.positions:
            self.state.add_log(f"Already in {ticker}, skipping", "WARN")
            return False

        # Check PDT
        can_dt, reason = self.account.can_day_trade()
        if not can_dt:
            self.state.add_log(f"PDT block: {reason}", "WARN")
            return False

        # Position sizing
        qty = self.account.max_shares(price)
        if qty <= 0:
            self.state.add_log(f"Cannot afford {ticker} at ${price:.2f}", "WARN")
            return False

        can_buy, reason = self.account.can_buy(price, qty)
        if not can_buy:
            self.state.add_log(f"Buy blocked: {reason}", "WARN")
            return False

        # Simulate execution delay
        delay_ms = random.randint(EXEC_DELAY_MIN_MS, EXEC_DELAY_MAX_MS)
        await asyncio.sleep(delay_ms / 1000.0)

        # Execute buy
        result = self.account.buy(ticker, price, qty)

        self.state.add_log(
            f"ENTRY {qty} {ticker} @ ${result['fill_price']:.2f} "
            f"(slip: ${result['slippage']:.4f}, fees: ${result['fees']:.4f}, "
            f"cost: ${result['total_cost']:.2f})",
            "TRADE",
        )
        self.state.add_log(
            f"  Signal: {signal['direction']} {signal['flag_level']} | "
            f"RSI={signal.get('rsi', 'N/A')} vol={signal.get('volume_ratio', 'N/A')}x "
            f"mag={signal.get('magnitude', 'N/A')} conf={signal.get('confidence', 'N/A')}",
            "INFO",
        )
        self.state.add_log(
            f"  Sizing: ${result['total_cost']:.2f} / ${self.account.equity:.2f} = "
            f"{result['total_cost']/self.account.equity*100:.1f}% of equity | "
            f"Cash remaining: ${self.account.available_cash:.2f}",
            "INFO",
        )

        # Start monitoring position
        exit_task = asyncio.create_task(
            self._monitor_position(ticker, signal)
        )
        self._exit_tasks[ticker] = exit_task

        return True

    async def _monitor_position(self, ticker: str, signal: dict) -> None:
        """Monitor position with parallel exit triggers."""
        if ticker not in self.account.positions:
            return

        pos = self.account.positions[ticker]
        entry_price = pos["entry_price"]
        target = signal["resistance"]
        stop_loss = signal["support"]
        catalyst = signal["catalyst_type"]

        # Time decay limits (in seconds)
        time_limits = {
            "geopolitical": 4 * 3600,
            "earnings": 48 * 3600,
            "contract_win": 72 * 3600,
            "regulatory": 168 * 3600,
            "supply_chain": 48 * 3600,
            "macro": 24 * 3600,
            "technical": 8 * 3600,
            "insider_buy": 96 * 3600,       # 4 days — insiders are informed
            "insider_sell": 72 * 3600,      # 3 days
            "congressional_buy": 120 * 3600, # 5 days — congress has oversight
            "congressional_sell": 96 * 3600, # 4 days
            "confirmed_insider_buy": 144 * 3600,       # 6 days — double signal
            "confirmed_congressional_buy": 168 * 3600,  # 7 days — strongest signal
        }
        max_hold_sec = time_limits.get(catalyst, 24 * 3600)

        trailing_stop_pct = 0.015  # 1.5%
        high_water = entry_price
        entry_time = time.time()
        prev_volumes = []

        self.state.add_log(
            f"Monitoring {ticker}: target=${target:.2f} stop=${stop_loss:.2f} "
            f"trailing=1.5% max_hold={max_hold_sec // 3600}h min_hold={MIN_HOLD_SEC:.0f}s",
            "INFO",
        )
        self.state.add_log(
            f"  Entry: ${entry_price:.2f} | RSI={signal.get('rsi', 'N/A')} "
            f"vol_ratio={signal.get('volume_ratio', 'N/A')}x | catalyst={catalyst}",
            "INFO",
        )

        check_count = 0
        while ticker in self.account.positions:
            await asyncio.sleep(POSITION_POLL_INTERVAL_SEC)
            check_count += 1

            try:
                stock = yf.Ticker(ticker)
                data = await asyncio.to_thread(
                    stock.history, period="1d", interval="1m"
                )
                if data.empty:
                    continue

                current_price = float(data["Close"].iloc[-1])
                current_vol = float(data["Volume"].iloc[-1])
                self.account.positions[ticker]["current_price"] = current_price

                elapsed = time.time() - entry_time
                pnl_unrealized = (current_price - entry_price) * pos["qty"]
                pnl_pct = (pnl_unrealized / (entry_price * pos["qty"])) * 100

                # Log position check every 5th check
                if check_count % 5 == 0:
                    self.state.add_log(
                        f"  {ticker} check #{check_count}: ${current_price:.2f} "
                        f"P&L=${pnl_unrealized:.2f} ({pnl_pct:+.1f}%) "
                        f"HWM=${high_water:.2f} elapsed={int(elapsed)}s",
                        "INFO",
                    )

                # ---- Enforce minimum hold time ----
                if elapsed < MIN_HOLD_SEC:
                    self._update_dashboard_positions()
                    continue

                exit_trigger = None
                exit_detail = ""

                # Update high water mark
                if current_price > high_water:
                    high_water = current_price

                # 1. Take-profit
                if signal["direction"] == "bullish" and current_price >= target:
                    exit_trigger = "take_profit"
                    exit_detail = f"Price ${current_price:.2f} >= target ${target:.2f}"
                elif signal["direction"] == "bearish" and current_price <= target:
                    exit_trigger = "take_profit"
                    exit_detail = f"Price ${current_price:.2f} <= target ${target:.2f}"

                # 2. Trailing stop
                trailing_stop = high_water * (1 - trailing_stop_pct)
                if signal["direction"] == "bullish" and current_price <= trailing_stop:
                    exit_trigger = "trailing_stop"
                    exit_detail = (
                        f"Price ${current_price:.2f} <= trailing ${trailing_stop:.2f} "
                        f"(HWM ${high_water:.2f})"
                    )

                # 3. Hard stop loss
                if signal["direction"] == "bullish" and current_price <= stop_loss:
                    exit_trigger = "stop_loss"
                    exit_detail = f"Price ${current_price:.2f} <= stop ${stop_loss:.2f}"

                # 4. Time decay
                if elapsed >= max_hold_sec:
                    exit_trigger = "time_decay"
                    exit_detail = f"Held {int(elapsed)}s >= max {max_hold_sec}s ({catalyst})"

                # 5. Volume divergence
                prev_volumes.append(current_vol)
                if len(prev_volumes) >= 4:
                    recent_prices_rising = current_price > entry_price
                    recent_vol_declining = all(
                        prev_volumes[-i - 1] < prev_volumes[-i - 2]
                        for i in range(3)
                    )
                    if recent_prices_rising and recent_vol_declining:
                        exit_trigger = "volume_divergence"
                        exit_detail = "Price rising but volume declining 3 consecutive checks"

                # Update dashboard position
                self._update_dashboard_positions()

                if exit_trigger:
                    self.state.add_log(
                        f"Exit trigger fired for {ticker}: {exit_trigger} | {exit_detail}",
                        "WARN",
                    )
                    await self._execute_exit(ticker, current_price, exit_trigger, signal)
                    return

            except Exception as e:
                self.state.add_log(f"Monitor error {ticker}: {e}", "ERROR")

    async def _execute_exit(self, ticker: str, price: float, trigger: str, signal: dict) -> None:
        """Execute sell order."""
        delay_ms = random.randint(EXEC_DELAY_MIN_MS, EXEC_DELAY_MAX_MS)
        await asyncio.sleep(delay_ms / 1000.0)

        result = self.account.sell(ticker, price)
        if not result:
            return

        result["exit_trigger"] = trigger
        result["catalyst"] = signal.get("headline", "")
        result["signal_confidence"] = signal.get("confidence", 0)

        color = "PROFIT" if result["pnl_net"] >= 0 else "LOSS"
        self.state.add_log(
            f"EXIT {result['qty']} {ticker} @ ${result['exit_price']:.2f} | "
            f"P&L: gross=${result['pnl_gross']:.2f} fees=${result['fees']:.4f} "
            f"net=${result['pnl_net']:.2f} ({result['pnl_pct']:.1f}%) | "
            f"Trigger: {trigger}",
            color,
        )
        hold_mins = result["hold_duration_sec"] / 60
        fb = result.get("fee_breakdown", {})
        self.state.add_log(
            f"  Hold: {hold_mins:.1f}min | Entry=${result['entry_price']:.2f} "
            f"Exit=${result['exit_price']:.2f} | Slippage=${result.get('exit_slippage', 0):.4f}",
            "INFO",
        )
        self.state.add_log(
            f"  Fees (E*Trade): commission=${fb.get('commission', 0):.2f} "
            f"SEC=${fb.get('sec_fee', 0):.6f} TAF=${fb.get('finra_taf', 0):.6f} "
            f"CAT=${fb.get('finra_cat', 0):.6f} total=${result['fees']:.4f}",
            "INFO",
        )

        # Log to file for optimization analysis
        self.state.log_trade_to_file({
            **result,
            "catalyst_type": signal.get("catalyst_type", ""),
            "rsi_at_entry": signal.get("rsi", None),
            "volume_ratio_at_entry": signal.get("volume_ratio", None),
            "support": signal.get("support", None),
            "resistance": signal.get("resistance", None),
            "equity_at_exit": round(self.account.equity, 2),
        })

        # Update dashboard
        self.state.add_trade(result)
        self.account.record_equity()
        self.state.add_equity_point(
            datetime.utcnow().strftime("%H:%M:%S"),
            self.account.equity,
        )
        self._update_dashboard_positions()
        self._update_dashboard_account()

    def _update_dashboard_positions(self) -> None:
        positions = []
        for ticker, pos in self.account.positions.items():
            unrealized = (pos.get("current_price", pos["entry_price"]) - pos["entry_price"]) * pos["qty"]
            unrealized_pct = (unrealized / (pos["entry_price"] * pos["qty"])) * 100
            held = (datetime.utcnow() - pos["entry_time"]).total_seconds()
            positions.append({
                "ticker": ticker,
                "direction": "LONG",
                "qty": pos["qty"],
                "entry_price": round(pos["entry_price"], 2),
                "current_price": round(pos.get("current_price", pos["entry_price"]), 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pct": round(unrealized_pct, 2),
                "held_seconds": round(held),
            })
        self.state.update_positions(positions)

    def _update_dashboard_account(self) -> None:
        self.state.update_account(
            current_equity=round(self.account.equity, 2),
            total_pnl=round(self.account.equity - self.account.starting_capital, 2),
            total_pnl_pct=round(
                ((self.account.equity - self.account.starting_capital) / self.account.starting_capital) * 100, 2
            ),
            available_cash=round(self.account.available_cash, 2),
            unsettled_funds=round(self.account.unsettled_funds, 2),
            day_trades_remaining=self.account.day_trades_remaining,
        )


# ---------------------------------------------------------------------------
# DemoOrchestrator - ties it all together
# ---------------------------------------------------------------------------

class DemoOrchestrator:
    """Main demo loop: scan → analyze → alert → execute."""

    def __init__(self, state: DashboardState) -> None:
        self.state = state
        self.account = SimulatedAccount()
        self.scanner = SignalSimulator()
        self.executor = DemoExecutor(self.account, state)
        self._running = False

        # Insider / congressional signal source
        from demo.insider_signals import InsiderSignalSource, boost_signal_with_insider
        self.insider_scanner = InsiderSignalSource()
        self._boost_signal = boost_signal_with_insider

    async def run(self) -> None:
        self._running = True
        self.state.add_log("Simulation started", "INFO")
        self.state.add_log(f"Starting capital: ${STARTING_CAPITAL:,.2f}", "INFO")
        self.state.add_log(f"Watchlist: {', '.join(WATCHLIST)}", "INFO")
        self.state.add_log("Signal sources: Technical analysis + Insider trading (Form 4) + Congressional (STOCK Act)", "INFO")
        self.state.add_log("Scanning for real technical setups + insider/congressional activity...", "INFO")

        # Record initial equity
        self.account.record_equity()
        self.state.add_equity_point(
            datetime.utcnow().strftime("%H:%M:%S"),
            self.account.equity,
        )

        cycle = 0
        while self._running:
            try:
                cycle += 1

                # Update market status
                market_open = _is_market_open()
                self.state.update_account(
                    market_open=market_open,
                    market_status="OPEN" if market_open else "CLOSED",
                    next_event=_next_market_event(),
                )

                self.state.add_log(f"--- Scan cycle #{cycle} ---", "INFO")

                # Scan for technical signals (uses real market data)
                signals = await self.scanner.scan_all()
                self.state.add_log(f"Scanned {len(WATCHLIST)} tickers, found {len(signals)} technical setups", "INFO")

                # Scan for insider / congressional signals
                insider_signals = self.insider_scanner.scan_all()
                if insider_signals:
                    self.state.add_log(f"Found {len(insider_signals)} insider/congressional signal(s)", "INFO")
                    for isig in insider_signals:
                        src = "INSIDER" if isig.get("source") == "SEC_Form4" else "CONGRESS"
                        self.state.add_signal({
                            "tickers": isig["ticker"],
                            "direction": isig["direction"],
                            "catalyst": isig["headline"],
                            "catalyst_type": isig["catalyst_type"],
                            "magnitude": isig["magnitude"],
                            "confidence": isig["confidence"],
                            "flag_level": isig["flag_level"],
                            "rsi": isig.get("rsi", 50),
                            "volume_ratio": isig.get("volume_ratio", 1.0),
                            "price": isig["price"],
                        })
                        self.state.add_log(
                            f"{src} SIGNAL: {isig['ticker']} {isig['direction']} | "
                            f"{isig['flag_level']} | conf={isig['confidence']} | "
                            f"{isig['headline'][:80]}",
                            "RED" if isig["flag_level"] == "RED" else "YELLOW",
                        )

                        # Check if insider signal confirms any technical signal
                        for sig in signals:
                            if sig["ticker"] == isig["ticker"] and sig["direction"] == isig["direction"]:
                                boosted = self._boost_signal(sig, isig)
                                self.state.add_log(
                                    f"  CONFIRMED: {src} + Technical on {sig['ticker']} — "
                                    f"conf {sig['confidence']} -> {boosted['confidence']}",
                                    "RED",
                                )
                                # Replace with boosted version
                                signals[signals.index(sig)] = boosted
                                break

                        # Standalone insider RED signals also auto-execute
                        if isig["flag_level"] == "RED":
                            self.state.add_log(f"Auto-executing {src} RED signal for {isig['ticker']}", "EXEC")
                            await self.executor.execute_entry(isig)

                for signal in signals:
                    # Add to dashboard signal feed
                    self.state.add_signal({
                        "tickers": signal["ticker"],
                        "direction": signal["direction"],
                        "catalyst": signal["headline"],
                        "catalyst_type": signal["catalyst_type"],
                        "magnitude": signal["magnitude"],
                        "confidence": signal["confidence"],
                        "flag_level": signal["flag_level"],
                        "rsi": signal.get("rsi", 50),
                        "volume_ratio": signal.get("volume_ratio", 1.0),
                        "price": signal["price"],
                    })

                    if signal["flag_level"] == "RED":
                        self.state.add_log(
                            f"RED FLAG: {signal['ticker']} {signal['direction']} - "
                            f"{signal['headline'][:80]}",
                            "RED",
                        )
                        self.state.add_log(
                            f"  RSI={signal.get('rsi', 'N/A')} vol={signal.get('volume_ratio', 'N/A')}x "
                            f"mag={signal['magnitude']} conf={signal['confidence']} "
                            f"price=${signal['price']:.2f} support=${signal.get('support', 0):.2f} "
                            f"resist=${signal.get('resistance', 0):.2f}",
                            "INFO",
                        )

                        self.state.add_log(f"Auto-executing {signal['ticker']} (RED flag)", "INFO")
                        await self.executor.execute_entry(signal)

                    elif signal["flag_level"] == "YELLOW":
                        self.state.add_log(
                            f"YELLOW FLAG: {signal['ticker']} {signal['direction']} - "
                            f"watching (mag={signal['magnitude']}, conf={signal['confidence']}, "
                            f"RSI={signal.get('rsi', 'N/A')}, vol={signal.get('volume_ratio', 'N/A')}x)",
                            "YELLOW",
                        )

                # Update account summary
                self.executor._update_dashboard_account()

                # Record equity periodically
                self.account.record_equity()
                self.state.add_equity_point(
                    datetime.utcnow().strftime("%H:%M:%S"),
                    self.account.equity,
                )

                # Update positions with current prices
                self.executor._update_dashboard_positions()

            except Exception as e:
                self.state.add_log(f"Scan error: {e}", "ERROR")

            await asyncio.sleep(SIGNAL_SCAN_INTERVAL_SEC)

    def stop(self) -> None:
        self._running = False
