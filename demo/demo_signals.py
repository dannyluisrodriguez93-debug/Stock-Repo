"""Template catalyst headlines used by SignalSimulator.

When the simulator detects a real technical setup on a ticker it picks a
random headline template matching the catalyst type.  The templates contain
``{ticker}`` placeholders that get formatted at runtime.
"""

from __future__ import annotations

CATALYST_TEMPLATES: dict[str, list[str]] = {
    # ------------------------------------------------------------------
    # Geopolitical
    # ------------------------------------------------------------------
    "geopolitical": [
        "Rising geopolitical tensions boost defense spending outlook; {ticker} positioned to benefit",
        "State Dept confirms new arms package — analysts flag {ticker} as primary contractor",
        "NATO allies agree to accelerate procurement; {ticker} among top suppliers",
        "Escalation in Eastern Europe drives flight-to-safety bid across defense names including {ticker}",
        "Pentagon briefs Congress on readiness gaps; supplemental funding likely benefits {ticker}",
        "Asia-Pacific defense pact expansion signals multi-year tailwind for {ticker}",
        "Sanctions announcement triggers supply-chain reshuffle; {ticker} seen as domestic alternative",
        "UN emergency session raises global threat level; defense ETF & {ticker} catch bid",
    ],

    # ------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------
    "earnings": [
        "{ticker} beats EPS estimates by 12 %; guidance raised for FY25",
        "{ticker} reports record quarterly revenue, margins expand 200 bps",
        "Analyst upgrades flood in after {ticker} posts surprise earnings beat",
        "{ticker} Q4 earnings crush expectations; backlog grows to all-time high",
        "Strong cloud / AI demand drives {ticker} earnings above consensus",
        "{ticker} announces $2B accelerated buyback alongside earnings beat",
        "{ticker} posts first profitable quarter in two years; short squeeze potential",
        "Revenue growth reaccelerates at {ticker}; Street revises models higher",
        "{ticker} raises full-year outlook on robust enterprise demand",
        "After-hours surge: {ticker} EPS $1.42 vs $1.18 expected",
    ],

    # ------------------------------------------------------------------
    # Regulatory
    # ------------------------------------------------------------------
    "regulatory": [
        "FDA grants breakthrough designation for {ticker}'s lead candidate",
        "FTC clears {ticker} acquisition, removing last regulatory overhang",
        "{ticker} receives favorable DOJ ruling; antitrust concerns eased",
        "New emission standards create compliance moat for {ticker}",
        "EU regulatory approval opens $30B addressable market for {ticker}",
        "FAA recertification of {ticker} platform expected within weeks — sources",
        "Commerce Dept export license granted to {ticker} for key ally sales",
        "Bipartisan bill fast-tracked that directly benefits {ticker}'s core business",
    ],

    # ------------------------------------------------------------------
    # Supply chain
    # ------------------------------------------------------------------
    "supply_chain": [
        "{ticker} secures long-term rare-earth supply agreement, de-risking production",
        "Major competitor plant shutdown shifts orders toward {ticker}",
        "{ticker} qualifies second-source fab, improving chip supply outlook",
        "Port congestion easing expected to unlock pent-up demand for {ticker} products",
        "{ticker} vertically integrates key component, cutting lead times 40 %",
        "Global logistics carrier signs exclusive deal with {ticker}",
        "Supplier diversification strategy pays off for {ticker} amid tariff uncertainty",
    ],

    # ------------------------------------------------------------------
    # Contract wins
    # ------------------------------------------------------------------
    "contract_win": [
        "{ticker} awarded $4.7B multi-year DoD contract for next-gen systems",
        "Pentagon selects {ticker} as sole-source provider for classified program",
        "{ticker} wins $1.2B international order from Middle East ally",
        "NASA taps {ticker} for Artemis support contract worth up to $900M",
        "{ticker} secures major cloud infrastructure deal with Fortune-50 client",
        "{ticker} lands follow-on production contract, extending backlog to 2029",
        "State government selects {ticker} for $500M IT modernization program",
        "Army Future Command picks {ticker} for next-phase prototype development",
        "{ticker} added to IDIQ vehicle with $6B ceiling across 5 years",
        "{ticker} and ally win joint venture contract for European missile defense",
    ],

    # ------------------------------------------------------------------
    # Macro / sector rotation
    # ------------------------------------------------------------------
    "macro": [
        "Fed signals rate pause; risk-on rotation lifts {ticker} and growth names",
        "CPI comes in below expectations — bond yields drop, {ticker} rallies",
        "Dollar weakness boosts multinational earnings outlook for {ticker}",
        "ISM manufacturing index beats; cyclical names like {ticker} see inflows",
        "Jobs report surprises to the upside; consumer-facing {ticker} surges",
        "Treasury yield curve un-inverts; banks and {ticker} lead market higher",
    ],

    # ------------------------------------------------------------------
    # Technical / momentum (catch-all when no fundamental catalyst maps)
    # ------------------------------------------------------------------
    "technical": [
        "{ticker} breaks out above 50-day MA on heavy volume",
        "Unusual options activity detected in {ticker} — large call sweeps",
        "{ticker} clears key resistance with 3x average volume",
        "Institutional dark-pool prints signal accumulation in {ticker}",
        "{ticker} golden cross confirmed on daily chart; momentum traders pile in",
        "Short interest in {ticker} drops sharply — potential short-covering rally",
        "{ticker} reclaims VWAP with strong bid-side tape; buyers in control",
    ],
}


# ---------------------------------------------------------------------------
# Mapping from ticker sector to preferred catalyst type
# ---------------------------------------------------------------------------
TICKER_SECTOR: dict[str, str] = {
    "BA": "contract_win",
    "LMT": "contract_win",
    "RTX": "contract_win",
    "GD": "contract_win",
    "NOC": "geopolitical",
    "AAPL": "earnings",
    "MSFT": "earnings",
    "GOOGL": "earnings",
    "META": "earnings",
    "AMZN": "earnings",
    "NVDA": "earnings",
    "AMD": "supply_chain",
    "TSLA": "regulatory",
    "SPY": "macro",
}
