import pytest

import os
import subprocess
import polling2
import json
import requests
import base64
import time

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

def run_openwrt_shell_command(command, *arg):
    # Add double quotes
    command = "\"" + command + "\""

    # Build argument array
    arguments = "["
    for val in arg:
        arguments += "\"" + val + "\","
    arguments = arguments[:-1] # Remove the last ","
    arguments += "]"

    # Call qemu guest tools function 'guest-exec'. This is only working if OpenWrt is booted and the qemu guest tools are running
    process = subprocess.run(['docker','exec','openwrt','sh','-c',r"""echo -ne '{"execute":"guest-exec", "arguments": { "path": """ + command + ", \"arg\":" + arguments + r""","capture-output": true}}' | nc -w 1 -U /run/qga.sock"""], 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, 
                         universal_newlines=True)
    
    if process.returncode != 0:
        return None
    
    if process.stdout == "":
        return None
    
    # Assume json here, parse it
    ret = json.loads(process.stdout)

    if 'return' not in ret:
        return None
    
    if 'pid' not in ret['return']:
        return None

    pid = ret['return']['pid']

    # Get stdout of process
    time.sleep(5) # Give command 5 seconds time to respond. It would be better to implement a real timeout here but I need to got he bed :-(
    # Call qemu guest tools function 'guest-exec-status'. This is only working if OpenWrt is booted and the qemu guest tools are running
    process = subprocess.run(['docker','exec','openwrt','sh','-c',r"""echo -ne '{"execute":"guest-exec-status", "arguments": { "pid": """ + str(pid) + r"""}}' | nc -w 1 -U /run/qga.sock"""], 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, 
                         universal_newlines=True)
    
    if process.returncode != 0:
        return None
    
    if process.stdout == "":
        return None

    # Assume json here, parse it
    ret = json.loads(process.stdout)
    data = ret['return']

    # decode output
    if 'err-data' in data:
        data['err-data'] = base64.b64decode(data['err-data']).decode()

    if 'out-data' in data:
        data['out-data'] = base64.b64decode(data['out-data']).decode()

    return data

def get_openwrt_info():
    # Call qemu guest tools function 'guest-get-osinfo'. This is only working if OpenWrt is booted and the qemu guest tools are running
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

def is_openwrt_booted():
    service_status = get_openwrt_info()

    if service_status != None:
        return True
    else:
        return False


# ************************ Tests ************************

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


def test_openwrt_booted(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=90.0, pause=1, check=lambda: is_openwrt_booted()
    )

    info = get_openwrt_info()
    print(info)

    assert 'OpenWrt' == info['name']


def test_openwrt_lan_veth_pair(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=90.0, pause=1, check=lambda: is_openwrt_booted()
    )
    
    try:
        response = polling2.poll(lambda: os.system("ping -c 1 172.31.1.1") == 0, step=1, timeout=90)
    except polling2.TimeoutException:
        assert False
    
    pass


def test_openwrt_wan_host(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=90.0, pause=1, check=lambda: is_openwrt_booted()
    )
    
    # For some reason ping is not working at github actions, so use nslookup to test internet connection
    response = run_openwrt_shell_command("nslookup", "google.com")
    print(response)
    
    assert response['exitcode'] == 0


def test_openwrt_luci_forwarding(docker_ip, docker_services):
    docker_services.wait_until_responsive(
        timeout=90.0, pause=1, check=lambda: is_openwrt_booted()
    )
    
    # Double check if caddy is still running
    assert get_service_status('caddy') == 'RUNNING'

    response = requests.get("http://localhost:9000")
    
    assert ('LuCI - Lua Configuration Interface' in response.content.decode()) == True
