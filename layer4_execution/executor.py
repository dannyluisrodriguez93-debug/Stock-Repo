"""Layer 4 - Trade execution and position lifecycle management."""

from datetime import datetime

from config.settings import get_settings
from layer3_alert.models import ApprovalResponse
from layer4_execution.broker.alpaca_broker import AlpacaBroker
from layer4_execution.broker.base import BrokerAdapter
from layer4_execution.broker.ibkr_broker import IBKRBroker
from layer4_execution.models import OrderSide, Position
from layer4_execution.position_monitor import PositionMonitor
from shared.db import Database
from shared.event_bus import ALERT_TO_EXECUTION, EventBus
from shared.logging import get_logger

log = get_logger(__name__)


def _create_broker(name: str) -> BrokerAdapter:
    brokers = {
        "alpaca": AlpacaBroker,
        "ibkr": IBKRBroker,
    }
    if name not in brokers:
        raise ValueError(f"Unknown broker: {name}")
    return brokers[name]()


class TradeExecutor:
    """Receives approved trades, executes them, and monitors positions."""

    def __init__(self, event_bus: EventBus, db: Database) -> None:
        self._event_bus = event_bus
        self._db = db
        settings = get_settings()
        self._broker = _create_broker(settings.execution.broker)
        self._monitor = PositionMonitor(self._broker, db)
        self._running = False

    def _compute_quantity(self, price: float, account: dict) -> int:
        """Size position at ~2% of portfolio value."""
        portfolio = account.get("portfolio_value", account.get("equity", 10000))
        risk_amount = float(portfolio) * 0.02
        qty = int(risk_amount / price)
        return max(1, qty)

    async def _execute_trade(self, approval: ApprovalResponse) -> None:
        setup = approval.setup
        log.info("executing_trade", ticker=setup.ticker, direction=setup.direction)

        # Get account info for position sizing
        account = await self._broker.get_account_info()
        quantity = self._compute_quantity(setup.entry_price, account)

        # Submit entry order
        side = OrderSide.BUY if setup.direction == "bullish" else OrderSide.SELL
        order = await self._broker.submit_order(
            setup.ticker, side, quantity, limit_price=setup.entry_price
        )

        log.info("entry_order_placed", order_id=order.order_id, qty=quantity, price=setup.entry_price)

        # Insert trade record
        trade_id = await self._db.insert_trade(
            ticker=setup.ticker,
            direction=setup.direction,
            entry_price=setup.entry_price,
            target_price=setup.target_price,
            stop_loss=setup.stop_loss,
            quantity=quantity,
            status="open",
            opened_at=datetime.utcnow().isoformat(),
        )

        # Create position and start monitoring
        position = Position(
            ticker=setup.ticker,
            direction=setup.direction,
            quantity=quantity,
            entry_price=setup.entry_price,
            target_price=setup.target_price,
            stop_loss=setup.stop_loss,
            catalyst_type=setup.catalyst_type,
        )

        result = await self._monitor.monitor(position, trade_id)

        log.info(
            "trade_complete",
            ticker=result.ticker,
            pnl=result.pnl,
            trigger=result.exit_trigger.value,
        )

    async def run(self) -> None:
        """Main execution consumer loop."""
        self._running = True
        log.info("executor_started", broker=self._broker.name)

        while self._running:
            try:
                approval: ApprovalResponse = await self._event_bus.subscribe(ALERT_TO_EXECUTION)

                if approval.approved:
                    await self._execute_trade(approval)
                else:
                    log.info("trade_skipped", ticker=approval.setup.ticker)

            except Exception as e:
                log.error("executor_error", error=str(e))

    def stop(self) -> None:
        self._running = False
