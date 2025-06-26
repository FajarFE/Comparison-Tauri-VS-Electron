import subprocess
import time
import os
import shutil # Untuk membersihkan direktori output

# --- Konfigurasi ---
electron_project_dir = "/home/fajar/Project/compare elektron vs tauri/my-electron-app"
tauri_project_dir = "/home/fajar/Project/compare elektron vs tauri/tauri-app"

electron_build_command = "npm run make"
tauri_build_command = "cargo tauri build"

# Direktori output yang akan dibersihkan untuk "cold build"
electron_output_dirs = ["out"] # Relatif terhadap electron_project_dir
tauri_output_dirs = ["src-tauri/target", "dist"] # Relatif terhadap tauri_project_dir
                                              # 'dist' adalah output frontend default Vite

# Jumlah pengulangan untuk setiap skenario build
repetitions = 1 # Ubah menjadi 2 atau 3 untuk hasil rata-rata yang lebih baik

# --- Fungsi Helper ---
def run_build_command(command, working_dir, description):
    """Menjalankan perintah build dan mengukur waktunya."""
    print(f"\n--- Menjalankan: {description} ---")
    print(f"Direktori: {working_dir}")
    print(f"Perintah: {command}")

    start_time = time.time()
    try:
        # Jalankan perintah
        # stdout=subprocess.PIPE dan stderr=subprocess.PIPE untuk menangkap output jika diperlukan
        # text=True agar output berupa string
        process = subprocess.Popen(
            command,
            shell=True, # Diperlukan untuk 'npm run ...' di beberapa sistem
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate() # Tunggu hingga selesai

        end_time = time.time()
        duration = end_time - start_time

        if process.returncode == 0:
            print(f"BERHASIL: {description} selesai dalam {duration:.2f} detik.")
            # print("Output:\n", stdout) # Uncomment untuk melihat output standar
        else:
            print(f"ERROR: {description} gagal (kode: {process.returncode}). Durasi: {duration:.2f} detik.")
            print("Stderr:\n", stderr)
            # print("Stdout:\n", stdout) # Tampilkan juga stdout jika ada error
            return None # Kembalikan None jika gagal
        return duration
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"EXCEPTION saat menjalankan {description}: {e}. Durasi hingga exception: {duration:.2f} detik.")
        return None

def clean_directory(base_dir, relative_dirs):
    """Membersihkan direktori output."""
    print(f"Membersihkan direktori output di {base_dir}...")
    for rel_dir in relative_dirs:
        dir_to_clean = os.path.join(base_dir, rel_dir)
        if os.path.exists(dir_to_clean):
            try:
                shutil.rmtree(dir_to_clean)
                print(f"  Dihapus: {dir_to_clean}")
            except Exception as e:
                print(f"  Gagal menghapus {dir_to_clean}: {e}")
        else:
            print(f"  Tidak ditemukan (sudah bersih): {dir_to_clean}")

def average(lst):
    """Menghitung rata-rata dari list, mengabaikan None."""
    valid_values = [x for x in lst if x is not None]
    return sum(valid_values) / len(valid_values) if valid_values else None

# --- Main Script ---
if __name__ == "__main__":
    if "/path/to/your/" in electron_project_dir or \
       "/path/to/your/" in tauri_project_dir:
        print("PERINGATAN: Anda belum mengganti path placeholder dalam skrip!")
        print("Silakan edit skrip dan ganti '/path/to/your/...' dengan path yang benar.")
        exit()

    results = {
        "Electron Cold Build": [],
        "Tauri Cold Build": [],
        # Anda bisa menambahkan skenario "Warm Build" jika diperlukan
        # dengan memodifikasi file dan tidak membersihkan output
    }

    print("Memulai Pengujian Kecepatan Build...\n")

    # Skenario 1: Cold Build
    print("=== SKENARIO: COLD BUILD ===")
    for i in range(repetitions):
        print(f"\n--- Iterasi Cold Build ke-{i+1} dari {repetitions} ---")

        # Cold Build Electron
        clean_directory(electron_project_dir, electron_output_dirs)
        duration_electron = run_build_command(electron_build_command, electron_project_dir, "Electron Cold Build")
        results["Electron Cold Build"].append(duration_electron)
        time.sleep(2) # Jeda singkat antar build

        # Cold Build Tauri
        clean_directory(tauri_project_dir, tauri_output_dirs)
        duration_tauri = run_build_command(tauri_build_command, tauri_project_dir, "Tauri Cold Build")
        results["Tauri Cold Build"].append(duration_tauri)
        time.sleep(2)

    # --- Tampilkan Hasil ---
    print("\n\n--- HASIL PENGUJIAN KECEPATAN BUILD ---")
    for scenario, durations in results.items():
        avg_duration = average(durations)
        if avg_duration is not None:
            print(f"Rata-rata {scenario}: {avg_duration:.2f} detik (dari {len([d for d in durations if d is not None])} run berhasil)")
        else:
            print(f"{scenario}: Tidak ada run yang berhasil.")

    # Anda bisa menambahkan visualisasi di sini jika mau,
    # menggunakan matplotlib, mirip dengan skrip visualisasi ukuran file.
    # Misalnya, buat bar chart dari rata-rata durasi.

    # Contoh sederhana visualisasi (membutuhkan matplotlib)
    try:
        import matplotlib.pyplot as plt

        avg_electron_cold = average(results["Electron Cold Build"])
        avg_tauri_cold = average(results["Tauri Cold Build"])

        if avg_electron_cold is not None and avg_tauri_cold is not None:
            labels = ['Electron Cold Build', 'Tauri Cold Build']
            times = [avg_electron_cold, avg_tauri_cold]
            colors = ['skyblue', 'lightgreen']

            plt.figure(figsize=(8, 6))
            bars = plt.bar(labels, times, color=colors, width=0.5)

            for bar in bars:
                yval = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2.0, yval + (0.01 * max(times, default=0)),
                         f'{yval:.2f} s', ha='center', va='bottom', fontweight='bold')

            plt.ylabel('Waktu Build Rata-rata (detik)')
            plt.title('Perbandingan Kecepatan Cold Build')
            plt.xticks(rotation=0)
            plt.grid(axis='y', linestyle='--')
            plt.tight_layout()
            output_image = "build_speed_comparison.png"
            plt.savefig(output_image)
            print(f"\nGrafik perbandingan kecepatan build disimpan sebagai: {output_image}")
            # plt.show() # Uncomment untuk menampilkan
        else:
            print("\nTidak dapat membuat grafik karena data tidak lengkap.")

    except ImportError:
        print("\nMatplotlib tidak terinstal. Tidak dapat membuat grafik visualisasi.")
    except Exception as e:
        print(f"\nError saat membuat grafik: {e}")

    print("\nPengujian Selesai.")
