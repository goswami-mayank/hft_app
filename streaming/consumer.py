import json

import pandas as pd
from confluent_kafka import Consumer, KafkaError

from config import DATA_DIR, KAFKA_BOOTSTRAP_SERVERS, MARKET_TOPIC
from sources.prices import write_bars


def main():
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "market-storage-v1",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([MARKET_TOPIC])
    print(f"Storage consumer connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}", flush=True)

    while True:
        record = consumer.poll(timeout=1.0)
        if record is None:
            continue
        if record.error():
            if record.error().code() in (
                KafkaError._PARTITION_EOF,
                KafkaError.UNKNOWN_TOPIC_OR_PART,
            ):
                continue
            raise RuntimeError(record.error())
        payload = json.loads(record.value().decode("utf-8"))
        bars = pd.DataFrame(payload["bars"])
        if not bars.empty:
            bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
            bars = bars.set_index("timestamp")
            bars.columns = [column.title() for column in bars.columns]
            write_bars(payload["ticker"], bars, DATA_DIR)
        consumer.commit(message=record, asynchronous=False)
        print(f"Stored {len(bars)} bars for {payload['ticker']}", flush=True)


if __name__ == "__main__":
    main()
