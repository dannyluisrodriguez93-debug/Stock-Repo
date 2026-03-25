"""Demo runner - ties simulation engine + dashboard together.

Usage:
    python -m demo.run          # Real market data simulation + dashboard
    python -m demo.run --demo   # Synthetic data demo (no yfinance needed)

Starts the simulation engine and live dashboard on http://localhost:5050
"""

import asyncio
import threading
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_dashboard(state):
    """Run Flask dashboard in a separate thread."""
    import demo.dashboard as dash
    dash.state = state
    dash.app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False, threaded=True)


def run_demo_dashboard(state):
    """Run dashboard with synthetic data (no external APIs needed)."""
    import demo.dashboard as dash
    dash.state = state
    dash.run(host="0.0.0.0", port=5050, debug=False, demo_mode=True)


async def run_simulation(state):
    """Run the simulation engine with real market data."""
    from demo.simulator import DemoOrchestrator
    orchestrator = DemoOrchestrator(state)
    await orchestrator.run()


def main():
    from demo.dashboard_state import DashboardState
    from demo.config import (
        STARTING_CAPITAL, BROKER_NAME, COMMISSION_PER_TRADE,
        SEC_FEE_RATE, FINRA_TAF_RATE, FINRA_CAT_FEE,
    )

    demo_only = "--demo" in sys.argv

    print("=" * 62)
    print("  TRADING SIGNAL SYSTEM")
    print("=" * 62)
    print()
    print(f"  Starting capital:  ${STARTING_CAPITAL:,.2f}")
    if demo_only:
        print("  Mode:              Synthetic data (no APIs required)")
    else:
        print("  Mode:              Live data sim (real prices, paper trades)")
    print("  Dashboard:         http://localhost:5050")
    print()
    print(f"  Broker model:      {BROKER_NAME}")
    print(f"  Commission:        ${COMMISSION_PER_TRADE:.2f} per trade")
    print(f"  SEC fee (2026):    ${SEC_FEE_RATE * 1_000_000:.2f} per $1M sold")
    print(f"  FINRA TAF:         ${FINRA_TAF_RATE:.6f} per share sold")
    print(f"  FINRA CAT:         ${FINRA_CAT_FEE:.6f} per transaction")
    print()
    print("  Signal sources:")
    print("    - Technical analysis (RSI, VWAP, SMA, volume)")
    print("    - SEC Form 4 insider trading filings")
    print("    - STOCK Act congressional disclosures")
    print()
    print("  Constraints:")
    print("    - PDT rule (3 day trades / 5 days under $25K)")
    print("    - T+1 settlement")
    print("    - Market hours (9:30 AM - 4:00 PM ET)")
    print("    - Realistic slippage & execution delay")
    print()
    print("=" * 62)
    print()

    # Shared state between simulator and dashboard
    state = DashboardState()

    if demo_only:
        # Run dashboard with its built-in synthetic data pump
        print("[*] Starting dashboard with synthetic data at http://localhost:5050")
        run_demo_dashboard(state)
    else:
        # Start dashboard in background thread
        dash_thread = threading.Thread(target=run_dashboard, args=(state,), daemon=True)
        dash_thread.start()

        # Give Flask a moment to start
        time.sleep(1)
        print("[*] Dashboard running at http://localhost:5050")
        print("[*] Starting simulation engine with real market data...")
        print()

        # Run simulation in asyncio event loop
        try:
            asyncio.run(run_simulation(state))
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
            sys.exit(0)


if __name__ == "__main__":
    main()
