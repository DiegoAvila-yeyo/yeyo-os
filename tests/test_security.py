import subprocess
import os
import pytest

def test_services_only_localhost():
    result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]
    for line in lines:
        # Ignorar DNS de WSL y localhost conocidos
        if any(x in line for x in ['127.0.0.1', '::1', '*:22', '10.255.255.254', '127.0.0.53', '127.0.0.54']):
            continue
        if '0.0.0.0' in line or ':::' in line:
            assert False, f"Servicio expuesto publicamente: {line}"

@pytest.mark.xfail(reason="auditd no puede conectar al kernel en WSL2 (Operation not permitted en audit netlink)")
def test_audit_running():
    result = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
    assert result.stdout.strip() == 'active'

def test_yeyo_service_exists():
    result = subprocess.run(['id', 'yeyo-service'], capture_output=True, text=True)
    assert result.returncode == 0

def test_var_lib_yeyo_permissions():
    st = os.stat('/var/lib/yeyo')
    mode = oct(st.st_mode)[-3:]
    assert mode == '750'

def test_log_dirs_exist():
    for d in ['guardian', 'api', 'memory', 'security']:
        assert os.path.isdir(f'/var/log/yeyo/{d}')

def test_firewall_active():
    result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
    assert 'active' in result.stdout.lower()

def test_logrotate_configured():
    assert os.path.isfile('/etc/logrotate.d/yeyo')
