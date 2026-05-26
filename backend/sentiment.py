from transformers import pipeline
import asyncio
from functools import lru_cache

# Loads once, reused across all requests
@lru_cache(maxsize=1)
def get_sentiment_pipeline():
    return pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        device=-1  # CPU; set to 0 for GPU
    )

def analyze_sentiment(text: str) -> dict:
    """
    Returns: {"label": "POSITIVE"|"NEGATIVE", "score": float, "normalized": float (-1 to 1)}
    """
    pipe = get_sentiment_pipeline()
    result = pipe(text[:512])[0]  # Truncate to model max
    label = result["label"]
    raw_score = result["score"]
    # Normalize to -1 (very negative) to +1 (very positive)
    normalized = raw_score if label == "POSITIVE" else -raw_score
    return {
        "label": label,
        "score": raw_score,
        "normalized": normalized,
        "is_negative": normalized < -0.3   # Threshold for escalation trigger
    }

def should_escalate(sentiment_history: list[float], threshold: float = -0.4) -> bool:
    """
    Returns True if the last 3 messages average is below the negative threshold.
    Used to trigger human handoff automatically.
    """
    if len(sentiment_history) < 2:
        return False
    recent = sentiment_history[-3:]
    average = sum(recent) / len(recent)
    return average < threshold