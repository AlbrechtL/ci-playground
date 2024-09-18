import pytest

import os
import subprocess
import polling2
import json

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
    
def get_openwrt_info():
    # Get current service list from supervisor
    process = subprocess.run(['docker','exec','openwrt','sh','-c',r"""echo -ne '{"execute":"guest-get-osinfo"}' | nc -w 1 -U /run/qga.sock"""], 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, 
                         universal_newlines=True)
    
    if process.returncode != 0:
        return None
    
    if process.stdout == "":
        return None
    
    # Assume json here, parse it
    info = json.loads(process.stdout)

    if 'return' not in info:
        return None
    
    if 'name' not in info['return']:
        return None

    return info['return']

def is_openwrt_loaded():
    service_status = get_openwrt_info()

    if service_status != None:
        return True
    else:
        return False


# Tests

def test_basic_container_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_container_running()
    )
    return

def test_nginx_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_service_started('nginx')
    )
    
    assert get_service_status('nginx') == 'RUNNING'

def test_openwrt_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_service_started('openwrt')
    )
    
    assert get_service_status('openwrt') == 'RUNNING'

def test_caddy_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_service_started('caddy')
    )

    assert get_service_status('caddy') == 'RUNNING'

def test_script_server_start(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_service_started('script-server')
    )

    assert get_service_status('script-server') == 'RUNNING'

def test_openwrt_ping(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_service_started('openwrt')
    )
    
    assert get_service_status('openwrt') == 'RUNNING'

    response = polling2.poll(lambda: os.system("ping -c 1 172.31.1.1") == 0, step=1, timeout=90)
    
    assert response == True

def test_openwrt_loaded(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=90.0, pause=1, check=lambda: is_openwrt_loaded()
    )

    info = get_openwrt_info()
    print(info)

    assert 'OpenWrt' == info['name']