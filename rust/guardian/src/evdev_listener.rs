//! YeyoOS Guardian — Captura de teclado a nivel kernel
//! Micro-fase 6.3 — Capa 6: Sistema Inmune
//!
//! Captura Ctrl+Alt+K vía evdev (Linux).
//! En macOS, solo disponible via API/CLI.

use std::sync::Arc;
use tokio::sync::Notify;
use tracing::{info, warn};

pub struct EvdevListener {
    trigger: Arc<Notify>,
}

impl EvdevListener {
    pub fn new() -> Self {
        Self {
            trigger: Arc::new(Notify::new()),
        }
    }

    pub fn get_trigger(&self) -> Arc<Notify> {
        self.trigger.clone()
    }

    pub async fn start(&self) {
        info!("[EVDEV] Iniciando listener de teclado para Kill Switch (Ctrl+Alt+K)");

        #[cfg(target_os = "linux")]
        {
            self.start_linux_listener().await;
        }

        #[cfg(not(target_os = "linux"))]
        {
            warn!("[EVDEV] No es Linux — Kill Switch solo disponible via API/CLI");
            // Wait indefinitely on non-Linux
            let () = std::future::pending().await;
        }
    }

    #[cfg(target_os = "linux")]
    async fn start_linux_listener(&self) {
        use std::fs::File;
        use std::io::Read;
        use std::mem;
        use tracing::error;

        #[repr(C)]
        struct InputEvent {
            tv_sec: i64,
            tv_usec: i64,
            type_: u16,
            code: u16,
            value: i32,
        }

        let kbd_path = Self::find_keyboard_device().unwrap_or_else(|| {
            warn!("[EVDEV] No se encontró teclado, usando /dev/input/event0");
            "/dev/input/event0".to_string()
        });

        info!("[EVDEV] Escuchando en: {}", kbd_path);

        let trigger = self.trigger.clone();

        tokio::task::spawn_blocking(move || {
            let mut file = match File::open(&kbd_path) {
                Ok(f) => f,
                Err(e) => {
                    error!("[EVDEV] No se pudo abrir {}: {}", kbd_path, e);
                    return;
                }
            };

            let event_size = mem::size_of::<InputEvent>();
            let mut buf = vec![0u8; event_size];
            let mut ctrl_pressed = false;
            let mut alt_pressed = false;

            const EV_KEY: u16 = 1;
            const KEY_K: u16 = 37;
            const KEY_LEFTCTRL: u16 = 29;
            const KEY_RIGHTCTRL: u16 = 97;
            const KEY_LEFTALT: u16 = 56;
            const KEY_RIGHTALT: u16 = 100;

            loop {
                if file.read_exact(&mut buf).is_err() {
                    break;
                }

                let event: InputEvent = unsafe {
                    std::ptr::read(buf.as_ptr() as *const InputEvent)
                };

                if event.type_ != EV_KEY {
                    continue;
                }

                let pressed = event.value == 1;

                match event.code {
                    KEY_LEFTCTRL | KEY_RIGHTCTRL => ctrl_pressed = pressed,
                    KEY_LEFTALT | KEY_RIGHTALT => alt_pressed = pressed,
                    KEY_K if pressed && ctrl_pressed && alt_pressed => {
                        info!("[EVDEV] 🔴 Ctrl+Alt+K detectado — Kill Switch!");
                        trigger.notify_one();
                    }
                    _ => {}
                }
            }
        });
    }

    #[cfg(target_os = "linux")]
    fn find_keyboard_device() -> Option<String> {
        let proc_devices = std::fs::read_to_string("/proc/bus/input/devices").ok()?;
        let mut current_handlers = String::new();
        let mut is_keyboard = false;

        for line in proc_devices.lines() {
            if line.starts_with("H: Handlers=") {
                current_handlers = line.to_string();
            }
            if line.contains("EV=120013") || line.contains("keyboard") {
                is_keyboard = true;
            }
            if line.is_empty() {
                if is_keyboard {
                    for part in current_handlers.split_whitespace() {
                        if part.starts_with("event") {
                            return Some(format!("/dev/input/{}", part));
                        }
                    }
                }
                is_keyboard = false;
            }
        }

        None
    }
}

impl Default for EvdevListener {
    fn default() -> Self {
        Self::new()
    }
}
