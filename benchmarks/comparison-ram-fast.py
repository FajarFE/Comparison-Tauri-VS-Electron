import subprocess
import time
import psutil
import os
import platform

# --- Konfigurasi (GANTI INI DENGAN PATH DAN NAMA YANG BENAR) ---
# Nama executable seperti yang Anda jalankan dari terminal setelah instalasi
# atau seperti yang ditemukan oleh `which nama_aplikasi`
electron_executable_name = "my-electron-app" # Contoh, mungkin berbeda
tauri_executable_name = "tauri-app"         # Contoh, mungkin berbeda

# Path absolut ke executable jika tidak ada di PATH sistem
# Jika ada di PATH, biarkan None atau string kosong
electron_executable_path = None # Contoh: "/opt/MyElectronApp/my-electron-app"
tauri_executable_path = None    # Contoh: "/opt/MyTauriApp/tauri-app"


# Durasi untuk pengukuran idle (detik)
idle_measurement_duration = 10
# Durasi untuk Anda melakukan interaksi manual (detik)
manual_interaction_duration = 20

# Jumlah pengulangan
repetitions = 1 # Ubah jika ingin rata-rata dari beberapa run

# --- Fungsi Helper ---

def get_process_info(process_name_or_pid):
    """Mencari proses dan mengembalikan info CPU & memori.
       Untuk Electron, ini mungkin hanya menangkap proses utama.
    """
    procs_found = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'cmdline']):
        try:
            # Mencocokkan berdasarkan nama atau PID
            if (isinstance(process_name_or_pid, str) and process_name_or_pid.lower() in proc.info['name'].lower()) or \
               (isinstance(process_name_or_pid, int) and process_name_or_pid == proc.info['pid']):
                # Untuk Electron, coba cari proses utama (bukan gpu, utility, dll)
                # Ini adalah heuristik dan mungkin perlu disesuaikan
                cmd = proc.info.get('cmdline')
                is_electron_main_candidate = True
                if cmd and isinstance(process_name_or_pid, str) and "electron" in process_name_or_pid.lower():
                    if any(arg in ['--type=gpu-process', '--type=utility', '--type=renderer'] for arg in cmd):
                        is_electron_main_candidate = False

                if is_electron_main_candidate:
                    procs_found.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not procs_found:
        return None

    # Untuk kesederhanaan, jika ada beberapa proses cocok (misal Electron),
    # kita bisa coba ambil yang utama atau jumlahkan.
    # Saat ini, kita ambil yang pertama ditemukan atau yang paling banyak menggunakan memori (heuristik)
    # Ini adalah bagian yang paling menantang untuk akurasi Electron.
    if len(procs_found) > 1:
        print(f"  Peringatan: Ditemukan {len(procs_found)} proses cocok untuk '{process_name_or_pid}'. Menggunakan yang paling banyak memori.")
        procs_found.sort(key=lambda p: p.memory_info().rss, reverse=True)


    # Ambil info dari proses yang dipilih (misalnya, yang pertama atau yang paling banyak memori)
    # Untuk Electron yang akurat, Anda perlu strategi yang lebih baik untuk agregasi semua prosesnya.
    target_proc = procs_found[0] # Ambil yang pertama (atau yang paling banyak memori jika diurutkan)
    try:
        cpu = target_proc.cpu_percent(interval=0.1) # interval kecil untuk pengukuran cepat
        mem_rss_mb = target_proc.memory_info().rss / (1024 * 1024) # Resident Set Size
        return {"pid": target_proc.pid, "cpu_percent": cpu, "memory_rss_mb": mem_rss_mb, "name": target_proc.name()}
    except psutil.NoSuchProcess: # Proses mungkin sudah ditutup
        return None


