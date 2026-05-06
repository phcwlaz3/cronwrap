"""Command-line interface for cronwrap utilities."""
from __future__ import annotations

import argparse
import sys

from cronwrap.dashboard import Dashboard
from cronwrap.history import JobHistory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Lightweight cron job wrapper utilities.",
    )
    sub = parser.add_subparsers(dest="command")

    dash = sub.add_parser("dashboard", help="Show a summary dashboard for a job.")
    dash.add_argument("job_name", help="Name of the cron job.")
    dash.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of recent runs to include (default: 50).",
    )
    dash.add_argument(
        "--history-dir",
        default=None,
        help="Override the directory used for run history storage.",
    )

    hist = sub.add_parser("history", help="List recent run records for a job.")
    hist.add_argument("job_name", help="Name of the cron job.")
    hist.add_argument("--limit", type=int, default=10, help="Number of records to show.")
    hist.add_argument("--history-dir", default=None)

    return parser


def cmd_dashboard(args: argparse.Namespace) -> int:
    history = JobHistory(base_dir=args.history_dir) if args.history_dir else JobHistory()
    dash = Dashboard(history=history)
    print(dash.render(args.job_name, limit=args.limit))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    history = JobHistory(base_dir=args.history_dir) if args.history_dir else JobHistory()
    records = history.get_records(args.job_name, limit=args.limit)
    if not records:
        print(f"No history found for job '{args.job_name}'.")
        return 0
    for rec in records:
        status = "OK" if rec.exit_code == 0 else "FAIL"
        print(f"[{status}] {rec.started_at}  exit={rec.exit_code}  duration={rec.duration_seconds}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "dashboard":
        return cmd_dashboard(args)
    if args.command == "history":
        return cmd_history(args)
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
