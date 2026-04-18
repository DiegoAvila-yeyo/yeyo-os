#!/usr/bin/env python3
"""
Smoke test para el piloto circular de YeyoNet.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lanza y monitorea un run del piloto circular de YeyoNet")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL base de la Central")
    parser.add_argument("--flow-id", default="image_prompt_ring_v1", help="Flow a ejecutar")
    parser.add_argument("--prompt", required=True, help="Prompt de imagen")
    parser.add_argument("--negative-prompt", default="", help="Negative prompt opcional")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--priority", type=int, default=5)
    parser.add_argument(
        "--ring-node-id",
        action="append",
        dest="ring_node_ids",
        help="IDs del anillo en orden. Si no se pasan, el backend intenta resolver central + satelites online.",
    )
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", type=Path, help="Ruta donde guardar el JSON final del run")
    return parser


def _print_step_table(run: dict) -> None:
    print(f"run_id={run.get('run_id')} status={run.get('status')} flow={run.get('flow_id')}")
    for step in run.get("steps", []):
        print(
            f"  step={step.get('step_index')} type={step.get('step_type')} "
            f"status={step.get('status')} assigned_to={step.get('assigned_to')} "
            f"job_id={step.get('job_id')}"
        )


def main() -> int:
    args = _build_parser().parse_args()
    base_url = args.base_url.rstrip("/")
    payload = {
        "flow_id": args.flow_id,
        "input": {
            "prompt": args.prompt,
            "negative_prompt": args.negative_prompt,
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "guidance_scale": args.guidance_scale,
            "seed": args.seed,
        },
        "priority": args.priority,
    }
    if args.ring_node_ids:
        payload["ring_node_ids"] = args.ring_node_ids

    with httpx.Client(timeout=30.0) as client:
        identity = client.get(f"{base_url}/api/v1/yeyonet/identity")
        identity.raise_for_status()
        print("identity:", json.dumps(identity.json(), ensure_ascii=False))

        satellites = client.get(f"{base_url}/api/v1/yeyonet/satellites")
        satellites.raise_for_status()
        print("satellites:", json.dumps(satellites.json(), ensure_ascii=False))

        response = client.post(f"{base_url}/api/v1/yeyonet/pipelines/runs", json=payload)
        response.raise_for_status()
        run = response.json()
        run_id = run["run_id"]
        print("created:", json.dumps({"run_id": run_id, "status": run.get("status")}, ensure_ascii=False))
        _print_step_table(run)

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            poll = client.get(f"{base_url}/api/v1/yeyonet/pipelines/runs/{run_id}")
            poll.raise_for_status()
            run = poll.json()
            _print_step_table(run)
            if run.get("status") in {"completed", "failed", "cancelled"}:
                if args.output:
                    args.output.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"saved: {args.output}")
                return 0 if run.get("status") == "completed" else 1
            time.sleep(args.poll_interval)

    print("timeout waiting for pipeline run", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
