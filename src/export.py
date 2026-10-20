"""Eksporter untuk hasil ke dalam bentuk JSON"""

# Import library
import math
from src.utils.state_utils import copy_state
from src.utils.validator import violations

# Bentuk kelas error baru
class ExportError(ValueError):
    """Hasil tidak dapat ditunjukkan secara visual"""

# Fungsi validator value ke JSON
def jsonable(value):

    # Memastikan hanya str, bool, int, dan +float yang bisa dipetakan ke JSON
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    raise ExportError(f"JSON value tidak dihandle: {type(value).__name__}")

def validate_single_package(p, index, ids):
    if not isinstance(p.id, str) or not p.id or p.id in ids:
        raise ValueError("ID paket harus unik dan tidak kosong")
    ids.add(p.id)

    orient = p.orientation.orientation
    if len(orient) != 3 or set(orient) != {"w", "l", "h"}:
        raise ValueError("Orientasi harus bernilai antara w, l, dan h")

    dims = list(p.dimension.get_dimensions(orient))
    if any(type(v) is not int or v <= 0 for v in dims):
        raise ValueError("Dimensi harus bernilai positif")
    if any(type(v) is not int or v < 0 for v in (p.value, p.weight, p.eta)):
        raise ValueError("Value, weight and ETA harus bernilai non-negatif")
    if type(p.is_inside) is not bool or type(p.is_fragile) is not bool:
        raise ValueError("Flag inside dan fragile harus bernilai boolean")

    coords = [p.x, p.y, p.z]
    if p.is_inside and any(type(v) is not int for v in coords):
        raise ValueError("Paket yang diload harus menyimpan koordinat")
    if not p.is_inside and any(v is not None for v in coords):
        raise ValueError("Paket yang tidak di load harus tidak menyimpan koordinat")
    return orient, dims

