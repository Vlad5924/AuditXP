"""Нагрузочная проверка PER-02 и PER-03 по HTTP.

Запуск при работающем сервере
    python scripts/load_test.py --base http://127.0.0.1:8000 --users 20
"""
import argparse
import asyncio
import json
import statistics
import time

import httpx

SCENARIOS = {
    "overview": "/api/v1/dashboard/overview",
    "risks": "/api/v1/risks?status=open&limit=50",
    "heatmap": "/api/v1/heatmap?date_from=2026-10-01&date_to=2026-10-31",
    "reports": "/api/v1/reports",
}


async def worker(client, path, count, timings):
    for _ in range(count):
        started = time.perf_counter()
        response = await client.get(path)
        response.raise_for_status()
        timings.append(time.perf_counter() - started)


async def main(base: str, users: int, requests: int) -> dict:
    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        token = (await client.post("/api/v1/auth/login", json={
            "login": "zhdanko", "password": "Auditor2026"})).json()
        client.headers["Authorization"] = f"Bearer {token['access_token']}"
        report = {}
        for name, path in SCENARIOS.items():
            timings: list[float] = []
            started = time.perf_counter()
            await asyncio.gather(*(worker(client, path, requests, timings)
                                   for _ in range(users)))
            total = time.perf_counter() - started
            timings.sort()
            report[name] = {
                "requests": len(timings),
                "avg_ms": round(statistics.mean(timings) * 1000, 1),
                "p95_ms": round(timings[int(len(timings) * 0.95) - 1]
                                * 1000, 1),
                "max_ms": round(timings[-1] * 1000, 1),
                "rps": round(len(timings) / total, 1)}
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--requests", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(main(args.base, args.users, args.requests)),
                     ensure_ascii=False, indent=2))
