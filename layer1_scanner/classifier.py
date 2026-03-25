"""LLM-based classification of news articles into trading signals."""

import json
from datetime import datetime

from openai import AsyncOpenAI

from config.settings import get_settings
from layer1_scanner.models import ClassifiedSignal, FlagLevel, RawArticle
from shared.exceptions import ClassificationError
from shared.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a financial news analyst. Classify the given headline and summary for trading relevance.

Return a JSON object with exactly these fields:
{
  "tickers": ["AAPL", "MSFT"],       // affected stock tickers (empty list if none)
  "direction": "bullish",             // "bullish" or "bearish"
  "catalyst_type": "earnings",        // one of: geopolitical, earnings, regulatory, supply_chain, contract_win
  "magnitude": 3,                     // impact magnitude 1-5 (1=noise, 5=market-moving)
  "confidence": 0.75,                 // your confidence in this classification 0.0-1.0
  "time_horizon": "2 days"            // expected duration of price impact
}

Rules:
- Only include real, publicly traded US stock tickers
- magnitude 5 = major events (war, Fed rate decision, massive earnings miss)
- magnitude 1 = routine news with no trading signal
- If the headline is not financially relevant, set magnitude to 1 and tickers to []
- Be conservative with confidence scores
"""


class SignalClassifier:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.classifier.model
        self._red_magnitude = settings.classifier.red_flag_magnitude
        self._red_confidence = settings.classifier.red_flag_confidence
        self._yellow_magnitude = settings.classifier.yellow_flag_magnitude

    async def classify(self, article: RawArticle) -> ClassifiedSignal | None:
        """Classify a single article. Returns None if not tradeable."""
        try:
            user_content = f"Headline: {article.headline}\nSummary: {article.summary[:500]}"

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            if not data.get("tickers"):
                return None

            signal = ClassifiedSignal(
                tickers=data["tickers"],
                direction=data.get("direction", "bullish"),
                catalyst_type=data.get("catalyst_type", "unknown"),
                magnitude=data.get("magnitude", 1),
                confidence=data.get("confidence", 0.5),
                time_horizon=data.get("time_horizon", ""),
                headline=article.headline,
                source=article.source,
                timestamp=article.published_at or datetime.utcnow(),
            )

            signal.flag_level = self._compute_flag(signal)

            log.info(
                "signal_classified",
                tickers=signal.tickers,
                direction=signal.direction,
                magnitude=signal.magnitude,
                confidence=signal.confidence,
                flag=signal.flag_level.value,
            )

            return signal

        except Exception as e:
            log.error("classification_error", headline=article.headline[:80], error=str(e))
            raise ClassificationError(str(e)) from e

    def _compute_flag(self, signal: ClassifiedSignal) -> FlagLevel:
        if signal.magnitude >= self._red_magnitude and signal.confidence >= self._red_confidence:
            return FlagLevel.RED
        if signal.magnitude >= self._yellow_magnitude:
            return FlagLevel.YELLOW
        return FlagLevel.NONE

    async def classify_batch(self, articles: list[RawArticle]) -> list[ClassifiedSignal]:
        """Classify a batch of articles, returning only tradeable signals."""
        signals = []
        for article in articles:
            try:
                signal = await self.classify(article)
                if signal:
                    signals.append(signal)
            except ClassificationError:
                continue
        return signals