def launch_and_monitor(app_name, executable_name, executable_path=None):
    """Meluncurkan aplikasi dan memantau startup kasar, idle, dan penggunaan aktif."""
    print(f"\n--- Mengukur Aplikasi: {app_name} ---")

    # Tentukan perintah untuk meluncurkan aplikasi
    if executable_path and os.path.exists(executable_path):
        command = [executable_path]
    else:
        # Coba temukan dengan 'which' jika tidak ada path absolut
        which_path = shutil.which(executable_name)
        if which_path:
            command = [which_path]
            print(f"  Ditemukan di PATH: {which_path}")
        else:
            print(f"  ERROR: Executable '{executable_name}' tidak ditemukan di PATH atau path yang diberikan tidak valid.")
            return None, None, None, None

    # 1. Mengukur Waktu Startup Kasar (hingga proses terdeteksi)
    startup_time = None
    process = None
    start_launch_time = time.time()
    try:
        # Gunakan Popen agar skrip tidak menunggu aplikasi ditutup
        process_handle = subprocess.Popen(command)
        time.sleep(0.5) # Beri waktu sedikit agar proses benar-benar dimulai

        # Coba temukan PID dari proses yang baru diluncurkan
        # Ini adalah bagian yang rumit; mencocokkan nama bisa tidak selalu akurat
        # Jika Anda tahu PID, itu lebih baik.
        launched_pid = process_handle.pid
        initial_info = get_process_info(launched_pid) # Coba dengan PID dulu
        if not initial_info: # Jika gagal dengan PID, coba dengan nama
             time.sleep(1) # Tunggu lebih lama jika PID tidak langsung terdaftar
             initial_info = get_process_info(executable_name)


        if initial_info and initial_info["pid"] == launched_pid:
            startup_time = time.time() - start_launch_time
            print(f"  Proses '{initial_info['name']}' (PID: {initial_info['pid']}) terdeteksi setelah {startup_time:.2f} detik (startup kasar).")
            process = psutil.Process(initial_info["pid"]) # Dapatkan objek proses psutil
        else:
            print(f"  Peringatan: Tidak dapat secara pasti mengidentifikasi proses yang diluncurkan untuk {executable_name} dengan PID {launched_pid}. Startup kasar tidak akurat.")
            # Coba cari berdasarkan nama sebagai fallback, tapi ini kurang ideal jika ada banyak instance
            fallback_info = get_process_info(executable_name)
            if fallback_info:
                process = psutil.Process(fallback_info["pid"])
                print(f"  Menggunakan proses fallback (PID: {fallback_info['pid']}, Nama: {fallback_info['name']})")
            else:
                print(f"  ERROR: Tidak dapat menemukan proses untuk {executable_name} sama sekali.")
                if process_handle: process_handle.terminate() # coba tutup jika ada handle
                return None, None, None, None


    except Exception as e:
        print(f"  ERROR saat meluncurkan atau mendeteksi proses {app_name}: {e}")
        if process_handle: process_handle.terminate()
        return None, None, None, None

    if not process:
        print(f"  Gagal mendapatkan objek proses untuk {app_name}.")
        if process_handle: process_handle.terminate()
        return None, None, None, None

    # 2. Mengukur Penggunaan Saat Idle
    print(f"  Mengukur penggunaan idle selama {idle_measurement_duration} detik...")
    time.sleep(idle_measurement_duration) # Tunggu aplikasi menjadi idle
    idle_info = get_process_info(process.pid) # Gunakan PID yang sudah didapat
    if idle_info:
        print(f"  Idle - CPU: {idle_info['cpu_percent']:.2f}%, RAM: {idle_info['memory_rss_mb']:.2f} MB")
    else:
        print(f"  Peringatan: Tidak bisa mendapatkan info idle untuk {app_name}.")

    # 3. Pengukuran Saat Interaksi Manual
    print(f"  SIAPKAN INTERAKSI MANUAL untuk {app_name} selama {manual_interaction_duration} detik...")
    print(f"  Mulai berinteraksi dengan aplikasi SEKARANG. Pengukuran akan dimulai dalam 3 detik.")
    time.sleep(3)

    active_cpu_readings = []
    active_ram_readings = []
    interaction_start_time = time.time()
    while time.time() - interaction_start_time < manual_interaction_duration:
        try:
            current_info = get_process_info(process.pid)
            if current_info:
                active_cpu_readings.append(current_info['cpu_percent'])
                active_ram_readings.append(current_info['memory_rss_mb'])
            time.sleep(0.5) # Interval pembacaan
        except psutil.NoSuchProcess:
            print(f"  Proses {app_name} ditutup saat interaksi manual.")
            break
        except Exception as e:
            print(f"  Error saat membaca info aktif: {e}")
            break

    active_info_summary = None
    if active_ram_readings and active_cpu_readings:
        active_info_summary = {
            "peak_cpu": max(active_cpu_readings) if active_cpu_readings else 0,
            "avg_cpu": sum(active_cpu_readings) / len(active_cpu_readings) if active_cpu_readings else 0,
            "peak_ram_mb": max(active_ram_readings) if active_ram_readings else 0,
            "avg_ram_mb": sum(active_ram_readings) / len(active_ram_readings) if active_ram_readings else 0,
        }
        print(f"  Aktif (Ringkasan) - Puncak CPU: {active_info_summary['peak_cpu']:.2f}%, Puncak RAM: {active_info_summary['peak_ram_mb']:.2f} MB")
    else:
        print(f"  Tidak ada data yang cukup terkumpul selama interaksi manual untuk {app_name}.")


    # Tutup aplikasi
    print(f"  Menutup aplikasi {app_name} (PID: {process.pid})...")
    try:
        process.terminate() # Coba terminasi dengan baik
        process.wait(timeout=5) # Tunggu hingga 5 detik
        print(f"  Aplikasi {app_name} berhasil ditutup.")
    except psutil.NoSuchProcess:
        print(f"  Aplikasi {app_name} sudah tertutup.")
    except psutil.TimeoutExpired:
        print(f"  Gagal menutup {app_name} dengan terminate, mencoba kill...")
        process.kill()
        process.wait(timeout=2)
        print(f"  Aplikasi {app_name} di-kill.")
    except Exception as e:
        print(f"  Error saat menutup {app_name}: {e}")


    return startup_time, idle_info, active_info_summary

