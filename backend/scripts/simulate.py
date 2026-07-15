#!/usr/bin/env python3
"""
FILE LOCATION: backend/scripts/simulate.py

CLI entrypoint for running attack simulations.

Usage:
    python backend/scripts/simulate.py --attack brute_force
    python backend/scripts/simulate.py --attack dns_tunneling --mode realtime --noise 15
    python backend/scripts/simulate.py --attack all --mode fast --noise 20 --seed 42

Run via justfile:
    just simulate brute_force
    just simulate-all
"""
import argparse
import asyncio
import json
import sys
import os 

# Allow running this script directly without needing the package installed
#sys.path.insert(0, __file__.rsplit("/backend/", 1)[0] + "/backend")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.simulation import ATTACK_TYPES  # noqa: E402
from app.simulation.runner import run_simulation  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Run a SIEM attack simulation")
    parser.add_argument(
        "--attack",
        required=True,
        choices=ATTACK_TYPES + ["all"],
        help="Which attack to simulate, or 'all' for every playbook",
    )
    parser.add_argument(
        "--mode",
        default="fast",
        choices=["fast", "realtime"],
        help="'fast' sends immediately with real timestamps; 'realtime' sleeps between events",
    )
    parser.add_argument(
        "--noise",
        type=int,
        default=20,
        help="Number of unrelated benign background events to interleave",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible simulation runs",
    )
    parser.add_argument(
        "--api-base-url",
        default=None,
        help="Override the ingestion API base URL (defaults to SIMULATION_API_BASE_URL env var or http://localhost:8000)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    print(f"Running simulation: attack={args.attack} mode={args.mode} noise={args.noise} seed={args.seed}")

    summary = await run_simulation(
        attack_type=args.attack,
        mode=args.mode,
        noise_events=args.noise,
        seed=args.seed,
        api_base_url=args.api_base_url,
    )

    print(json.dumps(summary, indent=2))
    print(f"\n✅ Done. Events sent: {summary['events_sent']}")


if __name__ == "__main__":
    asyncio.run(main())