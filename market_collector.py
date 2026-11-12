# Thin entrypoint for docker-compose; real logic lives in sources.prices / streaming.collector.
from config import MARKET_TOPIC, SUBSCRIPTION_TOPIC
from sources.prices import download_bars
from streaming.collector import main

__all__ = ["download_bars", "main", "MARKET_TOPIC", "SUBSCRIPTION_TOPIC"]

if __name__ == "__main__":
    main()