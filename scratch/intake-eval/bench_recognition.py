# -*- coding: utf-8 -*-
"""Benchmark the intake app's recognition path on the benchmark_v2 manifest.

Runs app.predict_file on every image of one drawing template, derives SMILES
from the graph path (molblock -> derived_strings) and keeps MolNexTR's own
SMILES alongside, scores both with tools/eval_ocsr.py, and prints a compact
comparison against the stock MolNexTR predictions.

Resumable: image_ids already present in <out>/raw.jsonl are skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "scratch", "intake-v0.1"))

import app  # noqa: E402  inserts scratch/intake-prototypes and imports prototype
import prototype as page  # noqa: E402
from eval_ocsr import score_predictions  # noqa: E402

MANIFEST = os.path.join(ROOT, "benchmark_v2", "manifest_all.jsonl")
STOCK = os.path.join(ROOT, "predictions", "v2_acs1996", "molnextr.jsonl")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", default="acs1996")
    ap.add_argument("--variants", default="",
                    help="comma-separated variant list; empty means all")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--out",
                    default=os.path.join(ROOT, "scratch", "intake-eval", "out", "bench"))
    return ap.parse_args()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    raw_path = os.path.join(args.out, "raw.jsonl")

    done = set()
    if os.path.exists(raw_path):
        for rec in read_jsonl(raw_path):
            done.add(rec.get("image_id"))

    rows = read_jsonl(MANIFEST)
    variants = {v.strip() for v in args.variants.split(",") if v.strip()}
    sel = [r for r in rows
           if r.get("template") == args.template
           and (not variants or r.get("variant") in variants)
           and r["image_id"] not in done]
    sel.sort(key=lambda r: r["image_id"])
    if args.limit:
        sel = sel[:args.limit]

    print(f"template {args.template}, {len(sel)} images to run "
          f"({len(done)} already in raw.jsonl)", flush=True)
    fh = open(raw_path, "a", encoding="utf-8")
    t0 = time.time()
    n_errors = 0
    for count, row in enumerate(sel, 1):
        t_img = time.time()
        image = os.path.join(ROOT, "benchmark_v2", row["image_path"])
        error = ""
        pred = {}
        try:
            pred = app.predict_file(image) or {}
        except Exception as exc:
            error = f"predict_file {type(exc).__name__}: {exc}"[:300]
        graph = ""
        try:
            graph, _ = page.derived_strings(page.clear_either_doubles(pred.get("molfile") or ""), "")
        except Exception as exc:
            if not error:
                error = f"derived_strings {type(exc).__name__}: {exc}"[:300]
        try:
            gate_ok, gate_reason = page.molscribe_gate(pred)
        except Exception as exc:
            gate_ok, gate_reason = False, f"gate {type(exc).__name__}: {exc}"[:200]
        rec = {
            "image_id": row["image_id"],
            "image_path": row["image_path"],
            "graph_smiles": graph or "",
            "model_smiles": pred.get("smiles") or "",
            "molfile": pred.get("molfile") or "",
            "confidence": pred.get("confidence"),
            "n_atoms": len(pred.get("atoms") or []),
            "gate_ok": bool(gate_ok),
            "gate_reason": gate_reason or "",
            "seconds": round(time.time() - t_img, 3),
            "error": error,
        }
        if error:
            n_errors += 1
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        if count % 50 == 0:
            rate = count / max(time.time() - t0, 1e-9)
            print(f"[{count}/{len(sel)}] {rate:.2f} img/s "
                  f"errors {n_errors}", flush=True)
    fh.close()
    if sel:
        print(f"ran {len(sel)} images in {time.time() - t0:.0f}s, "
              f"{n_errors} errors", flush=True)

    # Prediction files for scoring, built from ALL rows in raw.jsonl.
    g_path = os.path.join(args.out, "pred_graph.jsonl")
    m_path = os.path.join(args.out, "pred_model.jsonl")
    for dest, key in ((g_path, "graph_smiles"), (m_path, "model_smiles")):
        with open(dest, "w", encoding="utf-8") as out:
            for rec in read_jsonl(raw_path):
                out.write(json.dumps(
                    {"image_id": rec["image_id"],
                     "prediction": rec.get(key) or ""},
                    ensure_ascii=False) + "\n")

    per_graph, sum_graph, _ = score_predictions(MANIFEST, g_path, args.template)
    per_model, sum_model, _ = score_predictions(MANIFEST, m_path, args.template)
    per_stock, sum_stock, _ = score_predictions(MANIFEST, STOCK, args.template)
    with open(os.path.join(args.out, "summary_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(sum_graph, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out, "summary_model.json"), "w", encoding="utf-8") as fh:
        json.dump(sum_model, fh, indent=2, ensure_ascii=False)

    headline = f"organic_weighted_{args.template}"

    def pick(blocks, group):
        return next((b for b in blocks if b.get("group") == group), {})

    def row_of(blocks):
        head = pick(blocks, headline)
        allimg = pick(blocks, "ALL")
        return (head.get("exact"), head.get("connectivity"), head.get("valid"),
                allimg.get("exact"))

    def fmt(v):
        return "n/a" if v is None else f"{v:.3f}"

    print()
    w = "{:<8} {:>8} {:>8} {:>8} {:>12}"
    print(w.format("path", "exact", "conn", "valid", "ALL img exact"))
    print("-" * 52)
    for name, blocks in (("graph", sum_graph), ("model", sum_model),
                         ("stock", sum_stock)):
        e, c, v, a = row_of(blocks)
        print(w.format(name, fmt(e), fmt(c), fmt(v), fmt(a)))

    # Gate stats on the graph path, per image.
    gate = {rec["image_id"]: rec.get("gate_ok") for rec in read_jsonl(raw_path)}
    acc = [r for r in per_graph if gate.get(r["image_id"])]
    rej = [r for r in per_graph if not gate.get(r["image_id"])]

    def exact_rate(rows_):
        if not rows_:
            return None
        return sum(1 for r in rows_ if r.get("exact")) / len(rows_)

    total = len(acc) + len(rej)
    print()
    print(f"gate accepted {len(acc)}/{total} ({len(acc) / total:.3f})"
          if total else "no images scored")
    print(f"exact among accepted:   {fmt(exact_rate(acc))}  (n={len(acc)})")
    print(f"exact among rejected:   {fmt(exact_rate(rej))}  (n={len(rej)})")


if __name__ == "__main__":
    main()
