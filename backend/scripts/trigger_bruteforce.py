#!/usr/bin/env python3
import asyncio
import httpx
from datetime import datetime, timezone

API_URL = "http://localhost:8000/api/v1/events"

async def main():
    base = datetime.now(timezone.utc)
    
    # We need 3 high-severity login_failed events from the same source to trigger demo_threshold_bruteforce
    payloads = [
        {
            "timestamp": base.isoformat(),
            "source": "10.0.0.99",
            "event_type": "login_failed",
            "severity": "high",
            "raw_payload": {"user": "admin"},
            "metadata": {}
        }
        for _ in range(3)
    ]
    
    async with httpx.AsyncClient() as client:
        print("Sending 3 high-severity login_failed events from 10.0.0.99...")
        response = await client.post(API_URL, json=payloads)
        
        if response.status_code == 201:
            print("Events ingested successfully!")
            print("The correlation engine should have triggered the 'demo_threshold_bruteforce' alert in the background.")
        else:
            print(f"Error ingesting events: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
