import matplotlib.pyplot as plt
import os

# Path ke file build Anda
electron_deb_path = "my-electron-app/out/make/deb/x64/my-electron-app_1.0.0_amd64.deb" # Ganti dengan path Anda

tauri_deb_path = "./tauri-app/src-tauri/target/release/bundle/deb/tauri-app_0.1.0_amd64.deb"     # Ganti dengan path Anda


# Dapatkan ukuran file dalam MB
try:
    electron_size_bytes = os.path.getsize(electron_deb_path)
    tauri_size_bytes = os.path.getsize(tauri_deb_path)
except FileNotFoundError as e:
    print(f"Error: File tidak ditemukan - {e}")
    exit()

electron_size_mb = electron_size_bytes / (1024 * 1024)
tauri_size_mb = tauri_size_bytes / (1024 * 1024)

# Data untuk plot
app_names = ['Electron App', 'Tauri App']
sizes_mb = [electron_size_mb, tauri_size_mb]

# Membuat bar chart
plt.figure(figsize=(8, 6)) # Ukuran gambar (opsional)
bars = plt.bar(app_names, sizes_mb, color=['skyblue', 'lightgreen'])

# Menambahkan label nilai di atas bar
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + (0.01 * max(sizes_mb)), f'{yval:.2f} MB', ha='center', va='bottom')


plt.ylabel('Ukuran File (MB)')
plt.title('Perbandingan Ukuran File Build Aplikasi')
plt.ylim(0, max(sizes_mb) * 1.1) # Beri sedikit ruang di atas bar tertinggi
plt.grid(axis='y', linestyle='--') # Garis grid horizontal (opsional)

# Simpan grafik sebagai gambar atau tampilkan
plt.savefig('build_size_comparison.png')
print("Grafik disimpan sebagai build_size_comparison.png")
# plt.show() # Uncomment untuk menampilkan grafik secara interaktif
