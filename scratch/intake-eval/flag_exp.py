"""Which cheap checks on the predicted molfile separate right from wrong reads?"""
import json, os, sys, math
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-prototypes"))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "tools"))
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
import prototype as page
import eval_ocsr

def flags(block):
    out = {}
    raw = Chem.MolFromMolBlock(block, sanitize=False)
    if raw is None:
        return {"parse": True}
    try:
        m = Chem.Mol(raw); Chem.SanitizeMol(m)
    except Exception:
        out["valence"] = True
        m = None
    if m is not None:
        out["radical"] = any(a.GetNumRadicalElectrons() for a in m.GetAtoms())
        out["fragments"] = len(Chem.GetMolFrags(m)) > 1
    conf = raw.GetConformer()
    lens = []
    for b in raw.GetBonds():
        p, q = conf.GetAtomPosition(b.GetBeginAtomIdx()), conf.GetAtomPosition(b.GetEndAtomIdx())
        lens.append(math.hypot(p.x - q.x, p.y - q.y))
    if lens:
        med = sorted(lens)[len(lens) // 2]
        out["long_bond"] = max(lens) > 2.5 * med if med else False
    out["alias"] = any(a.HasProp("molFileAlias") for a in raw.GetAtoms())
    return out

rows = [json.loads(l) for l in open(os.path.join(ROOT, "out", "bench_v0", "raw.jsonl"), encoding="utf-8")]
man = eval_ocsr.load_manifest_index(os.path.join(ROOT, "..", "..", "benchmark_v2", "manifest_all.jsonl"))
stats = {}
for r in rows:
    block = page.clear_either_doubles(r.get("molfile") or "")
    smi = page.derived_strings(block, "")[0] if block else ""
    truth = man[r["image_id"]]["smiles_isomeric"]
    ok = bool(eval_ocsr.canon(smi) and eval_ocsr.canon(smi) == eval_ocsr.canon(truth))
    f = flags(block) if block else {"empty": True}
    anyflag = any(v for k, v in f.items() if k != "alias")
    for k in list(f) + ["ANY", "NONE"]:
        v = anyflag if k == "ANY" else (not anyflag if k == "NONE" else f.get(k))
        if v:
            s = stats.setdefault(k, [0, 0]); s[0] += 1; s[1] += ok
total_ok = sum(1 for r in rows)
for k, (n, good) in sorted(stats.items()):
    print(f"{k:10s} n={n:4d} exact among flagged={good / n:.2f}")
