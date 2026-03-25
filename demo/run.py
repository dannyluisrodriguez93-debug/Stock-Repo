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

    demo_only = "--demo" in sys.argv

    print("=" * 60)
    print("  TRADING SIGNAL SYSTEM - DEMO MODE")
    print("=" * 60)
    print()
    print("  Starting capital: $1,000.00")
    if demo_only:
        print("  Mode: Synthetic data demo (no APIs required)")
    else:
        print("  Mode: Simulation (real market data, simulated execution)")
    print("  Dashboard: http://localhost:5050")
    print()
    print("  Constraints enforced:")
    print("    - Pattern Day Trader rule (3 day trades / 5 days)")
    print("    - T+1 settlement")
    print("    - SEC/FINRA fees")
    print("    - Market hours (9:30 AM - 4:00 PM ET)")
    print("    - Realistic slippage & execution delay")
    print()
    print("=" * 60)
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
