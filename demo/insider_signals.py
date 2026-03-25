"""Insider trading & congressional disclosure signal source.

Monitors SEC Form 4 filings (insider buys/sells) and STOCK Act
disclosures (congressional trading) to generate high-confidence
trading signals. When insiders or politicians are buying/selling,
it often precedes significant price moves.

In demo mode, generates synthetic but realistic insider/congressional
signals. In production mode, can be wired to:
  - SEC EDGAR XBRL API (Form 4 filings, free, no key)
  - Quiver Quantitative API (congressional trades)
  - Capitol Trades / OpenSecrets data
  - Insider Monkey / WhaleWisdom aggregators
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from demo.config import WATCHLIST
from demo.demo_signals import (
    CATALYST_TEMPLATES,
    COMMITTEES,
    CONGRESSIONAL_CONFIDENCE_BOOST,
    INSIDER_CONFIDENCE_BOOST,
    INSIDER_TITLES,
    REPRESENTATIVES,
    SENATORS,
    TICKER_SECTOR,
)


# ---------------------------------------------------------------------------
# Synthetic insider activity generator (demo mode)
# ---------------------------------------------------------------------------

class InsiderSignalSource:
    """Generates insider / congressional trading signals.

    Each scan cycle has a chance to produce insider or congressional
    signals. These carry higher base confidence than pure technical
    signals because "smart money" is acting on information.
    """

    def __init__(self) -> None:
        # Track recent filings to avoid spamming same ticker
        self._recent_insider: dict[str, datetime] = {}
        self._recent_congressional: dict[str, datetime] = {}
        # Cooldown: don't repeat same ticker within N minutes (sim time)
        self.cooldown_minutes = 30
        # Running stats for logging
        self.total_insider_signals = 0
        self.total_congressional_signals = 0

    def scan_insider(
        self,
        sim_time: datetime | None = None,
        tickers: list[str] | None = None,
    ) -> list[dict]:
        """Check for insider trading activity across watchlist.

        Returns list of insider signal dicts (may be empty).
        In demo mode, ~15% chance per scan of generating an insider signal.
        """
        now = sim_time or datetime.utcnow()
        watch = tickers or WATCHLIST
        signals = []

        # ~15% chance of an insider signal per scan cycle
        if random.random() > 0.15:
            return signals

        # Pick a random ticker (weighted toward tech/defense — more insider activity)
        ticker = random.choice(watch)

        # Cooldown check
        last_seen = self._recent_insider.get(ticker)
        if last_seen and (now - last_seen).total_seconds() < self.cooldown_minutes * 60:
            return signals

        # Generate insider filing
        is_buy = random.random() < 0.70  # 70% buys (buys are more signal-worthy)
        signal = self._build_insider_signal(ticker, is_buy, now)
        if signal:
            signals.append(signal)
            self._recent_insider[ticker] = now
            self.total_insider_signals += 1

        return signals

    def scan_congressional(
        self,
        sim_time: datetime | None = None,
        tickers: list[str] | None = None,
    ) -> list[dict]:
        """Check for congressional trading disclosures.

        Returns list of congressional signal dicts (may be empty).
        In demo mode, ~8% chance per scan of generating a congressional signal.
        Congressional signals carry extra weight — these people have oversight.
        """
        now = sim_time or datetime.utcnow()
        watch = tickers or WATCHLIST
        signals = []

        # ~8% chance — congressional trades are rarer but higher impact
        if random.random() > 0.08:
            return signals

        ticker = random.choice(watch)

        # Cooldown check
        last_seen = self._recent_congressional.get(ticker)
        if last_seen and (now - last_seen).total_seconds() < self.cooldown_minutes * 60:
            return signals

        is_buy = random.random() < 0.65  # 65% buys
        signal = self._build_congressional_signal(ticker, is_buy, now)
        if signal:
            signals.append(signal)
            self._recent_congressional[ticker] = now
            self.total_congressional_signals += 1

        return signals

    def scan_all(
        self,
        sim_time: datetime | None = None,
        tickers: list[str] | None = None,
    ) -> list[dict]:
        """Run both insider and congressional scans. Returns combined signals."""
        signals = []
        signals.extend(self.scan_insider(sim_time, tickers))
        signals.extend(self.scan_congressional(sim_time, tickers))
        return signals

    # -------------------------------------------------------------------
    # Signal builders
    # -------------------------------------------------------------------

    def _build_insider_signal(
        self, ticker: str, is_buy: bool, now: datetime
    ) -> dict | None:
        """Build a synthetic SEC Form 4 insider trading signal."""
        sector = TICKER_SECTOR.get(ticker, "technical")
        base_prices = {
            "NVDA": 135.0, "TSLA": 245.0, "AAPL": 192.0, "AMD": 165.0,
            "META": 510.0, "SPY": 525.0, "BA": 188.0, "MSFT": 420.0,
            "GOOGL": 175.0, "AMZN": 195.0, "LMT": 460.0, "RTX": 120.0,
            "GD": 295.0, "NOC": 470.0,
        }
        price = base_prices.get(ticker, 150.0) * random.uniform(0.97, 1.03)

        # Insider details
        title = random.choice(INSIDER_TITLES)
        shares = random.choice([1000, 2500, 5000, 10000, 15000, 25000, 50000])
        value = f"{shares * price:,.0f}"
        count = random.randint(1, 5)  # number of insiders

        # Filing recency (how many days ago)
        filing_days_ago = random.randint(0, 3)
        filing_date = (now - timedelta(days=filing_days_ago)).strftime("%Y-%m-%d")

        # Pick template
        cat_key = "insider_buy" if is_buy else "insider_sell"
        templates = CATALYST_TEMPLATES.get(cat_key, [])
        if not templates:
            return None

        headline = random.choice(templates).format(
            ticker=ticker, shares=f"{shares:,}", price=price,
            value=value, count=count,
        )

        # Confidence: insider buys are high-signal, cluster buys even more
        if is_buy:
            base_conf = random.uniform(0.65, 0.85)
            if count >= 3:
                base_conf += 0.10  # cluster buying boost
            magnitude = min(5, 3 + (count // 2))
        else:
            base_conf = random.uniform(0.50, 0.70)
            magnitude = min(4, 2 + (count // 2))

        confidence = min(0.95, base_conf + INSIDER_CONFIDENCE_BOOST)
        direction = "bullish" if is_buy else "bearish"
        flag = "RED" if magnitude >= 3 and confidence >= 0.6 else "YELLOW"

        return {
            "ticker": ticker,
            "direction": direction,
            "catalyst_type": cat_key,
            "headline": headline,
            "magnitude": magnitude,
            "confidence": round(confidence, 2),
            "price": round(price, 2),
            "support": round(price * 0.965, 2),
            "resistance": round(price * 1.06, 2),
            "rsi": round(random.uniform(30, 65), 1),
            "volume_ratio": round(random.uniform(1.2, 3.0), 2),
            "flag_level": flag,
            "timestamp": now.strftime("%H:%M:%S"),
            "source": "SEC_Form4",
            # Extra fields for logging/optimization
            "insider_title": title,
            "insider_shares": shares,
            "insider_value": value,
            "insider_count": count,
            "filing_date": filing_date,
            "filing_days_ago": filing_days_ago,
        }

    def _build_congressional_signal(
        self, ticker: str, is_buy: bool, now: datetime
    ) -> dict | None:
        """Build a synthetic STOCK Act congressional trading signal."""
        base_prices = {
            "NVDA": 135.0, "TSLA": 245.0, "AAPL": 192.0, "AMD": 165.0,
            "META": 510.0, "SPY": 525.0, "BA": 188.0, "MSFT": 420.0,
            "GOOGL": 175.0, "AMZN": 195.0, "LMT": 460.0, "RTX": 120.0,
            "GD": 295.0, "NOC": 470.0,
        }
        price = base_prices.get(ticker, 150.0) * random.uniform(0.97, 1.03)

        # Pick a senator or representative
        is_senator = random.random() < 0.45
        if is_senator:
            person = random.choice(SENATORS)
            person_type = "senator"
        else:
            person = random.choice(REPRESENTATIVES)
            person_type = "representative"

        # Find relevant committee
        relevant_committees = [
            c for c, tickers in COMMITTEES.items() if ticker in tickers
        ]
        committee = random.choice(relevant_committees) if relevant_committees else "Appropriations"

        shares = random.choice([500, 1000, 2500, 5000, 10000, 25000])
        value = f"{shares * price:,.0f}"
        count = random.randint(1, 4)

        # Pick template
        cat_key = "congressional_buy" if is_buy else "congressional_sell"
        templates = CATALYST_TEMPLATES.get(cat_key, [])
        if not templates:
            return None

        headline = random.choice(templates).format(
            ticker=ticker, senator=person, representative=person,
            shares=f"{shares:,}", price=price, value=value,
            count=count, committee=committee,
        )

        # Congressional signals are high-confidence — they have oversight/info
        if is_buy:
            base_conf = random.uniform(0.70, 0.90)
            magnitude = min(5, 3 + (count // 2))
        else:
            base_conf = random.uniform(0.55, 0.75)
            magnitude = min(4, 2 + (count // 2))

        # Boost confidence if committee has oversight of this sector
        if relevant_committees:
            base_conf += 0.05  # committee member trading in their oversight area

        confidence = min(0.95, base_conf + CONGRESSIONAL_CONFIDENCE_BOOST)
        direction = "bullish" if is_buy else "bearish"
        flag = "RED" if magnitude >= 3 and confidence >= 0.6 else "YELLOW"

        return {
            "ticker": ticker,
            "direction": direction,
            "catalyst_type": cat_key,
            "headline": headline,
            "magnitude": magnitude,
            "confidence": round(confidence, 2),
            "price": round(price, 2),
            "support": round(price * 0.96, 2),
            "resistance": round(price * 1.07, 2),
            "rsi": round(random.uniform(30, 65), 1),
            "volume_ratio": round(random.uniform(1.0, 2.5), 2),
            "flag_level": flag,
            "timestamp": now.strftime("%H:%M:%S"),
            "source": "STOCK_Act",
            # Extra fields for logging/optimization
            "congress_member": person,
            "congress_type": person_type,
            "committee": committee,
            "has_oversight": bool(relevant_committees),
            "congress_shares": shares,
            "congress_value": value,
            "congress_count": count,
        }


# ---------------------------------------------------------------------------
# Helper: boost existing technical signal with insider confirmation
# ---------------------------------------------------------------------------

def boost_signal_with_insider(
    technical_signal: dict, insider_signal: dict
) -> dict:
    """When a technical signal aligns with insider activity on same ticker,
    boost the confidence and create a combined signal.

    This is the 'smart money confirmation' — when technicals AND insiders
    agree, the probability of a profitable trade is significantly higher.
    """
    combined = dict(technical_signal)

    # Boost confidence
    insider_boost = INSIDER_CONFIDENCE_BOOST
    if insider_signal.get("source") == "STOCK_Act":
        insider_boost = CONGRESSIONAL_CONFIDENCE_BOOST

    combined["confidence"] = min(0.95, technical_signal["confidence"] + insider_boost)
    combined["magnitude"] = min(5, technical_signal["magnitude"] + 1)

    # Upgrade flag level if boosted enough
    if combined["magnitude"] >= 3 and combined["confidence"] >= 0.6:
        combined["flag_level"] = "RED"

    # Combine headlines
    combined["headline"] = (
        f"{technical_signal['headline']} + {insider_signal['headline'][:60]}"
    )
    combined["catalyst_type"] = f"confirmed_{insider_signal['catalyst_type']}"

    # Preserve insider data for logging
    combined["insider_confirmation"] = True
    combined["insider_source"] = insider_signal.get("source", "unknown")
    combined["insider_detail"] = insider_signal.get("headline", "")

    return combined
