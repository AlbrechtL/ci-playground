import os
import subprocess
import pytest
import polling2

def is_container_running():
    # Get current service list from supervisor
    process = subprocess.run(['docker','exec','openwrt','supervisorctl','status'], 
                         stdout=subprocess.PIPE, 
                         universal_newlines=True)
    
    # Check if supervisord is running
    if process.returncode == 0 \
    or process.returncode == 3 : # Means a service has an issue
        return True
    else:
        return False

def get_service_status(service):
    # Get current service list from supervisor
    process = subprocess.run(['docker','exec','openwrt','supervisorctl','status'], 
                         stdout=subprocess.PIPE, 
                         universal_newlines=True)
    
    # Check if supervisord is running
    if process.returncode == 0 \
    or process.returncode == 3 : # Means a service has an issue
        # Extract list from supervisorctl output
        service_list = process.stdout.splitlines()

        # Filter for service
        service_status = [s for s in service_list if service in s][0].split()

        return service_status[1]
    else:
        return None

def is_service_started(service):
    service_status = get_service_status(service)

    if service_status != None:
        # Check if service is running or in other states
        if service_status == 'RUNNING' \
        or service_status == 'BACKOFF' \
        or service_status == 'EXITED' \
        or service_status == 'FATAL' \
        or service_status == 'UNKNOWN':
            return True
        else:
            return False
    else:
        return False
    
def test_basic_container_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_container_running()
    )
    return

def test_nginx_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_service_started('nginx')
    )
    
    assert get_service_status('nginx') == 'RUNNING'

def test_openwrt_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_service_started('openwrt')
    )
    
    assert get_service_status('openwrt') == 'RUNNING'

def test_caddy_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_service_started('caddy')
    )

    assert get_service_status('caddy') == 'RUNNING'

def test_script_server_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_service_started('script-server')
    )

    assert get_service_status('script-server') == 'RUNNING'

def test_openwrt_ping(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_service_started('openwrt')
    )
    
    assert get_service_status('openwrt') == 'RUNNING'

    response = polling2.poll(lambda: os.system("ping -c 1 172.31.1.1") == 0, step=1, timeout=90)
    
    assert response == True