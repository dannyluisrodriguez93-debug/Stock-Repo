"""Data models for Layer 3 - Alert + Approval."""

from pydantic import BaseModel

from layer2_deepdive.models import TradeSetup


class AlertPayload(BaseModel):
    """Formatted alert sent to Danny."""
    ticker: str
    direction: str
    entry_price: float
    target_price: float
    stop_loss: float
    catalyst_summary: str
    time_horizon: str
    confidence: float
    technical_summary: str
    volume_summary: str

    @classmethod
    def from_trade_setup(cls, setup: TradeSetup) -> "AlertPayload":
        risk = abs(setup.entry_price - setup.stop_loss)
        reward = abs(setup.target_price - setup.entry_price)
        rr_ratio = reward / risk if risk > 0 else 0

        tech = setup.technical
        tech_summary = (
            f"RSI: {tech.rsi} | Trend: {tech.trend} | "
            f"Support: ${tech.support} | Resistance: ${tech.resistance} | "
            f"VWAP: ${tech.vwap}"
        )
        vol = setup.volume
        vol_summary = (
            f"Volume spike: {vol.spike_ratio}x avg | "
            f"Current: {vol.current_volume:,.0f} | 20d avg: {vol.avg_volume_20d:,.0f}"
        )

        return cls(
            ticker=setup.ticker,
            direction=setup.direction,
            entry_price=setup.entry_price,
            target_price=setup.target_price,
            stop_loss=setup.stop_loss,
            catalyst_summary=setup.catalyst_summary,
            time_horizon=setup.time_horizon,
            confidence=setup.confidence,
            technical_summary=tech_summary,
            volume_summary=vol_summary,
        )

    def format_message(self) -> str:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.target_price - self.entry_price)
        rr = reward / risk if risk > 0 else 0
        direction_emoji = "LONG" if self.direction == "bullish" else "SHORT"

        return (
            f"--- TRADE ALERT ---\n"
            f"Ticker: {self.ticker} ({direction_emoji})\n"
            f"Confidence: {self.confidence:.0%}\n\n"
            f"Entry:     ${self.entry_price:.2f}\n"
            f"Target:    ${self.target_price:.2f}\n"
            f"Stop-Loss: ${self.stop_loss:.2f}\n"
            f"R:R Ratio: {rr:.1f}:1\n\n"
            f"Catalyst: {self.catalyst_summary}\n"
            f"Window: {self.time_horizon}\n\n"
            f"Technical: {self.technical_summary}\n"
            f"Volume: {self.volume_summary}\n\n"
            f"Reply GO to execute or NO to skip."
        )


class ApprovalResponse(BaseModel):
    """Danny's response to an alert."""
    approved: bool
    setup: TradeSetup
