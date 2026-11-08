"""Live, secret-safe Copilot latency benchmark against a fixed synthetic profile.

Run from backend: python -m scripts.benchmark_copilot --output ../docs/copilot-latency-before.json
Only timings, counts, model ID and success categories are recorded. No keys/replies.
"""
import argparse
import json
import logging
import statistics
import time
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.data.synthetic import DEMO_USER_ID, build_demo_customer
from app.db.memory import InMemoryRepository
from app.schemas.chat import ChatMessage
from app.services.gateway import Gateway
from app.tools.registry import ToolRegistry
from intelligence import copilot

QUESTIONS = {
    "health": "How was my health score calculated?",
    "risk": "Explain my biggest risk",
    "simulation": "What if I cut $200 over 10 days?",
}


def benchmark(repeats=3):
    logging.disable(logging.CRITICAL)
    settings = get_settings()
    as_of = date(2026, 11, 8)
    repo = InMemoryRepository(build_demo_customer(as_of))
    original_client, original_render = copilot._client, copilot.format_reply
    rows = []
    try:
        for name, question in QUESTIONS.items():
            for sample in range(repeats):
                phases = []
                tool_times = []
                render_times = []

                class TimedTools(ToolRegistry):
                    def call(self, tool, args=None):
                        started = time.perf_counter()
                        try:
                            return super().call(tool, args)
                        finally:
                            tool_times.append(time.perf_counter() - started)

                class TimedClient:
                    def __enter__(self):
                        self.client = original_client(settings)
                        self.models = self
                        return self

                    def __exit__(self, *_):
                        self.client.close()

                    def generate_content(self, **kwargs):
                        started = time.perf_counter()
                        try:
                            return self.client.models.generate_content(**kwargs)
                        finally:
                            phase = "composition" if kwargs["config"].response_json_schema else "tools"
                            phases.append((phase, time.perf_counter() - started))

                def render(*args, **kwargs):
                    started = time.perf_counter()
                    try:
                        return original_render(*args, **kwargs)
                    finally:
                        render_times.append(time.perf_counter() - started)

                copilot._client = lambda _: TimedClient()
                copilot.format_reply = render
                tools = TimedTools(repo.load_profile(DEMO_USER_ID, as_of), Gateway("baseline"), settings)
                started = time.perf_counter()
                row = {"question": name, "sample": sample + 1}
                try:
                    result = copilot.chat([ChatMessage(role="user", content=question)], tools)
                    row.update(success=True, source=result.meta.source, reply_characters=len(result.reply))
                except Exception as exc:
                    row.update(success=False, error_category=type(exc).__name__)
                row.update(
                    total_s=round(time.perf_counter() - started, 4),
                    model_s=round(sum(duration for _, duration in phases), 4),
                    composition_s=round(sum(duration for phase, duration in phases if phase == "composition"), 4),
                    tool_s=round(sum(tool_times), 4), render_s=round(sum(render_times), 4),
                    model_calls=len(phases), tool_executions=len(tool_times),
                )
                rows.append(row)
                print(json.dumps(row), flush=True)
    finally:
        copilot._client, copilot.format_reply = original_client, original_render
    summary = {}
    for question in QUESTIONS:
        attempts = [row for row in rows if row["question"] == question]
        samples = [row for row in attempts if row["success"]]
        summary[question] = {
            "successes": len(samples),
            "failures": len(attempts) - len(samples),
            "attempt_median_s": round(statistics.median(row["total_s"] for row in attempts), 4),
            "attempt_range_s": [min(row["total_s"] for row in attempts), max(row["total_s"] for row in attempts)],
            **({"median_s": round(statistics.median(row["total_s"] for row in samples), 4),
                "median_model_calls": statistics.median(row["model_calls"] for row in samples),
                "median_model_s": round(statistics.median(row["model_s"] for row in samples), 4),
                "median_tool_s": round(statistics.median(row["tool_s"] for row in samples), 4),
                "median_composition_s": round(statistics.median(row["composition_s"] for row in samples), 4)}
               if samples else {}),
        }
    return {"model": settings.gemini_model, "as_of": as_of.isoformat(), "repeats": repeats,
            "samples": rows, "summary": summary}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 6))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = benchmark(args.repeats)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"]}), flush=True)
