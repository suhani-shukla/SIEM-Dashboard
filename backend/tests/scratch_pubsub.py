import asyncio
import json
from fakeredis.aioredis import FakeRedis

async def main():
    redis_client = FakeRedis(decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("alerts:new")
    
    # Check the subscribe message
    msg = await pubsub.get_message(ignore_subscribe_messages=False)
    print("Subscribe message:", msg)
    
    async def publish():
        await asyncio.sleep(0.1)
        print("Publishing message...")
        await redis_client.publish("alerts:new", "hello")
        print("Published.")
        
    async def consume():
        print("Consuming...")
        # Try reading with timeout
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        print("Received message:", msg)
        
    await asyncio.gather(publish(), consume())
    await pubsub.close()
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