# --- Main Script ---
if __name__ == "__main__":
    import shutil # Untuk shutil.which

    # Peringatan jika path placeholder masih ada
    if electron_executable_path and "/path/to/your/" in electron_executable_path :
        print("PERINGATAN: Path placeholder untuk Electron belum diganti!")
    if tauri_executable_path and "/path/to/your/" in tauri_executable_path :
        print("PERINGATAN: Path placeholder untuk Tauri belum diganti!")


    results = {
        "Electron": {"startup": [], "idle_cpu": [], "idle_ram": [], "active_peak_cpu": [], "active_peak_ram": []},
        "Tauri": {"startup": [], "idle_cpu": [], "idle_ram": [], "active_peak_cpu": [], "active_peak_ram": []},
    }

    for i in range(repetitions):
        print(f"\n=== ITERASI KE-{i+1} DARI {repetitions} ===")

        # Uji Electron
        s_e, i_e, a_e = launch_and_monitor("Electron", electron_executable_name, electron_executable_path)
        if s_e is not None: results["Electron"]["startup"].append(s_e)
        if i_e:
            results["Electron"]["idle_cpu"].append(i_e["cpu_percent"])
            results["Electron"]["idle_ram"].append(i_e["memory_rss_mb"])
        if a_e:
            results["Electron"]["active_peak_cpu"].append(a_e["peak_cpu"])
            results["Electron"]["active_peak_ram"].append(a_e["peak_ram_mb"])
        time.sleep(5) # Jeda antar aplikasi

        # Uji Tauri
        s_t, i_t, a_t = launch_and_monitor("Tauri", tauri_executable_name, tauri_executable_path)
        if s_t is not None: results["Tauri"]["startup"].append(s_t)
        if i_t:
            results["Tauri"]["idle_cpu"].append(i_t["cpu_percent"])
            results["Tauri"]["idle_ram"].append(i_t["memory_rss_mb"])
        if a_t:
            results["Tauri"]["active_peak_cpu"].append(a_t["peak_cpu"])
            results["Tauri"]["active_peak_ram"].append(a_t["peak_ram_mb"])
        time.sleep(5)


    # --- Tampilkan Hasil Rata-rata ---
    print("\n\n--- HASIL PENGUKURAN PERFORMA RUNTIME (RATA-RATA) ---")

    def print_avg_results(app_label, app_results):
        print(f"\n{app_label}:")
        if app_results["startup"]:
            print(f"  Waktu Startup Kasar: {sum(app_results['startup'])/len(app_results['startup']):.2f} detik")
        if app_results["idle_ram"]:
            print(f"  RAM Idle: {sum(app_results['idle_ram'])/len(app_results['idle_ram']):.2f} MB")
        if app_results["idle_cpu"]:
            print(f"  CPU Idle: {sum(app_results['idle_cpu'])/len(app_results['idle_cpu']):.2f} %")
        if app_results["active_peak_ram"]:
            print(f"  Puncak RAM Aktif: {sum(app_results['active_peak_ram'])/len(app_results['active_peak_ram']):.2f} MB")
        if app_results["active_peak_cpu"]:
            print(f"  Puncak CPU Aktif: {sum(app_results['active_peak_cpu'])/len(app_results['active_peak_cpu']):.2f} %")

    print_avg_results("Electron", results["Electron"])
    print_avg_results("Tauri", results["Tauri"])

    # Di sini Anda bisa menambahkan kode visualisasi matplotlib jika diinginkan,
    # mirip dengan skrip sebelumnya, menggunakan data dari dictionary `results`.
    # Contoh sederhana:
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        metrics_to_plot = {
            "Waktu Startup Kasar (s)": ("startup", results["Electron"]["startup"], results["Tauri"]["startup"]),
            "RAM Idle (MB)": ("idle_ram", results["Electron"]["idle_ram"], results["Tauri"]["idle_ram"]),
            "Puncak RAM Aktif (MB)": ("active_peak_ram", results["Electron"]["active_peak_ram"], results["Tauri"]["active_peak_ram"])
        }
        num_metrics = len(metrics_to_plot)
        fig, axes = plt.subplots(nrows=1, ncols=num_metrics, figsize=(5 * num_metrics, 5))
        if num_metrics == 1: # Jika hanya satu metrik, axes tidak akan menjadi array
            axes = [axes]

        plot_idx = 0
        for title, (key, data_e, data_t) in metrics_to_plot.items():
            ax = axes[plot_idx]
            avg_e = sum(data_e)/len(data_e) if data_e else 0
            avg_t = sum(data_t)/len(data_t) if data_t else 0

            labels = ['Electron', 'Tauri']
            values = [avg_e, avg_t]
            colors = ['skyblue', 'lightgreen']

            bars = ax.bar(labels, values, color=colors, width=0.6)
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, yval + (0.01 * max(values, default=0)),
                         f'{yval:.2f}', ha='center', va='bottom', fontweight='bold')
            ax.set_ylabel(title.split('(')[-1].replace(')', '').strip()) # Ambil satuan dari judul
            ax.set_title(title)
            ax.grid(axis='y', linestyle='--')
            plot_idx +=1

        plt.tight_layout()
        output_image = "runtime_performance_comparison.png"
        plt.savefig(output_image)
        print(f"\nGrafik perbandingan performa runtime disimpan sebagai: {output_image}")

    except ImportError:
        print("\nMatplotlib tidak terinstal. Tidak dapat membuat grafik visualisasi.")
    except Exception as e:
        print(f"\nError saat membuat grafik: {e}")


    print("\nPengujian Selesai.")
