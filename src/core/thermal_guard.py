"""
YeyoOS — Thermal Guard
Monitoreo de temperatura GPU/CPU durante generación de imágenes.

Lógica de throttling:
  - GPU >= PAUSE_TEMP  →  pausa el proceso hasta que baje a GPU_RESUME_TEMP
  - CPU >= PAUSE_TEMP  →  pausa el proceso hasta que baje a CPU_RESUME_TEMP
  - GPU >= CRITICAL_TEMP o CPU >= CRITICAL_TEMP → aborta la generación (ThermalAbortError)
  - Hilo de monitoreo en background (cada MONITOR_INTERVAL seg) independiente de los callbacks
  - Si no hay sensor de temperatura CPU disponible, throttlea por uso de CPU (>85% sostenido)

Umbrales (conservadores para GTX 1060 3GB / CPU genérica):
  GPU: pausa a 72°C, reanuda a 60°C, crítico a 85°C
  CPU: pausa a 70°C, reanuda a 58°C, crítico a 90°C

Fuentes de temperatura CPU en Windows (orden de preferencia):
  1. LibreHardwareMonitor via WMI (root/LibreHardwareMonitor)
  2. MSAcpi_ThermalZoneTemperature via WMI (root/wmi)
  3. Fallback por carga de CPU (psutil) — activa throttle si >85% por 3+ lecturas
"""

import time
import threading
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("yeyoos.core.thermal")

# ── Umbrales ───────────────────────────────────────────────────────────────
GPU_PAUSE_TEMP    = 72   # °C — pausa la generación
GPU_RESUME_TEMP   = 60   # °C — reanuda la generación
GPU_CRITICAL_TEMP = 85   # °C — aborta la generación

CPU_PAUSE_TEMP    = 70   # °C — pausa la generación
CPU_RESUME_TEMP   = 58   # °C — reanuda la generación
CPU_CRITICAL_TEMP = 90   # °C — aborta la generación

POLL_INTERVAL    = 2.0   # segundos entre lecturas mientras espera enfriar
MONITOR_INTERVAL = 1.5   # segundos entre lecturas del hilo de background

# Throttle por carga CPU cuando no hay sensor: pausa si >85% por N lecturas
CPU_LOAD_PAUSE_PCT   = 85
CPU_LOAD_PAUSE_COUNT = 3   # lecturas consecutivas antes de pausar
# ───────────────────────────────────────────────────────────────────────────


class ThermalAbortError(RuntimeError):
    """Se lanza cuando la temperatura alcanza el umbral crítico y la generación debe detenerse."""


@dataclass
class ThermalStatus:
    gpu_temp: float | None   # None si no hay GPU NVIDIA o pynvml no disponible
    cpu_temp: float | None   # None si ningún sensor CPU está disponible
    cpu_load: float | None   # % uso CPU (psutil), usado como fallback
    gpu_paused: bool
    cpu_paused: bool
    gpu_critical: bool
    cpu_critical: bool

    @property
    def should_pause(self) -> bool:
        return self.gpu_paused or self.cpu_paused

    @property
    def is_critical(self) -> bool:
        return self.gpu_critical or self.cpu_critical

    def __str__(self) -> str:
        gpu_str = f"{self.gpu_temp:.0f}°C" if self.gpu_temp is not None else "N/A"
        cpu_str = f"{self.cpu_temp:.0f}°C" if self.cpu_temp is not None else "N/A"
        load_str = f" (carga {self.cpu_load:.0f}%)" if self.cpu_load is not None else ""
        return f"GPU={gpu_str} CPU={cpu_str}{load_str}"


