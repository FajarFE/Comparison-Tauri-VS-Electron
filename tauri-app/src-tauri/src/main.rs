// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    let tauri_setup_start_time = std::time::Instant::now();
    tauri::Builder::default()
        .setup(move |_app| {
            println!("[Tauri Backend] Setup took: {:?}", tauri_setup_start_time.elapsed());
            Ok(())
        })
        // ...
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
