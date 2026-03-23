//! YeyoOS Guardian — Kill Switch
//! Micro-fase 6.3 — Capa 6: Sistema Inmune
//!
//! PAUSA DE EMERGENCIA de toda la IA.
//! PAUSA, no MATA: todos los procesos IA se pausan y pueden resumirse.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum KillSwitchState {
    Active,
    Paused,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PausedProcess {
    pub name: String,
    pub pid: Option<u32>,
    pub container_id: Option<String>,
    pub paused_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KillSwitchEvent {
    pub timestamp: DateTime<Utc>,
    pub action: String,
    pub triggered_by: String,
    pub processes_affected: usize,
}

const AI_TARGETS: &[&str] = &[
    "ollama",
    "yeyo-backend",
    "stable-diffusion",
    "whisper",
    "tts-server",
];

const AI_CONTAINER_PREFIXES: &[&str] = &[
    "yeyo-ai-",
    "yeyo-node-",
    "yeyo-sandbox-",
];

pub struct KillSwitch {
    state: Arc<RwLock<KillSwitchState>>,
    paused_processes: Arc<RwLock<Vec<PausedProcess>>>,
    events: Arc<RwLock<Vec<KillSwitchEvent>>>,
    state_file: PathBuf,
}

impl KillSwitch {
    pub fn new(state_dir: PathBuf) -> Self {
        let state_file = state_dir.join("kill_switch_state.json");
        let initial_state = Self::load_state(&state_file)
            .unwrap_or(KillSwitchState::Active);

        Self {
            state: Arc::new(RwLock::new(initial_state)),
            paused_processes: Arc::new(RwLock::new(Vec::new())),
            events: Arc::new(RwLock::new(Vec::new())),
            state_file,
        }
    }

    fn load_state(path: &PathBuf) -> Option<KillSwitchState> {
        let content = std::fs::read_to_string(path).ok()?;
        serde_json::from_str(&content).ok()
    }

    async fn save_state(&self) {
        let state = self.state.read().await;
        if let Ok(json) = serde_json::to_string_pretty(&*state) {
            if let Some(parent) = self.state_file.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            if let Err(e) = std::fs::write(&self.state_file, json) {
                error!("No se pudo persistir estado del Kill Switch: {}", e);
            }
        }
    }

    pub async fn toggle(&self, triggered_by: &str) -> KillSwitchState {
        let current = self.get_state().await;
        match current {
            KillSwitchState::Active => self.pause(triggered_by).await,
            KillSwitchState::Paused => self.resume(triggered_by).await,
        }
    }

    pub async fn pause(&self, triggered_by: &str) -> KillSwitchState {
        let mut state = self.state.write().await;

        if *state == KillSwitchState::Paused {
            warn!("[KILL SWITCH] Ya está en pausa");
            return KillSwitchState::Paused;
        }

        error!("═══════════════════════════════════════");
        error!("  🔴 KILL SWITCH ACTIVADO");
        error!("  Pausando TODA la IA del sistema...");
        error!("  Trigger: {}", triggered_by);
        error!("═══════════════════════════════════════");

        let mut paused = Vec::new();

        for target in AI_TARGETS {
            match Self::pause_process_by_name(target).await {
                Ok(pid) => {
                    info!("[KILL SWITCH] Pausado: {} (PID: {:?})", target, pid);
                    paused.push(PausedProcess {
                        name: target.to_string(),
                        pid,
                        container_id: None,
                        paused_at: Utc::now(),
                    });
                }
                Err(e) => {
                    warn!("[KILL SWITCH] No se pudo pausar {}: {}", target, e);
                }
            }
        }

        for prefix in AI_CONTAINER_PREFIXES {
            match Self::pause_containers_by_prefix(prefix).await {
                Ok(containers) => {
                    for cid in containers {
                        info!("[KILL SWITCH] Container pausado: {}", cid);
                        paused.push(PausedProcess {
                            name: format!("container:{}", cid),
                            pid: None,
                            container_id: Some(cid),
                            paused_at: Utc::now(),
                        });
                    }
                }
                Err(e) => {
                    warn!("[KILL SWITCH] Error pausando containers {}: {}", prefix, e);
                }
            }
        }

        let processes_affected = paused.len();

        *state = KillSwitchState::Paused;
        drop(state);

        self.save_state().await;

        let mut pp = self.paused_processes.write().await;
        *pp = paused;

        let event = KillSwitchEvent {
            timestamp: Utc::now(),
            action: "PAUSE".to_string(),
            triggered_by: triggered_by.to_string(),
            processes_affected,
        };
        self.events.write().await.push(event);

        error!(
            "[KILL SWITCH] {} procesos IA pausados. Resume: Ctrl+Alt+K o API.",
            processes_affected
        );

        KillSwitchState::Paused
    }

    pub async fn resume(&self, triggered_by: &str) -> KillSwitchState {
        let mut state = self.state.write().await;

        if *state == KillSwitchState::Active {
            info!("[KILL SWITCH] Ya está activo");
            return KillSwitchState::Active;
        }

        info!("═══════════════════════════════════════");
        info!("  🟢 KILL SWITCH DESACTIVADO");
        info!("  Reanudando IA del sistema...");
        info!("  Trigger: {}", triggered_by);
        info!("═══════════════════════════════════════");

        let paused = self.paused_processes.read().await.clone();
        let mut resumed_count = 0;

        for process in &paused {
            if let Some(pid) = process.pid {
                if Self::resume_process(pid).await.is_ok() {
                    info!("[KILL SWITCH] Reanudado: {} (PID: {})", process.name, pid);
                    resumed_count += 1;
                }
            }
            if let Some(ref cid) = process.container_id {
                if Self::resume_container(cid).await.is_ok() {
                    info!("[KILL SWITCH] Container reanudado: {}", cid);
                    resumed_count += 1;
                }
            }
        }

        *state = KillSwitchState::Active;
        drop(state);

        self.save_state().await;
        self.paused_processes.write().await.clear();

        let event = KillSwitchEvent {
            timestamp: Utc::now(),
            action: "RESUME".to_string(),
            triggered_by: triggered_by.to_string(),
            processes_affected: resumed_count,
        };
        self.events.write().await.push(event);

        info!("[KILL SWITCH] {} procesos reanudados.", resumed_count);

        KillSwitchState::Active
    }

    async fn pause_process_by_name(name: &str) -> Result<Option<u32>, String> {
        let output = tokio::process::Command::new("pgrep")
            .arg("-f")
            .arg(name)
            .output()
            .await
            .map_err(|e| format!("pgrep falló: {}", e))?;

        if !output.status.success() {
            return Err(format!("Proceso '{}' no encontrado", name));
        }

        let pids: Vec<u32> = String::from_utf8_lossy(&output.stdout)
            .lines()
            .filter_map(|l| l.trim().parse().ok())
            .collect();

        for pid in &pids {
            let _ = tokio::process::Command::new("kill")
                .args(["-STOP", &pid.to_string()])
                .output()
                .await;
        }

        Ok(pids.first().copied())
    }

    async fn pause_containers_by_prefix(prefix: &str) -> Result<Vec<String>, String> {
        let output = tokio::process::Command::new("docker")
            .args(["ps", "-q", "--filter", &format!("name={}", prefix)])
            .output()
            .await
            .map_err(|e| format!("docker ps falló: {}", e))?;

        let container_ids: Vec<String> = String::from_utf8_lossy(&output.stdout)
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(|l| l.trim().to_string())
            .collect();

        for cid in &container_ids {
            let _ = tokio::process::Command::new("docker")
                .args(["pause", cid])
                .output()
                .await;
        }

        Ok(container_ids)
    }

    async fn resume_process(pid: u32) -> Result<(), String> {
        tokio::process::Command::new("kill")
            .args(["-CONT", &pid.to_string()])
            .output()
            .await
            .map_err(|e| format!("kill -CONT falló: {}", e))?;
        Ok(())
    }

    async fn resume_container(container_id: &str) -> Result<(), String> {
        tokio::process::Command::new("docker")
            .args(["unpause", container_id])
            .output()
            .await
            .map_err(|e| format!("docker unpause falló: {}", e))?;
        Ok(())
    }

    pub async fn get_state(&self) -> KillSwitchState {
        self.state.read().await.clone()
    }

    pub async fn get_paused_processes(&self) -> Vec<PausedProcess> {
        self.paused_processes.read().await.clone()
    }

    pub async fn get_events(&self) -> Vec<KillSwitchEvent> {
        self.events.read().await.clone()
    }
}