# Converter JSON dari Dict (mendukung 1 State atau list[State] untuk multi-truk)
def state_to_dict(state, context="State", all_trucks=None):
    location = "Truk"

    try:
        raw_states = list(state) if isinstance(state, (list, tuple)) else [state]
        if not raw_states:
            raise ValueError("State tidak boleh kosong")

        # Validasi setiap state sebelum diproses
        for s in raw_states:
            location = "Truk"
            truck = s.truck
            size = [truck.dimension.w, truck.dimension.l, truck.dimension.h]
            if any(type(v) is not int or v <= 0 for v in [*size, truck.max_capacity]):
                raise ValueError("Dimensi dan kapasitas harus bernilai positif")
            s_ids = set()
            for index, p in enumerate(s.packages):
                location = f"Paket {getattr(p, 'id', index + 1)!r}"
                validate_single_package(p, index, s_ids)

        # Deduplikasi paket pada state multi-truk (misal pada initial state antar truk)
        clean_states = [copy_state(s) if len(raw_states) > 1 else s for s in raw_states]
        if len(clean_states) > 1:
            seen_loaded = set()
            for s in clean_states:
                changed = False
                for p in s.packages:
                    if p.is_inside:
                        if p.id in seen_loaded:
                            p.remove()
                            changed = True
                        else:
                            seen_loaded.add(p.id)
                if changed:
                    s.evaluate()

        # Daftar kontainer truk
        trucks_objs = list(all_trucks) if all_trucks else [s.truck for s in clean_states]
        trucks_dicts = []
        for t in trucks_objs:
            location = "Truk"
            t_size = [t.dimension.w, t.dimension.l, t.dimension.h]
            if any(type(v) is not int or v <= 0 for v in [*t_size, t.max_capacity]):
                raise ValueError("Dimensi dan kapasitas harus bernilai positif")
            trucks_dicts.append(dict(zip(("w", "l", "h", "capacity"), [*t_size, t.max_capacity])))

        # Petakan paket yang dimuat ke nomor truknya (1-indexed)
        loaded_by_id = {}
        for truck_idx, s in enumerate(clean_states, 1):
            for p in s.packages:
                if p.is_inside and p.id not in loaded_by_id:
                    loaded_by_id[p.id] = (truck_idx, p)

        packages, ids = [], set()
        for index, base_p in enumerate(clean_states[0].packages):
            if base_p.id in loaded_by_id:
                truck_idx, p = loaded_by_id[base_p.id]
                pos = p.get_position()
            else:
                truck_idx, p = None, base_p
                pos = None

            location = f"Paket {getattr(p, 'id', index + 1)!r}"
            orient, dims = validate_single_package(p, index, ids)

            pkg_dict = {
                "id": p.id, "dims": dims, "pos": list(pos[:3]) if pos else None,
                "truck": truck_idx,
                "orient": list(orient), "value": p.value, "weight": p.weight,
                "fragile": p.is_fragile, "eta": p.eta,
            }
            packages.append(pkg_dict)

        # Pengecekan validasi akhir tiap state truk
        location = "state validation"
        errors = []
        objs = []
        for truck_idx, s in enumerate(clean_states, 1):
            s_errors = violations(s)
            if len(trucks_dicts) > 1:
                errors.extend(f"Truk {truck_idx}: {msg}" for msg in s_errors)
            else:
                errors.extend(s_errors)
            objs.append(s.objective_details())

        total_cap = sum(t["capacity"] for t in trucks_dicts)
        primary_truck = {**trucks_dicts[0], "capacity": total_cap} if len(trucks_dicts) > 1 else trucks_dicts[0]

        # Mengembalikan nilai
        return {
            "truck": primary_truck,
            "trucks": trucks_dicts,
            "packages": packages,
            "value": sum(o["value"] for o in objs),
            "base_value": sum(o["base_value"] for o in objs),
            "penalty_total": sum(o["penalty_total"] for o in objs),
            "penalty_count": sum(o["penalty_count"] for o in objs),
            "penalty": sum(o["penalty"] for o in objs),
            "objective": objs[0]["objective"],
            "weight": sum(p["weight"] for p in packages if p["pos"] is not None),
            "feasible": not errors,
            "violations": errors,
        }

    # Handler untuk error apabila ditemukan
    except (AttributeError, TypeError, ValueError, KeyError, IndexError, OverflowError) as exc:
        raise ExportError(f"Cannot export {context}, {location}: {exc}") from exc

# Fungsi untuk mengecek setiap titik x ada titik y yang mendampinginya
def line_chart(title, x_label, lines, y_label="Nilai objective dari paket yang diload"):
    if any(len(line["x"]) != len(line["y"]) for line in lines):
        raise ExportError(f"Grafik {title!r}: x/y memiliki perbedaan jumlah")
    return {"title": title, "x_label": x_label, "y_label": y_label, "lines": lines}

# Converter line
def to_line(name, values, start=0):
    return {"name": name, "x": list(range(start, start + len(values))), "y": values}

# Converter stats
def to_stats(**values):
    return [{"label": label, "value": value} for label, value in values.items()]

# Converter satu proses algoritma
def to_run(label, seed, initial, final, value, iterations, duration, all_trucks=None):
    return {
        "label": label, "seed": seed, "group": None, "config": None,
        "states": {
            "init": state_to_dict(initial, f"{label}/initial", all_trucks=all_trucks),
            "final": state_to_dict(final, f"{label}/final", all_trucks=all_trucks),
        },
        "labels": {"init": "Initial state (random)", "final": "Final state (terminal)"},
        "final_value": value, "iterations": iterations, "duration": duration,
        "stats": to_stats(**{"Final objective value": value, "Search duration (s)": duration}),
        "notes": [], "charts": []
    }

