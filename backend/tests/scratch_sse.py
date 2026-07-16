import asyncio
import json
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from fakeredis.aioredis import FakeRedis

# Import other packages first
import app.core.redis

# Import the FastAPI instance last and rename it to avoid namespace collision
from app.main import app as fastapi_app

async def main():
    print("Initializing FakeRedis...")
    redis_client = FakeRedis(decode_responses=True)

    async def _get_redis_client():
        return redis_client

    app.core.redis.get_redis_client = _get_redis_client

    print("Starting LifespanManager...")
    async with LifespanManager(fastapi_app) as manager:
        print("LifespanManager started.")
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            
            async def consume():
                try:
                    print("Connecting to SSE stream...")
                    async with client.stream("GET", "/api/v1/alerts/stream") as response:
                        print("Response status:", response.status_code)
                        async for line in response.aiter_lines():
                            print("Received line:", line)
                            if line.startswith("data:"):
                                print("Found data line!")
                                break
                except Exception as e:
                    print("Consumer exception:", e)

            consumer_task = asyncio.create_task(consume())
            await asyncio.sleep(0.5)
            
            print("Publishing alert...")
            await redis_client.publish("alerts:new", json.dumps({"id": "123", "rule_name": "test"}))
            print("Alert published.")
            
            await asyncio.sleep(0.5)
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                print("Consumer task cancelled.")

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
