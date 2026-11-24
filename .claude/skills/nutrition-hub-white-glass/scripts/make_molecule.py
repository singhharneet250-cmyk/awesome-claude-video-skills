#!/usr/bin/env python3
"""
SMILES -> 3D molecule data for templates/molecule-3d.html (needs RDKit: pip install rdkit).

    python3 make_molecule.py --id creatine --name Creatine --smiles "N[C:1](=N)N(C)CC(=O)O" --formula C4H9N3O2
    python3 make_molecule.py --batch ../assets/molecules/library.json      # rebuild the whole library

The coordinates are a computed conformer (RDKit ETKDGv3 embedding, then MMFF94 optimisation),
not an experimental structure: say so on screen ("3D model: computed conformer").

Checks before writing:
  --formula  must equal RDKit's molecular formula (catches a wrong SMILES)
  --cip      e.g. "S" or "S,R": must equal the CIP labels of the stereocentres, in the order
             the atoms appear in the SMILES (catches a wrong enantiomer, e.g. D- instead of L-leucine)
An atom map number ":1" in the SMILES marks the one signal-orange accent atom.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, rdMolDescriptors
    from rdkit.Chem import rdCIPLabeler
except ImportError:
    sys.exit("RDKit is needed: pip install rdkit")

import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "molecules"


def build(mid, name, smiles, formula=None, cip=None, seed=0xC0FFEE):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"{mid}: RDKit could not parse the SMILES")
    accent = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum() == 1]
    for a in mol.GetAtoms():
        a.SetAtomMapNum(0)

    got = rdMolDescriptors.CalcMolFormula(mol)
    if formula and got != formula:
        raise ValueError(f"{mid}: formula is {got}, expected {formula}. Check the SMILES.")

    rdCIPLabeler.AssignCIPLabels(mol)
    labels = [a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")]
    if cip is not None and ",".join(labels) != cip:
        raise ValueError(f"{mid}: stereocentres are {','.join(labels) or 'none'}, expected {cip}. Check @/@@ in the SMILES.")

    molh = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(molh, params) != 0:
        raise ValueError(f"{mid}: 3D embedding failed")
    method = "RDKit ETKDGv3 + MMFF94"
    if AllChem.MMFFHasAllMoleculeParams(molh):
        AllChem.MMFFOptimizeMolecule(molh, maxIters=2000)
    else:
        AllChem.UFFOptimizeMolecule(molh, maxIters=2000)
        method = "RDKit ETKDGv3 + UFF"

    xyz = molh.GetConformer().GetPositions()
    xyz -= xyz.mean(0)
    # principal axes: longest extent along x, then y, so every molecule frames the same way
    _, _, vt = np.linalg.svd(xyz, full_matrices=False)
    xyz = xyz @ vt.T
    if np.linalg.det(vt) < 0:          # keep handedness (a mirror image is a different enantiomer)
        xyz[:, 2] *= -1

    atoms = [[a.GetSymbol(), *[round(float(v), 4) for v in p]] for a, p in zip(molh.GetAtoms(), xyz)]
    bonds = []
    for b in molh.GetBonds():
        order = b.GetBondTypeAsDouble()
        bonds.append([b.GetBeginAtomIdx(), b.GetEndAtomIdx(), 1.5 if b.GetIsAromatic() else order])
    return {
        "id": mid, "name": name, "formula": got, "smiles": smiles,
        "stereo": ",".join(labels) or None,
        "method": method + " (computed conformer, not an experimental structure)",
        "accent": accent[0] if accent else None,
        "atoms": atoms, "bonds": bonds,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id"); ap.add_argument("--name"); ap.add_argument("--smiles")
    ap.add_argument("--formula"); ap.add_argument("--cip")
    ap.add_argument("--batch", type=Path, help="JSON list of {id, name, smiles, formula, cip}")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    entries = json.loads(args.batch.read_text()) if args.batch else [vars(args)]
    args.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for e in entries:
        try:
            data = build(e["id"], e["name"], e["smiles"], e.get("formula"), e.get("cip"))
        except (ValueError, KeyError) as err:
            print(f"FAIL {err}"); failed += 1; continue
        (args.out / f"{data['id']}.json").write_text(json.dumps(data, separators=(",", ":")))
        heavy = sum(1 for a in data["atoms"] if a[0] != "H")
        print(f"ok   {data['id']:<16} {data['formula']:<12} stereo {data['stereo'] or '-':<8} "
              f"{heavy} heavy atoms, accent atom {data['accent']}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
