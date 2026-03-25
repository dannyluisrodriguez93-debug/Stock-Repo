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

    # ------------------------------------------------------------------
    # Insider trading (SEC Form 4 filings — C-suite, directors, 10%+ owners)
    # ------------------------------------------------------------------
    "insider_buy": [
        "SEC Form 4: {ticker} CEO purchases {shares} shares at ${price:.2f} — largest insider buy in 12 months",
        "{ticker} CFO acquires {shares} shares in open-market purchase worth ${value}",
        "Cluster insider buying at {ticker}: {count} insiders purchased shares this week",
        "{ticker} director buys {shares} shares; 4th consecutive insider purchase this quarter",
        "10% owner increases {ticker} stake by {shares} shares — Form 4 filed today",
        "{ticker} COO exercises options and holds — bullish signal per insider analytics",
        "Multiple {ticker} executives buying ahead of earnings: {count} Form 4 filings in 10 days",
        "SVP of {ticker} makes first open-market purchase in 3 years — {shares} shares at ${price:.2f}",
        "{ticker} board member accumulates {shares} additional shares; total insider buys up 340% YoY",
        "Insider sentiment shift: {ticker} buy/sell ratio hits 8:1 this month per SEC filings",
    ],
    "insider_sell": [
        "SEC Form 4: {ticker} CEO sells {shares} shares at ${price:.2f} — largest insider sale in 6 months",
        "{ticker} CFO disposes {shares} shares via 10b5-1 plan — routine or signal?",
        "Cluster insider selling at {ticker}: {count} insiders sold shares this week",
        "{ticker} CTO sells {shares} shares; 3rd executive to sell this month",
        "{ticker} insider sales spike: {count} Form 4 dispositions totaling ${value}",
        "Multiple {ticker} directors reducing positions ahead of lockup expiry",
    ],

    # ------------------------------------------------------------------
    # Congressional / political trading (STOCK Act disclosures)
    # ------------------------------------------------------------------
    "congressional_buy": [
        "STOCK Act: Rep. Pelosi discloses purchase of {ticker} call options worth ${value}",
        "Sen. {senator} reports new {ticker} position — {shares} shares purchased",
        "Congressional disclosure: {committee} member buys {ticker} ahead of sector hearing",
        "Pelosi trade alert: {ticker} calls acquired — history shows 70%+ hit rate on her picks",
        "Multiple members of {committee} Committee purchased {ticker} within same week",
        "Sen. {senator} adds to {ticker} position; 3rd congressional buy this month",
        "STOCK Act filing: Rep. {representative} buys ${value} of {ticker} — committee has oversight",
        "Congressional buying cluster: {count} members disclosed {ticker} purchases in 14 days",
        "Bipartisan {ticker} buying: both sides of aisle adding positions per STOCK Act filings",
        "Sen. {senator} discloses {ticker} purchase days before favorable committee vote",
    ],
    "congressional_sell": [
        "STOCK Act: Sen. {senator} sells entire {ticker} position — {shares} shares",
        "Congressional exit: {count} members sold {ticker} this week per disclosure filings",
        "Rep. {representative} liquidates {ticker} holdings worth ${value}",
        "Multiple {committee} Committee members reducing {ticker} exposure",
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


# ---------------------------------------------------------------------------
# Insider / congressional signal enrichment data
# ---------------------------------------------------------------------------

# Real senators/reps known for active trading (public info from STOCK Act)
SENATORS: list[str] = [
    "Tuberville", "Hagerty", "Hickenlooper", "Ossoff", "Kelly",
    "Lujan", "Cassidy", "Sullivan", "Hoeven", "Capito",
    "Coons", "King", "Lummis", "Rosen", "Blackburn",
]

REPRESENTATIVES: list[str] = [
    "Pelosi", "Crenshaw", "Gottheimer", "Fallon", "Green",
    "Gimenez", "Mace", "Meuser", "Mooney", "Curtis",
    "Garcia", "Kim", "Connolly", "Malinowski", "Khanna",
]

# Committees with sector oversight (maps to which tickers they'd trade)
COMMITTEES: dict[str, list[str]] = {
    "Armed Services": ["BA", "LMT", "RTX", "GD", "NOC"],
    "Commerce & Technology": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "AMD"],
    "Energy & Commerce": ["TSLA", "AMZN"],
    "Financial Services": ["SPY"],
    "Intelligence": ["NVDA", "MSFT", "GOOGL", "META"],
    "Science & Technology": ["NVDA", "AMD", "MSFT", "GOOGL"],
}

# Insider titles for Form 4 filings
INSIDER_TITLES: list[str] = [
    "CEO", "CFO", "COO", "CTO", "President", "SVP of Engineering",
    "EVP & General Counsel", "Director", "Board Member",
    "10% Owner", "VP of Product", "Chief Strategy Officer",
]

# Confidence boost when insider/congressional signal aligns with technical
INSIDER_CONFIDENCE_BOOST: float = 0.15
CONGRESSIONAL_CONFIDENCE_BOOST: float = 0.20  # historically higher signal value
