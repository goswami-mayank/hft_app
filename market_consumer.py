# Thin entrypoint for docker-compose; real logic lives in streaming.consumer.
from streaming.consumer import main

if __name__ == "__main__":
    main()