# Mengembalikan proses HC
def hc_run(result, hc_type, label, seed, params):
    initial = result.init_states or result.init_state
    final = result.final_states or result.final_state
    all_trucks = result.extra.get("trucks")
    run = to_run(label, seed, initial, final, result.final_value, result.iterations, result.duration, all_trucks=all_trucks)
    history, extra = result.value_history, result.extra
    axis = "Iteration (proposal)" if hc_type == "HC_STOCHASTIC" else "Iteration (accepted step)"
    truck_histories = extra.get("truck_histories") or [history]
    if len(truck_histories) > 1:
        chart_lines = [to_line(f"Truk {i + 1}", h) for i, h in enumerate(truck_histories)]
    else:
        chart_lines = [to_line(label, history)]
    run["charts"] = [line_chart("Objektif vs Iterasi", axis, chart_lines)]

    # Klasifikasi berdasarkan jenis HC
    if hc_type == "HC_STEEPEST" or hc_type == "HC_STOCHASTIC":
        run["stats"] += to_stats(**{"Banyak iterasi": result.iterations})
    elif hc_type == "HC_SIDEWAYS":
        run["stats"] += to_stats(**{
            "Banyak iterasi": result.iterations,
            "Maximum pergerakan samping": params.max_side,
        })
    else:
        run["labels"] = {"init": "Initial state untuk awal percobaan", "final": "Terminal state terbaik dalam percobaan"}
        run["charts"] = [
            line_chart("Objective vs Iterasi tiap pengulangan", "Iterasi (langkah diterima tiap pengulangan)", [
                to_line(f"Restart {i + 1}", h) for i, h in enumerate(extra["all_histories"])
            ]),
        ]
        run["stats"] += to_stats(**{
            "Banyak pengulangan": extra["total_restarts"],
            "Banyak iterasi tiap pengulangan": extra["iterations_per_restart"],
            "Pengulangan maksimum": params.max_restart,
        })
    return run

# Mengembalikan proses eksponensial SA
def sa_exponentials(initial_value, history, probabilities):
    if len(history) != len(probabilities):
        raise ExportError("Objektif/probabilitas SA memiliki perbedaan jumlah")
    values, previous = [], initial_value
    for current, probability in zip(history, probabilities):
        improving = current is not None and previous is not None and current > previous
        values.append(probability if 0 < probability < 1 or (probability == 1 and not improving and current is not None and previous is not None) else None)
        previous = current
    return values

# Mengembalikan proses SA
def sa_run(result, label, seed, params):
    initial = result.init_states or result.init_state
    final = result.final_states or result.final_state
    all_trucks = result.extra.get("trucks")
    run = to_run(label, seed, initial, final,
               result.final_value, result.iterations, result.duration, all_trucks=all_trucks)
    extra = result.extra
    run["labels"]["final"] = "Final state"
    truck_histories = extra.get("truck_histories")
    truck_init_values = extra.get("truck_init_values")
    truck_probs = extra.get("truck_probs")

    if truck_histories and len(truck_histories) > 1:
        obj_lines = [
            to_line(f"Truk {i + 1}", [init_v, *h])
            for i, (init_v, h) in enumerate(zip(truck_init_values, truck_histories))
        ]
        exp_lines = [
            to_line(f"Truk {i + 1}", sa_exponentials(init_v, h, pr), 1)
            for i, (init_v, h, pr) in enumerate(zip(truck_init_values, truck_histories, truck_probs))
        ]
    else:
        obj_lines = [to_line(label, [run["states"]["init"]["value"], *result.value_history])]
        exp_lines = [to_line(label, sa_exponentials(result.init_state.value, result.value_history, extra["probs"]), 1)]

    run["charts"] = [
        line_chart("Objektif vs Iterasi", "Iterasi (tahap annealing)", obj_lines),
        line_chart("e^(delta E / T) vs Iterasi", "Iterasi (tahap annealing)", exp_lines, "e^(delta E / T)"),
    ]
    run["stats"] += to_stats(**{"Frekuensi stuck": extra["stuck"]})
    if extra.get("best_states") is not None:
        best = state_to_dict(extra["best_states"], f"{label}/best", all_trucks=all_trucks)
        run["states"]["best"] = best
        run["labels"]["best"] = "Best state ditemukan"
    elif extra.get("best_state") is not None:
        best = state_to_dict(extra["best_state"], f"{label}/best", all_trucks=all_trucks)
        run["states"]["best"] = best
        run["labels"]["best"] = "Best state ditemukan"
    else:
        run["notes"].append("Proses tidak menemukan best state")
    return run

