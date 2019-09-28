import netifaces
import winreg
import socket

from constants import REG_CONTROL_CLASS, REG_CONTROL_NETWORK, TAP_COMPONENT_ID


def get_iface_name(iface):
    iface_name = None
    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    reg_key = winreg.OpenKey(reg, REG_CONTROL_NETWORK)
    try:
        reg_subkey = winreg.OpenKey(reg_key, iface + r'\Connection')
        iface_name = winreg.QueryValueEx(reg_subkey, 'Name')[0]
    except FileNotFoundError:
        pass
    return iface_name


def get_default_iface():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('8.8.8.8', 80))
    addr = sock.getsockname()[0]

    iface = None
    for item in netifaces.interfaces():
        ifaddr = netifaces.ifaddresses(item)
        if netifaces.AF_INET not in ifaddr:
            continue
        cur_addr = netifaces.ifaddresses(item)[netifaces.AF_INET][0]['addr']
        if cur_addr == addr:
            iface = item
            break
    return iface


def get_tap_iface():
    iface = None
    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    reg_key = winreg.OpenKey(reg, REG_CONTROL_CLASS)
    try:
        for i in range(10000):
            key_name = winreg.EnumKey(reg_key, i)
            reg_subkey = winreg.OpenKey(reg_key, key_name)
            componentId = winreg.QueryValueEx(reg_subkey, 'ComponentId')[0]
            if componentId == TAP_COMPONENT_ID:
                iface = winreg.QueryValueEx(reg_subkey, 'NetCfgInstanceId')[0]
                break
    except Exception:
        pass
    return iface


def get_iface_gateway_ipv4(iface):
    gateways = netifaces.gateways()[netifaces.AF_INET]
    for item in gateways:
        if item[1] == iface:
            return item[0]
    return None


if __name__ == "__main__":
    # test
    print(get_default_iface())
    print(get_tap_iface())
    print(get_iface_name(get_default_iface()))
    print(get_iface_name(get_tap_iface()))
    print(get_iface_gateway_ipv4(get_default_iface()))
