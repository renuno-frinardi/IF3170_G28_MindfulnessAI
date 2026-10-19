"""Menjalankan solver dan mengolah input output"""

# Import library
import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from src import export
from src.objective import DEFAULT_OBJECTIVE, OBJECTIVES, objective_label, validate_objective
from src.parser.main import parse
from src.solver import solve

# Definisi variable global
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
GA_MODES = {"jumlah_populasi", "banyak_iterasi"}
MAX_PACKAGES = 300
MAX_SA_STEPS = 100_000
MAX_STOCHASTIC_NMAX = 100_000
MAX_RESTARTS = 200
MAX_CANDIDATES = 1_000
max_side = 10_000
MAX_GA_CONTROL = 200

# Parser tulisan
def parse_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input teks tidak boleh kosong.")
    lines = [(i, s.strip()) for i, s in enumerate(text.splitlines(), 1) if s.strip()]
    if lines[0][1] == "GA":
        if len(lines) < 5:
            raise ValueError("Input GA membutuhkan data truk, mode, nilai kontrol, dan jumlah paket.")
        if lines[2][1] not in GA_MODES:
            raise ValueError(f"Baris {lines[2][0]}: mode GA harus tepat 'jumlah_populasi' atau 'banyak_iterasi'.")
    fd, name = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        try:
            return parse(name)
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Kesalahan input: {exc}") from exc
    finally:
        os.unlink(name)

# Validasi integer
def val_integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} harus berupa integer >= {minimum}.")

# Validasi kapasitas
def val_cap(value, limit, name):
    if value > limit:
        raise ValueError(f"{name} melebihi batas ({limit:,}). Gunakan CLI dengan --no-caps untuk eksekusi yang lebih besar")

# Validasi masalah
def validate_problem(problem, enforce_caps=True):
    p = problem.problem
    if not p.packages:
        raise ValueError("Minimal dibutuhkan satu paket")
    if enforce_caps:
        val_cap(len(p.packages), MAX_PACKAGES, "Package count")
    if problem.algo == "SA":
        start, alpha, minimum = p.params.t_start, p.params.alpha, p.params.t_min
        if not all(math.isfinite(v) for v in (start, alpha, minimum)):
            raise ValueError("Temperatur SA dan alpha harus bernilai terhingga (bukan NaN atau tak hingga)")
        if not (start >= minimum > 0 and 0 < alpha < 1):
            raise ValueError("SA membutuhkan t_start >= t_min > 0 dan 0 < alpha < 1")
        steps = (math.log(minimum) - math.log(start)) / math.log(alpha)
        if enforce_caps:
            val_cap(math.floor(steps) + 1, MAX_SA_STEPS, "Estimated SA steps")
    elif problem.algo == "GA":
        if p.pilihan not in GA_MODES:
            raise ValueError("Mode GA tidak dikenal")
        val_integer(p.n, "GA control", 1 if p.pilihan == "jumlah_populasi" else 0)
        if enforce_caps:
            val_cap(p.n, MAX_GA_CONTROL, "GA control")
    elif problem.algo == "HC":
        limits = {"nmax": MAX_STOCHASTIC_NMAX, "num_cand": MAX_CANDIDATES, "max_restart": MAX_RESTARTS, "max_side": max_side}
        for name, value in asdict(p.params).items():
            val_integer(value, name)
            if enforce_caps:
                val_cap(value, limits[name], name)
    else:
        raise ValueError(f"Algoritma tidak dikenal: {problem.algo}")

# Membuat header metadata
def make_meta(problem, seed, repeats, source, input_text, objective=DEFAULT_OBJECTIVE):
    p = problem.problem
    variant = p.hc_type if problem.algo == "HC" else None
    return {
        "title": f"Hill climbing: {variant.removeprefix('HC_').lower().replace('_', ' ')}" if variant else {"SA": "Simulated annealing", "GA": "Genetic algorithm"}[problem.algo],
        "algo": problem.algo, "variant": variant, "seed": seed,
        "objective": objective, "objective_label": objective_label(objective),
        "repeats": None if problem.algo == "GA" else repeats,
        "params": {"pilihan": p.pilihan, "n": p.n} if problem.algo == "GA" else asdict(p.params),
        "source": source, "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_commit": None, "python": platform.python_version(), "input_text": input_text,
    }

# Menjalankan proses
def run_experiment(problem, seed, repeats=3, source="inline", input_text=None, enforce_caps=True, objective=DEFAULT_OBJECTIVE):
    if type(seed) is not int:
        raise ValueError("Seed harus berupa integer.")
    objective = validate_objective(objective)
    validate_problem(problem, enforce_caps)
    if problem.algo != "GA":
        val_integer(repeats, "Repeats")
    meta = make_meta(problem, seed, repeats, source, input_text, objective)
    if problem.algo == "GA":
        runs = export.ga_run(solve(problem, seed=seed, objective_mode=objective))
        meta.update(pilihan=problem.problem.pilihan, control_value=problem.problem.n,
                    winner_index=max(range(len(runs)), key=lambda i: runs[i]["final_value"]))
    else:
        runs = []
        for i in range(repeats):
            result = solve(problem, seed=seed + i, objective_mode=objective)
            label, params = f"Run {i + 1}", problem.problem.params
            if problem.algo == "SA":
                run = export.sa_run(result, label, seed + i, params)
            else:
                run = export.hc_run(result, problem.problem.hc_type, label, seed + i, params)
            runs.append(run)
    return export.build_envelope(meta, runs)

# Menyimpan metadata
def save_envelope(envelope, out_dir=OUTPUT_DIR):
    meta = envelope["meta"]
    label = meta["variant"] or (f"GA_{meta['pilihan']}" if meta["algo"] == "GA" else meta["algo"])
    source = re.sub(r"[^A-Za-z0-9_-]", "_", Path(meta["source"]).stem) or "inline"
    objective = meta.get("objective", DEFAULT_OBJECTIVE)
    suffix = "" if objective == DEFAULT_OBJECTIVE else f"_{objective}"
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{label}{suffix}_{source}_seed{meta['seed']}.json"
    contents = {target: json.dumps(envelope, allow_nan=False, indent=2) + "\n",
                target.with_suffix(".txt"): export.report_text(envelope)}
    staged = []
    try:
        for path, content in contents.items():
            fd, name = tempfile.mkstemp(dir=directory, suffix=".tmp")
            staged.append((name, path))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        for name, path in staged:
            os.replace(name, path)  # Readers never see a half-written file.
    finally:
        for name, _ in staged:
            if os.path.exists(name):
                os.unlink(name)
    return target

# Fungsi entri utama untuk program
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--no-caps", action="store_true", help="Allow larger offline runs; safety checks remain")
    parser.add_argument("--objective", choices=tuple(OBJECTIVES), default=DEFAULT_OBJECTIVE, help="Objective function yang dipakai")
    args = parser.parse_args(argv)
    try:
        text = args.input.read_text(encoding="utf-8")
        envelope = run_experiment(parse_text(text), args.seed, args.repeats, args.input.stem, text, enforce_caps=not args.no_caps, objective=args.objective)
        saved = save_envelope(envelope, args.out)
        print(saved)
        print(saved.with_suffix(".txt"))
        for run in envelope["runs"]:
            print(f"{run['label']}: value={run['final_value']} iterations={run['iterations']} " f"duration={run['duration']:.4f}s feasible={run['states']['final']['feasible']}")
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0

# Entrypoint program
if __name__ == "__main__":
    raise SystemExit(main())