# Mengembalikan proses GA
def ga_run(result):
    runs = []
    all_trucks = result.extra.get("trucks")
    for i, raw in enumerate(result.extra["results"]):
        label = f"Config {i // 3 + 1}, run {i % 3 + 1}"
        initial = raw.get("initial_states") or raw["initial_state"]
        final = raw.get("final_states") or raw["final_state"]
        trucks = raw.get("trucks") or all_trucks
        run = to_run(label, None, initial, final, raw["final_objective"], raw["iterations"], raw["duration_seconds"], all_trucks=trucks)
        run["group"] = i // 3
        run["config"] = {"population_size": raw["population_size"], "generations": raw["iterations"]}
        run["labels"] = {"init": "Individu terbaik pada populasi awal", "final": "Individu terbaik pada akhir proses"}
        history = raw["objective_history"]
        run["charts"] = [line_chart("Objektif populasi vs Iterasi", "Iteration (generation)", [
            {"name": name, "x": history["iteration"], "y": history[key]}
            for name, key in (("Maximum", "maximum"), ("Average", "average"))
        ])]
        run["stats"] += to_stats(**{"Besar populasi": raw["population_size"], "Iterasi": raw["iterations"]})
        runs.append(run)
    return runs

# Mengembalikan state
def state_text(state):
    trucks = state.get("trucks") or [state["truck"]]
    if len(trucks) == 1:
        truck = trucks[0]
        truck_header = f"Truk: {truck['w']} x {truck['l']} x {truck['h']}; Kapasitas: {truck['capacity']}"
    else:
        spec = ", ".join(f"Truk {i}: {t['w']}x{t['l']}x{t['h']} (kap {t['capacity']})" for i, t in enumerate(trucks, 1))
        truck_header = f"Multi-Truk ({len(trucks)} kontainer): {spec}"
    lines = [truck_header,
             f"Objektif: {state['value']}; Beban dimuat: {state['weight']}; Yang bisa dimuat: {state['feasible']}",
             "ID | Status | Posisi (x,y,z) | Besar orientasi | Orientasi | Nilai | Berat | Fragile | ETA"]
    for p in state["packages"]:
        if p["pos"] is None:
            status_str = "Tdk Dimuat"
        elif len(trucks) > 1 or (p.get("truck") and p["truck"] > 1):
            status_str = f"Dimuat (Truk {p.get('truck') or 1})"
        else:
            status_str = "Dimuat"
        fields = [p["id"], status_str, p["pos"],
                  p["dims"], ",".join(p["orient"]), p["value"], p["weight"], p["fragile"], p["eta"]]
        lines.append(" | ".join("-" if value is None else str(value) for value in fields))
    lines.extend(f"Violation: {message}" for message in state["violations"])
    return "\n".join(lines)

# Mengembalikan laporan
def report_text(envelope):
    meta = envelope["meta"]
    objective = meta.get("objective_label") or meta.get("objective", "value")
    lines = [meta["title"], f"Objective: {objective}", ""]
    for run in envelope["runs"]:
        lines.extend([run["label"], "=" * len(run["label"])])
        for key, title in (("init", "Initial state"), ("final", "Final state")):
            lines.extend([f"{title}: {run['labels'][key]}", run["state_texts"][key], ""])
        for item in run["stats"]:
            value = item["value"]
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"{item['label']}: {value if value is not None else '-'}")
        lines.extend(f"Catatan: {note}" for note in run["notes"])
        lines.append("")
    return "\n".join(lines)

# Membangun header
def build_envelope(meta, runs):
    envelope = jsonable({"schema_version": 1, "meta": meta, "runs": runs})
    for run in envelope["runs"]:
        run["state_texts"] = {key: state_text(run["states"][key]) for key in ("init", "final")}
    return envelope