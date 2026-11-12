from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_headlines(headlines):
    """Average VADER sentiment across a list of headlines, or None if there are none to score."""
    headlines = [headline for headline in (headlines or []) if headline]
    if not headlines:
        return None
    scores = [_analyzer.polarity_scores(headline)["compound"] for headline in headlines]
    compound = sum(scores) / len(scores)
    label = "Positive" if compound > 0.15 else "Negative" if compound < -0.15 else "Neutral"
    return {"Compound": compound, "Label": label, "Count": len(headlines)}
