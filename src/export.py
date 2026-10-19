"""Eksporter untuk hasil ke dalam bentuk JSON"""

# Import library
import math
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

# Converter JSON dari Dict
def state_to_dict(state, context="State"):
    location = "Truk"

    try:
        # Pengecekan truk
        truck = state.truck
        size = [truck.dimension.w, truck.dimension.l, truck.dimension.h]
        if any(type(v) is not int or v <= 0 for v in [*size, truck.max_capacity]):
            raise ValueError("Dimensi dan kapasitas harus bernilai positif")

        # Pengecekan truk
        packages, ids = [], set()
        for index, p in enumerate(state.packages):

            # Pengecekan paket
            location = f"Paket {getattr(p, 'id', index + 1)!r}"
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
            pos = p.get_position() if p.is_inside else None

            # Menyimpan paket ke dict
            packages.append({
                "id": p.id, "dims": dims, "pos": list(pos[:3]) if pos else None,
                "orient": list(orient), "value": p.value, "weight": p.weight,
                "fragile": p.is_fragile, "eta": p.eta,
            })

        # Pengecekan validasi akhir
        location = "state validation"
        errors = violations(state)

        # Mengembalikan nilai
        return {
            "truck": dict(zip(("w", "l", "h", "capacity"), [*size, truck.max_capacity])),
            "packages": packages, "value": state.objective_value(),
            "weight": sum(p.weight for p in state.packages if p.is_inside),
            "feasible": not errors, "violations": errors,
        }

    # Handler untuk error apabila ditemukan
    except (AttributeError, TypeError, ValueError, KeyError, IndexError, OverflowError) as exc:
        raise ExportError(f"Cannot export {context}, {location}: {exc}") from exc

# Fungsi untuk mengecek setiap titik x ada titik y yang mendampinginya
def line_chart(title, x_label, lines, y_label="Total nilai dari paket yang diload"):
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
def to_run(label, seed, initial, final, value, iterations, duration):
    return {
        "label": label, "seed": seed, "group": None, "config": None,
        "states": {"init": state_to_dict(initial, f"{label}/initial"), "final": state_to_dict(final, f"{label}/final")},
        "labels": {"init": "Initial state (random)", "final": "Final state (terminal)"},
        "final_value": value, "iterations": iterations, "duration": duration,
        "stats": to_stats(**{"Final objective value": value, "Search duration (s)": duration}),
        "notes": [], "charts": []
    }

# Mengembalikan proses HC
def hc_run(result, hc_type, label, seed, params):
    run = to_run(label, seed, result.init_state, result.final_state, result.final_value, result.iterations, result.duration)
    history, extra = result.value_history, result.extra
    axis = "Iteration (proposal)" if hc_type == "HC_STOCHASTIC" else "Iteration (accepted step)"
    run["charts"] = [line_chart("Objektif vs Iterasi", axis, [to_line(label, history)])]

    # Klasifikasi berdasarkan jenis HC
    if hc_type == "HC_STEEPEST" or hc_type == "HC_STOCHASTIC":
        run["stats"] += to_stats(**{"Banyak iterasi hingga terminasi": result.iterations})
    elif hc_type == "HC_SIDEWAYS":
        run["stats"] += to_stats(**{
            "Banyak iterasi hingga terminasi": result.iterations,
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
    run = to_run(label, seed, result.init_state, result.final_state,
               result.final_value, result.iterations, result.duration)
    extra = result.extra
    run["labels"]["final"] = "Final state"
    run["charts"] = [
        line_chart("Objektif vs Iterasi", "Iterasi (tahap annealing)", [
            to_line(label, [run["states"]["init"]["value"], *result.value_history])]),
        line_chart("e^(delta E / T) vs Iterasi", "Iterasi (tahap annealing)", [
            to_line(label, sa_exponentials(result.init_state.value, result.value_history, extra["probs"]), 1)
        ], "e^(delta E / T)"),
    ]
    run["stats"] += to_stats(**{"Berapa kali terjebak": extra["stuck"]})
    if extra.get("best_state") is not None:
        best = state_to_dict(extra["best_state"], f"{label}/best")
        run["states"]["best"] = best
        run["labels"]["best"] = "Best state ditemukan"
    else:
        run["notes"].append("Proses tidak menemukan best state")
    return run

# Mengembalikan proses GA
def ga_run(result):
    runs = []
    for i, raw in enumerate(result.extra["results"]):
        label = f"Config {i // 3 + 1}, run {i % 3 + 1}"
        run = to_run(label, None, raw["initial_state"], raw["final_state"], raw["final_objective"], raw["iterations"], raw["duration_seconds"])
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
    truck = state["truck"]
    lines = [f"Truk: {truck['w']} x {truck['l']} x {truck['h']}; Kapasitas: {truck['capacity']}",
             f"Objektif: {state['value']}; Beban dimuat: {state['weight']}; Yang bisa dimuat: {state['feasible']}",
             "ID | Status | Posisi (x,y,z) | Besar orientasi | Orientasi | Nilai | Berat | Fragile | ETA"]
    for p in state["packages"]:
        fields = [p["id"], "Tdk Dimuat" if p["pos"] is None else "Dimuat", p["pos"],
                  p["dims"], ",".join(p["orient"]), p["value"], p["weight"], p["fragile"], p["eta"]]
        lines.append(" | ".join("-" if value is None else str(value) for value in fields))
    lines.extend(f"Violation: {message}" for message in state["violations"])
    return "\n".join(lines)

# Mengembalikan laporan
def report_text(envelope):
    lines = [envelope["meta"]["title"], ""]
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
