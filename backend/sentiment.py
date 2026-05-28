from functools import lru_cache
import os
import re

NEGATIVE_WORDS = {
    "angry", "awful", "bad", "broken", "cancel", "complaint", "failed",
    "frustrated", "hate", "horrible", "late", "lost", "mad", "refund",
    "terrible", "unacceptable", "upset", "worst",
}
POSITIVE_WORDS = {"thanks", "thank", "great", "good", "helpful", "resolved", "perfect"}


@lru_cache(maxsize=1)
def get_sentiment_pipeline():
    if os.getenv("ENABLE_TRANSFORMERS_SENTIMENT", "false").lower() != "true":
        return None
    try:
        from transformers import pipeline
        return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)
    except Exception:
        return None


def _lexical_sentiment(text: str) -> dict:
    words = re.findall(r"[a-z']+", text.lower())
    neg = sum(1 for word in words if word in NEGATIVE_WORDS)
    pos = sum(1 for word in words if word in POSITIVE_WORDS)
    if neg == pos == 0:
        normalized = 0.0
    else:
        normalized = max(-1.0, min(1.0, (pos - neg) / max(pos + neg, 1)))
    label = "NEGATIVE" if normalized < -0.2 else "POSITIVE" if normalized > 0.2 else "NEUTRAL"
    return {
        "label": label,
        "score": abs(normalized),
        "normalized": normalized,
        "is_negative": normalized < -0.3,
    }


def analyze_sentiment(text: str) -> dict:
    pipe = get_sentiment_pipeline()
    if pipe:
        try:
            result = pipe(text[:512])[0]
            label = result["label"]
            raw_score = float(result["score"])
            normalized = raw_score if label == "POSITIVE" else -raw_score
            return {
                "label": label,
                "score": raw_score,
                "normalized": normalized,
                "is_negative": normalized < -0.3,
            }
        except Exception:
            pass
    return _lexical_sentiment(text)


def should_escalate(sentiment_history: list[float], threshold: float = -0.4) -> bool:
    if len(sentiment_history) < 2:
        return False
    recent = sentiment_history[-3:]
    return (sum(recent) / len(recent)) < threshold


def contains_handoff_request(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in [
        "human", "real person", "agent", "representative", "manager", "escalate",
        "talk to someone", "speak to someone",
    ])
