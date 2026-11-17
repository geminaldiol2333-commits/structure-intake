"""Compare ways of turning the predicted molfile into SMILES, on bench_v0/raw.jsonl."""
import json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-prototypes"))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "tools"))
import prototype as page
page.patch_molscribe()
from molscribe.chemistry import _expand_functional_group
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
import eval_ocsr

def current(block):
    return page.derived_strings(block, "")[0]

def sanitized(block):
    mol = Chem.MolFromMolBlock(block)          # sanitize: wedges -> chirality, 2D -> E/Z
    if mol is None:
        return current(block)
    if any(a.HasProp("molFileAlias") or a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
        try:
            s, _ = _expand_functional_group(Chem.Mol(mol), {}, False)
            if s and s != "<invalid>":
                return s
        except Exception:
            pass
        return current(block)
    return Chem.MolToSmiles(mol)

def no_either(block):
    """Double bonds written as 'either' (stereo 3) get their geometry back from 2D."""
    out = []
    lines = block.splitlines()
    counts = None
    for i, line in enumerate(lines):
        if i == 3:
            counts = (int(line[0:3]), int(line[3:6]))
        if counts and 4 + counts[0] <= i < 4 + counts[0] + counts[1]:
            if line[6:9].strip() == "2" and line[9:12].strip() == "3":
                line = line[:9] + "  0" + line[12:]
        out.append(line)
    return chr(10).join(out)


def fixed(block):
    return sanitized(no_either(block))


rows = [json.loads(l) for l in open(os.path.join(ROOT, "out", "bench_v0", "raw.jsonl"), encoding="utf-8")]
man = os.path.join(ROOT, "..", "..", "benchmark_v2", "manifest_all.jsonl")
for name, fn in (("fixed", fixed), ("current_noeither", lambda b: current(no_either(b)))):
    path = os.path.join(ROOT, "out", "bench_v0", f"exp_{name}.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            smi = r["model_smiles"] if fn is None else (fn(r.get("molfile") or "") if r.get("molfile") else "")
            fh.write(json.dumps({"image_id": r["image_id"], "prediction": smi}) + "\n")
    _, summary, _ = eval_ocsr.score_predictions(man, path, "acs1996")
    b = next(x for x in summary if x["group"] == "ALL")
    print(f"{name:10s} exact {b['exact']:.3f} conn {b['connectivity']:.3f} chiral {b['chiral_match']:.3f} ez {b['e_z_match']:.3f} valid {b['valid']:.3f}")
