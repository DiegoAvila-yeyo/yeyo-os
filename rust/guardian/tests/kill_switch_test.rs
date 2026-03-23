//! Tests para Kill Switch — Micro-fase 6.3

use std::path::PathBuf;
use yeyo_guardian::kill_switch::{KillSwitch, KillSwitchState};

fn temp_state_dir() -> PathBuf {
    let dir = std::env::temp_dir().join(format!("yeyo-ks-test-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[tokio::test]
async fn test_initial_state_is_active() {
    let ks = KillSwitch::new(temp_state_dir());
    assert_eq!(ks.get_state().await, KillSwitchState::Active);
}

#[tokio::test]
async fn test_pause_changes_state() {
    let ks = KillSwitch::new(temp_state_dir());
    let state = ks.pause("test").await;
    assert_eq!(state, KillSwitchState::Paused);
    assert_eq!(ks.get_state().await, KillSwitchState::Paused);
}

#[tokio::test]
async fn test_resume_changes_state() {
    let ks = KillSwitch::new(temp_state_dir());
    ks.pause("test").await;
    let state = ks.resume("test").await;
    assert_eq!(state, KillSwitchState::Active);
}

#[tokio::test]
async fn test_toggle_works() {
    let ks = KillSwitch::new(temp_state_dir());
    let state = ks.toggle("test").await;
    assert_eq!(state, KillSwitchState::Paused);
    let state = ks.toggle("test").await;
    assert_eq!(state, KillSwitchState::Active);
}

#[tokio::test]
async fn test_events_recorded() {
    let ks = KillSwitch::new(temp_state_dir());
    ks.pause("keyboard-shortcut").await;
    ks.resume("keyboard-shortcut").await;

    let events = ks.get_events().await;
    assert_eq!(events.len(), 2);
    assert_eq!(events[0].action, "PAUSE");
    assert_eq!(events[1].action, "RESUME");
    assert_eq!(events[0].triggered_by, "keyboard-shortcut");
}

#[tokio::test]
async fn test_state_persists_to_file() {
    let dir = temp_state_dir();
    {
        let ks = KillSwitch::new(dir.clone());
        ks.pause("test").await;
    }
    let ks2 = KillSwitch::new(dir);
    assert_eq!(ks2.get_state().await, KillSwitchState::Paused);
}

#[tokio::test]
async fn test_double_pause_is_safe() {
    let ks = KillSwitch::new(temp_state_dir());
    ks.pause("test").await;
    let state = ks.pause("test").await;
    assert_eq!(state, KillSwitchState::Paused);
}

#[tokio::test]
async fn test_double_resume_is_safe() {
    let ks = KillSwitch::new(temp_state_dir());
    let state = ks.resume("test").await;
    assert_eq!(state, KillSwitchState::Active);
}
