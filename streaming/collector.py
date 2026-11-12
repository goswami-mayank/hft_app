import json
import re
import time

from confluent_kafka import Consumer, Producer

from config import KAFKA_BOOTSTRAP_SERVERS, MARKET_TOPIC, POLL_SECONDS, SUBSCRIPTION_TOPIC
from sources.prices import download_bars, serialize_bars


def main():
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "ticker-collector-v1",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([SUBSCRIPTION_TOPIC])
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    tickers = set()
    last_seen = {}
    next_poll = 0.0
    print(f"Collector connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}", flush=True)

    while True:
        record = consumer.poll(timeout=1.0)
        if record is not None and not record.error():
            payload = json.loads(record.value().decode("utf-8"))
            ticker = str(payload.get("ticker", "")).strip().upper()
            if re.fullmatch(r"[A-Z0-9][A-Z0-9._^=-]{0,30}", ticker):
                tickers.add(ticker)

        if not tickers or time.monotonic() < next_poll:
            continue

        for ticker in sorted(tickers):
            try:
                bars = download_bars(ticker)
                if bars.empty:
                    print(f"No yfinance bars returned for {ticker}", flush=True)
                    continue
                cursor = last_seen.get(ticker)
                if cursor is not None:
                    bars = bars[bars.index > cursor]
                if bars.empty:
                    continue
                payload = serialize_bars(ticker, bars)
                producer.produce(
                    MARKET_TOPIC,
                    key=ticker.encode("utf-8"),
                    value=json.dumps(payload).encode("utf-8"),
                )
                if producer.flush(30):
                    raise TimeoutError("Kafka producer did not flush all market bars")
                last_seen[ticker] = bars.index[-1]
                print(f"Published {len(payload['bars'])} bars for {ticker}", flush=True)
            except Exception as error:
                print(f"Could not update {ticker}: {error}", flush=True)

        next_poll = time.monotonic() + POLL_SECONDS


if __name__ == "__main__":
    main()