class ThermalGuard:
    """
    Guarda térmica para procesos intensivos de GPU/CPU.

    Incluye:
    - check_and_wait(): llamar en cada step del pipeline SD.
    - Hilo de monitoreo en background que pausa/aborta independientemente de los callbacks.

    Ejemplo:
        guard = ThermalGuard()
        guard.start_background_monitor()
        def sd_callback(pipe, step_index, timestep, callback_kwargs):
            guard.check_and_wait(step=step_index, total=total_steps)
            return callback_kwargs
        # Al finalizar:
        guard.stop_background_monitor()
    """

    def __init__(
        self,
        gpu_pause: int = GPU_PAUSE_TEMP,
        gpu_resume: int = GPU_RESUME_TEMP,
        gpu_critical: int = GPU_CRITICAL_TEMP,
        cpu_pause: int = CPU_PAUSE_TEMP,
        cpu_resume: int = CPU_RESUME_TEMP,
        cpu_critical: int = CPU_CRITICAL_TEMP,
        poll_interval: float = POLL_INTERVAL,
        monitor_interval: float = MONITOR_INTERVAL,
    ):
        self.gpu_pause    = gpu_pause
        self.gpu_resume   = gpu_resume
        self.gpu_critical = gpu_critical
        self.cpu_pause    = cpu_pause
        self.cpu_resume   = cpu_resume
        self.cpu_critical = cpu_critical
        self.poll_interval    = poll_interval
        self.monitor_interval = monitor_interval

        self._nvml_ready    = False
        self._nvml_handle   = None
        self._wmi_lhm       = None   # LibreHardwareMonitor WMI
        self._wmi_acpi      = None   # MSAcpi WMI fallback
        self._psutil_ready  = False  # psutil sensors (Linux/macOS)
        self._load_fallback = False  # throttle por carga CPU

        # Estado compartido con el hilo de monitoreo
        self._abort_flag   = threading.Event()
        self._pause_event  = threading.Event()  # set = hay que pausar
        self._monitor_thread: threading.Thread | None = None
        self._monitor_active = False

        # Contador de lecturas de alta carga para el fallback
        self._high_load_streak = 0

        self._init_nvml()
        self._init_cpu_sensors()

    # ── Inicialización ─────────────────────────────────────────────────────

    def _init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._nvml_ready  = True
            logger.debug("ThermalGuard: nvidia-ml-py inicializado ✅")
        except Exception as e:
            logger.warning(f"ThermalGuard: nvidia-ml-py no disponible ({e}) — sin monitoreo GPU")

    def _init_cpu_sensors(self) -> None:
        import platform
        if platform.system() == "Windows":
            self._init_wmi_lhm()
            if not (self._wmi_lhm or self._wmi_acpi):
                self._init_load_fallback()
        else:
            self._init_psutil_sensors()
            if not self._psutil_ready:
                self._init_load_fallback()

    def _init_wmi_lhm(self) -> None:
        """
        LibreHardwareMonitor expone sensores detallados via WMI.
        Es la fuente más confiable en Windows si LHM está corriendo.
        """
        try:
            import wmi
            w = wmi.WMI(namespace="root/LibreHardwareMonitor")
            sensors = w.Sensor()
            cpu_temps = [s for s in sensors if s.SensorType == "Temperature" and "CPU" in s.Name]
            if cpu_temps:
                self._wmi_lhm = w
                logger.info("ThermalGuard: LibreHardwareMonitor WMI disponible ✅")
                return
        except Exception:
            pass
        # LHM no disponible — intentar ACPI
        self._init_wmi_acpi()

    def _init_wmi_acpi(self) -> None:
        """MSAcpi_ThermalZoneTemperature — disponible en la mayoría de Windows, valores menos precisos."""
        try:
            import wmi
            w = wmi.WMI(namespace="root/wmi")
            sensors = w.MSAcpi_ThermalZoneTemperature()
            if sensors:
                # Verificar que los valores son plausibles (entre 0°C y 120°C)
                temps = [(s.CurrentTemperature / 10.0) - 273.15 for s in sensors]
                if any(0 < t < 120 for t in temps):
                    self._wmi_acpi = w
                    logger.info("ThermalGuard: WMI ACPI temps disponible ✅")
                    return
            logger.warning("ThermalGuard: WMI ACPI devuelve valores no plausibles — descartado")
        except Exception as e:
            logger.warning(f"ThermalGuard: WMI ACPI no disponible ({e})")

    def _init_psutil_sensors(self) -> None:
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                self._psutil_ready = True
                logger.info("ThermalGuard: psutil sensors disponible ✅")
            else:
                logger.warning("ThermalGuard: psutil no reporta temperaturas en este OS")
        except Exception as e:
            logger.warning(f"ThermalGuard: psutil no disponible ({e})")

    def _init_load_fallback(self) -> None:
        """
        Cuando no hay ningún sensor de temperatura CPU disponible, usamos % de carga
        como proxy conservador: si la CPU está al 85%+ por 3 lecturas seguidas, pausamos.
        """
        try:
            import psutil
            psutil.cpu_percent(interval=0.1)  # primera llamada descartada (calibración)
            self._load_fallback = True
            logger.warning(
                "ThermalGuard: ⚠️  Sin sensor de temperatura CPU — usando carga CPU como proxy. "
                f"Pausará si CPU > {CPU_LOAD_PAUSE_PCT}% por {CPU_LOAD_PAUSE_COUNT} lecturas."
            )
        except Exception as e:
            logger.error(f"ThermalGuard: psutil no disponible para fallback de carga ({e})")

    # ── Lectura de temperaturas ────────────────────────────────────────────

    def _read_gpu_temp(self) -> float | None:
        if not self._nvml_ready:
            return None
        try:
            import pynvml
            return float(pynvml.nvmlDeviceGetTemperature(
                self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU
            ))
        except Exception:
            return None

    def _read_cpu_temp(self) -> float | None:
        import platform
        if platform.system() == "Windows":
            if self._wmi_lhm:
                return self._read_cpu_temp_lhm()
            if self._wmi_acpi:
                return self._read_cpu_temp_acpi()
            return None
        if self._psutil_ready:
            return self._read_cpu_temp_psutil()
        return None

    def _read_cpu_temp_lhm(self) -> float | None:
        """Lee temperatura CPU via LibreHardwareMonitor WMI."""
        try:
            sensors = self._wmi_lhm.Sensor()
            cpu_temps = [
                float(s.Value) for s in sensors
                if s.SensorType == "Temperature" and "CPU" in s.Name and s.Value is not None
            ]
            if not cpu_temps:
                return None
            return max(cpu_temps)
        except Exception:
            return None

    def _read_cpu_temp_acpi(self) -> float | None:
        """Lee temperatura CPU via MSAcpi WMI (kelvin × 10 → celsius)."""
        try:
            sensors = self._wmi_acpi.MSAcpi_ThermalZoneTemperature()
            if not sensors:
                return None
            temps_c = [(s.CurrentTemperature / 10.0) - 273.15 for s in sensors]
            # Filtrar valores no plausibles (sensor devuelve 0 o valores absurdos en algunos BIOS)
            plausible = [t for t in temps_c if 0 < t < 120]
            return max(plausible) if plausible else None
        except Exception:
            return None

    def _read_cpu_temp_psutil(self) -> float | None:
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if key in temps and temps[key]:
                    return max(e.current for e in temps[key])
            for entries in temps.values():
                if entries:
                    return max(e.current for e in entries)
        except Exception:
            pass
        return None

    def _read_cpu_load(self) -> float | None:
        if not self._load_fallback:
            return None
        try:
            import psutil
            return psutil.cpu_percent(interval=None)
        except Exception:
            return None

    def status(self) -> ThermalStatus:
        gpu_temp = self._read_gpu_temp()
        cpu_temp = self._read_cpu_temp()
        cpu_load = self._read_cpu_load()

        # Determinar pause por carga cuando no hay sensor de temperatura
        if cpu_temp is None and cpu_load is not None:
            if cpu_load >= CPU_LOAD_PAUSE_PCT:
                self._high_load_streak += 1
            else:
                self._high_load_streak = 0
            load_pause = self._high_load_streak >= CPU_LOAD_PAUSE_COUNT
        else:
            load_pause = False

        gpu_paused   = gpu_temp is not None and gpu_temp >= self.gpu_pause
        cpu_paused   = (cpu_temp is not None and cpu_temp >= self.cpu_pause) or load_pause
        gpu_critical = gpu_temp is not None and gpu_temp >= self.gpu_critical
        cpu_critical = cpu_temp is not None and cpu_temp >= self.cpu_critical

        return ThermalStatus(
            gpu_temp=gpu_temp,
            cpu_temp=cpu_temp,
            cpu_load=cpu_load,
            gpu_paused=gpu_paused,
            cpu_paused=cpu_paused,
            gpu_critical=gpu_critical,
            cpu_critical=cpu_critical,
        )

    # ── Hilo de monitoreo en background ───────────────────────────────────

    def start_background_monitor(self) -> None:
        """
        Inicia un hilo daemon que monitorea temperaturas continuamente.
        Si detecta temperatura crítica, activa _abort_flag.
        Si detecta temperatura de pausa, activa _pause_event.
        """
        if self._monitor_active:
            return
        self._abort_flag.clear()
        self._pause_event.clear()
        self._monitor_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="thermal-monitor"
        )
        self._monitor_thread.start()
        logger.debug("ThermalGuard: hilo de monitoreo iniciado")

    def stop_background_monitor(self) -> None:
        """Detiene el hilo de monitoreo en background."""
        self._monitor_active = False
        self._pause_event.clear()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.debug("ThermalGuard: hilo de monitoreo detenido")

    def _monitor_loop(self) -> None:
        while self._monitor_active:
            try:
                st = self.status()

                if st.is_critical:
                    reason = []
                    if st.gpu_critical:
                        reason.append(f"GPU {st.gpu_temp:.0f}°C >= {self.gpu_critical}°C CRÍTICO")
                    if st.cpu_critical:
                        reason.append(f"CPU {st.cpu_temp:.0f}°C >= {self.cpu_critical}°C CRÍTICO")
                    logger.critical(f"🔥 TEMPERATURA CRÍTICA: {', '.join(reason)} — ABORTANDO")
                    self._abort_flag.set()
                    self._monitor_active = False
                    return

                if st.should_pause:
                    self._pause_event.set()
                    logger.warning(f"🌡️  Monitor background: pausando — {st}")
                else:
                    if self._pause_event.is_set():
                        logger.info(f"✅ Monitor background: temperaturas normales — {st}")
                    self._pause_event.clear()

            except Exception as e:
                logger.debug(f"ThermalGuard monitor error: {e}")

            time.sleep(self.monitor_interval)

    # ── Lógica principal ───────────────────────────────────────────────────

    def check_and_wait(self, step: int = 0, total: int = 0) -> None:
        """
        Llama esto en cada step del pipeline SD.
        - Si _abort_flag está activo (temperatura crítica detectada por el monitor), lanza ThermalAbortError.
        - Si la temperatura supera el umbral de pausa, bloquea el hilo hasta que enfríe.

        Args:
            step:  step actual (para logging)
            total: total de steps (para logging)
        """
        # Primero verificar aborto
        if self._abort_flag.is_set():
            raise ThermalAbortError("Generación abortada por temperatura crítica")

        st = self.status()
        step_info = f"step {step}/{total}" if total else f"step {step}"

        # Temperatura crítica en este mismo check
        if st.is_critical:
            self._abort_flag.set()
            raise ThermalAbortError(
                f"Temperatura crítica detectada en {step_info}: {st}"
            )

        if not st.should_pause:
            return

        if st.gpu_paused:
            logger.warning(
                f"🌡️  GPU {st.gpu_temp:.0f}°C >= {self.gpu_pause}°C — "
                f"pausando generación en {step_info}"
            )
        if st.cpu_paused:
            temp_str = f"{st.cpu_temp:.0f}°C" if st.cpu_temp is not None else f"carga {st.cpu_load:.0f}%"
            logger.warning(
                f"🌡️  CPU {temp_str} — pausando generación en {step_info}"
            )

        # Esperar hasta que GPU y CPU bajen a sus umbrales de reanudación
        while True:
            time.sleep(self.poll_interval)

            # Verificar aborto durante la espera
            if self._abort_flag.is_set():
                raise ThermalAbortError("Generación abortada por temperatura crítica durante pausa")

            st = self.status()

            if st.is_critical:
                self._abort_flag.set()
                raise ThermalAbortError(
                    f"Temperatura crítica alcanzada durante pausa en {step_info}: {st}"
                )

            gpu_ok = (st.gpu_temp is None) or (st.gpu_temp < self.gpu_resume)
            # Para CPU: si hay sensor, comparar temperatura; si es fallback de carga,
            # reanudar cuando la racha de alta carga se rompa
            if st.cpu_temp is not None:
                cpu_ok = st.cpu_temp < self.cpu_resume
            else:
                cpu_ok = self._high_load_streak < CPU_LOAD_PAUSE_COUNT

            logger.debug(f"🌡️  Esperando enfriar... {st}")

            if gpu_ok and cpu_ok:
                self._pause_event.clear()
                logger.info(f"✅ Temperaturas normales ({st}) — reanudando en {step_info}")
                return

    def check_and_wait_async_safe(self, step: int = 0, total: int = 0) -> None:
        """
        Alias de check_and_wait para uso en callbacks síncronos dentro de
        run_in_executor (no coroutine — bloquea el hilo del executor, no el event loop).
        """
        self.check_and_wait(step=step, total=total)

    def reset_abort(self) -> None:
        """Limpia el flag de aborto (usar solo para reintentos manuales)."""
        self._abort_flag.clear()

    def shutdown(self) -> None:
        """Detiene el monitor y libera recursos de pynvml."""
        self.stop_background_monitor()
        if self._nvml_ready:
            try:
                import pynvml
                pynvml.nvmlShutdown()
            except Exception:
                pass


# ── Singleton global ────────────────────────────────────────────────────────
_guard: ThermalGuard | None = None


def get_thermal_guard() -> ThermalGuard:
    """Retorna la instancia global (crea una si no existe)."""
    global _guard
    if _guard is None:
        _guard = ThermalGuard()
    return _guard
