"""gold-council command-line interface. Offline research only; no order placement exists."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from gold_council import __version__
from gold_council.config import load_config, project_root


def _catalog_by_filename(root: Path) -> dict[str, dict]:
    """Map local filenames -> catalog metadata, for rows whose local_path is filled."""
    p = root / "knowledge" / "catalog.csv"
    out = {}
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r.get("local_path"):
                out[Path(r["local_path"]).name] = {"source_id": r["source_id"], "title": r["title"],
                                                   "author": r["author"], "edition": r["edition"],
                                                   "rights": r["rights_basis"]}
    return out


def cmd_status(args, cfg, root):
    from gold_council.execution import CAN_PLACE_ORDERS
    print(json.dumps({
        "version": __version__, "mode": cfg.mode, "symbol": cfg.instrument.symbol,
        "allow_real_account": cfg.risk.allow_real_account, "can_place_orders": CAN_PLACE_ORDERS,
        "implemented": ["config", "risk engine (offline)", "knowledge ingest/search", "detectors",
                        "regime engine (draft thresholds)", "strategy registry", "csv import/validate",
                        "baseline A backtester (OHLC, conservative fills)"],
        "not_implemented": ["MT5 exporters", "council orchestration", "tick-level backtests", "paper broker service",
                            "dashboard", "alerts", "any order execution"],
    }, indent=2))


def cmd_knowledge(args, cfg, root):
    from gold_council.ingestion.ingest import connect, ingest_path, stats
    con = connect(root / cfg.paths.knowledge_db)
    if args.action == "ingest":
        for r in ingest_path(con, Path(args.path), _catalog_by_filename(root)):
            print(f"{r.status:11} {r.source_id or '-':20} chunks={r.chunks:<5} flagged={r.flagged_pages or []} {r.path}")
    elif args.action == "stats":
        print(json.dumps(stats(con), indent=2))
    elif args.action == "search":
        from gold_council.retrieval.search import search
        hits = search(con, args.query, args.limit)
        if not hits:
            print("NO RESULTS (unresolved in local library)")
        for h in hits:
            print(f"[{h.chunk_id}] {h.title} p.{h.page_start}-{h.page_end} score={h.score:.2f}\n    {h.snippet}")


def cmd_strategies(args, cfg, root):
    from gold_council.strategies.registry import load_registry, validate_registry
    defs = load_registry(root / cfg.paths.strategies)
    if args.action == "list":
        for s in defs:
            print(f"{s.spec_id:4} {s.id:28} v{s.version:7} {s.status:18} emits={s.can_emit_candidates()} "
                  f"unresolved={len(s.unresolved)}")
    else:
        probs = validate_registry(defs)
        print("\n".join(probs) if probs else f"OK: {len(defs)} definitions valid")
        return 1 if probs else 0


def cmd_data(args, cfg, root):
    from datetime import timedelta
    from gold_council.market_data.csv_import import load_csv, validate
    df = load_csv(args.path, args.tz)
    rep = validate(df, timedelta(minutes=args.bar_minutes))
    print(json.dumps({**rep.__dict__, "ok": rep.ok,
                      "first_utc": str(df["time"].iloc[0]), "last_utc": str(df["time"].iloc[-1])}, indent=2))
    return 0 if rep.ok else 1


def cmd_regime(args, cfg, root):
    from datetime import datetime, timedelta, timezone
    from gold_council.market_data.csv_import import load_csv, validate
    from gold_council.regime.engine import classify
    bar = timedelta(minutes=args.bar_minutes)
    df = load_csv(args.path, args.tz)
    rep = validate(df, bar)
    if not rep.ok:
        print(json.dumps({"refused": "data failed validation", **rep.__dict__}, indent=2))
        return 1
    now = datetime.now(timezone.utc)
    df = df[df["time"] + bar <= now].reset_index(drop=True)   # completed bars only
    # No point-in-time calendar is wired yet, so event risk is unknown (fails closed).
    print(json.dumps(classify(df, cfg.regime, event_risk=None).to_dict(), indent=2))


def cmd_backtest(args, cfg, root):
    import hashlib
    import subprocess
    from datetime import datetime, timedelta, timezone
    from gold_council.backtesting.engine import Costs, chrono_split, metrics, run, segment
    from gold_council.backtesting.plans import BUILDERS
    from gold_council.market_data.csv_import import load_csv, validate
    bar = timedelta(minutes=args.bar_minutes)
    df = load_csv(args.path, args.tz)
    rep = validate(df, bar)
    if not rep.ok:
        print(json.dumps({"refused": "data failed validation", **rep.__dict__}, indent=2)); return 1
    split = chrono_split(len(df), gap_bars=args.gap_bars)
    seg = segment(df, split, args.segment, args.unseal_reason)
    costs = Costs(spread=args.spread, slippage=args.slippage, latency_bars=args.latency_bars)
    res = run(seg, BUILDERS[args.strategy](seg, bar), costs)
    m = metrics(res)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=root).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "src"], capture_output=True, text=True, cwd=root).stdout.strip())
    except Exception:
        commit, dirty = "unknown", True
    manifest = {
        "run_at": datetime.now(timezone.utc).isoformat(), "experiment": "baseline_A_deterministic",
        "strategy": args.strategy, "segment": args.segment, "unseal_reason": args.unseal_reason,
        "data_path": str(args.path), "data_sha256": hashlib.sha256(Path(args.path).read_bytes()).hexdigest(),
        "broker_tz": args.tz, "bar_minutes": args.bar_minutes, "rows": len(df), "segment_rows": len(seg),
        "split": split.__dict__, "costs": costs.__dict__, "code_commit": commit, "code_dirty": dirty,
        "fill_rules": "next-bar open; SL-first when SL and TP share a bar; gaps through SL exit at open",
        "data_label": args.label, "metrics": m,
        "warning": "Research result. Not evidence of profitability unless data is real, costs are realistic, "
                   "and it survives validation + sealed holdout.",
    }
    keys = ("strategy", "segment", "unseal_reason", "data_sha256", "broker_tz", "bar_minutes", "split", "costs",
            "code_commit", "code_dirty", "data_label")
    run_id = hashlib.sha256(json.dumps({k: manifest[k] for k in keys}, sort_keys=True, default=str)
                            .encode()).hexdigest()[:12]
    if args.segment == "holdout":   # every holdout access is recorded permanently
        log = root / "reports" / "holdout_access_log.md"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"- {manifest['run_at']} run={run_id} strategy={args.strategy} "
                     f"data={manifest['data_sha256'][:12]} reason: {args.unseal_reason.strip()}\n")
    out = root / "reports" / "backtests" / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    import csv as _csv
    with open(out / "trades.csv", "w", newline="") as fh:
        w = _csv.writer(fh); w.writerow(["plan_id", "side", "entry_index", "entry", "exit_index", "exit", "reason", "r"])
        for x in res:
            w.writerow([x.plan_id, x.side, x.entry_index, x.entry, x.exit_index, x.exit, x.reason, x.r])
    print(json.dumps({"run_id": run_id, "saved_to": str(out.relative_to(root)), "data_label": args.label, **m},
                     indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gold-council", description="Gold Council offline research tools "
                                 "(research/paper only; no live trading).")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show mode, safety locks and what is/isn't implemented")
    k = sub.add_parser("knowledge", help="local library")
    ks = k.add_subparsers(dest="action", required=True)
    ki = ks.add_parser("ingest"); ki.add_argument("--path", required=True)
    ks.add_parser("stats")
    kq = ks.add_parser("search"); kq.add_argument("query"); kq.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("strategies", help="strategy registry")
    s.add_argument("action", choices=["list", "validate"])
    d = sub.add_parser("data", help="validate an OHLC CSV export")
    d.add_argument("action", choices=["validate"]); d.add_argument("--path", required=True)
    d.add_argument("--tz", required=True, help="broker server IANA timezone, e.g. Europe/Athens")
    d.add_argument("--bar-minutes", type=int, default=15)
    r = sub.add_parser("regime", help="classify regime of the last completed bar in a CSV")
    r.add_argument("--path", required=True); r.add_argument("--tz", required=True)
    r.add_argument("--bar-minutes", type=int, default=15)
    b = sub.add_parser("backtest", help="baseline A replay on a CSV (dev/validation segments only by default)")
    b.add_argument("--path", required=True); b.add_argument("--tz", required=True)
    b.add_argument("--strategy", required=True, choices=["donchian", "crt_mid", "crt_far"])
    b.add_argument("--bar-minutes", type=int, default=60)
    b.add_argument("--segment", choices=["dev", "validation", "holdout"], default="dev")
    b.add_argument("--unseal-reason", default=None, help="required to touch the holdout")
    b.add_argument("--gap-bars", type=int, default=24)
    b.add_argument("--spread", type=float, required=True, help="round-trip spread in price units (e.g. 0.30)")
    b.add_argument("--slippage", type=float, default=0.0)
    b.add_argument("--latency-bars", type=int, default=0)
    b.add_argument("--label", required=True, choices=["SYNTHETIC", "REAL_PUBLIC", "REAL_BROKER", "OTHER"],
                   help="what kind of data this is; printed on every result")
    args = ap.parse_args(argv)

    root = Path(args.config).resolve().parent if args.config else project_root()
    cfg = load_config(args.config)
    fn = {"status": cmd_status, "knowledge": cmd_knowledge, "strategies": cmd_strategies,
          "data": cmd_data, "regime": cmd_regime, "backtest": cmd_backtest}[args.cmd]
    return fn(args, cfg, root) or 0


if __name__ == "__main__":
    sys.exit(main())
