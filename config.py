import os

DATA_DIR = os.getenv("DATA_DIR", "data")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SUBSCRIPTION_TOPIC = "ticker-subscriptions"
MARKET_TOPIC = "market-bars"
POLL_SECONDS = 60

# Default queries for the macro/policy/geopolitics news tab, independent of any single company.
MACRO_TOPICS = [
    "Indian stock market",
    "RBI monetary policy",
    "US Federal Reserve policy",
    "global geopolitics markets",
]
