import os

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# redis_client: redis.Redis = redis.Redis(...)

redis_client: redis.Redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD"),
    username=os.getenv("REDIS_USERNAME"),
    db=int(os.getenv("REDIS_DB", 0)),
)
