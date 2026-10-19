# IF3170_G28_MindfulnessAI — Pac-Man (Packet Management)

**Pac-Man (Packet Management)** adalah program optimasi pemuatan paket 3 dimensi ke dalam kontainer truk menggunakan pendekatan algoritma *Local Search*. Program ini mencari susunan dan orientasi paket yang memaksimumkan nilai muatan tanpa melanggar batasan kapasitas berat, dimensi kontainer, gravitasi (paket tidak melayang), maupun aturan paket *fragile*. 

## Identitas Kelompok 28 — MindfulnessAI

| Nama | NIM |
| :--- | :---: |
| Renuno Yuqa Frinardi | 13524080 |
| Valentino Daniel Kusumo | 13524104 |
| Leonardus Brain Fatolosja | 13524146 |

## Fitur & Implementasi Program

- **Algoritma Pencarian Lokal (*Local Search*)**:
  - *Steepest Ascent Hill Climbing* 
  - *Hill Climbing with Sideways Move* 
  - *Stochastic Hill Climbing* 
  - *Random Restart Hill Climbing* 
  - *Simulated Annealing* 
  - *Genetic Algorithm*
- **Fungsi Objektif (*Objective Function*)**:
  - **O1 (`value`)**: Memaksimumkan nilai total paket yang berhasil dimuat di dalam truk.
  - **O2 (`eta_penalty`)**: Nilai total paket dikurangi penalti keterlambatan urutan posisi bongkar-muat berdasarkan *Estimated Time of Arrival* (ETA).
- **Multi-Truk (Bonus)**:
  - Mendukung pemuatan paket secara sekuensial ke dalam beberapa kontainer truk hingga seluruh paket terangkut atau seluruh kontainer terisi.

## Prasyarat

- **Python 3.10+** 
- *Browser* modern dengan dukungan WebGL (Chrome, Edge, atau Firefox) untuk membuka GUI.

## Cara Menjalankan Program

Pastikan terminal berada pada direktori utama (*root*) repositori ini.

### 1. Menjalankan Antarmuka GUI (Web Server)

Jalankan perintah berikut untuk menyalakan server lokal:

```bash
python -m src.server
```

Setelah server berjalan, buka *browser* dan akses:

```text
http://127.0.0.1:8000/
```

Melalui GUI, Anda dapat:
1. Memilih berkas contoh dari folder `input/` pada dropdown **Algoritma** (atau mengunggah file `.txt` / `.json` lewat tombol **Buka JSON / TXT**).
2. Memilih **Objective** (`O1` atau `O2`), mengatur **Seed** dan **Pengulangan**, lalu menekan tombol **Jalankan**.