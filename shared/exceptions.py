"""Custom exception hierarchy for the trading signal system."""


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""


class ScannerError(TradingSystemError):
    """Error in Layer 1 news scanning."""


class ClassificationError(ScannerError):
    """Error during LLM classification."""


class DeepDiveError(TradingSystemError):
    """Error in Layer 2 ticker analysis."""


class DataFeedError(DeepDiveError):
    """Error fetching market data."""


class TechnicalAnalysisError(DeepDiveError):
    """Error computing technical indicators."""


class AlertError(TradingSystemError):
    """Error in Layer 3 alerting."""


class ApprovalTimeoutError(AlertError):
    """Approval wait timed out."""


class ExecutionError(TradingSystemError):
    """Error in Layer 4 execution."""


class BrokerError(ExecutionError):
    """Error communicating with broker."""


class OrderError(ExecutionError):
    """Error placing or managing orders."""
