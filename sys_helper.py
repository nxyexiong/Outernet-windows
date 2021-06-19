import os
import sys
import subprocess

from iface_helper import get_default_iface, get_iface_gateway_ipv4, get_iface_name, get_tap_iface
from logger import LOGGER


def execute(cmd):
    CREATE_NO_WINDOW = 0x08000000
    ret = subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)
    LOGGER.info("system execute '%s' ret: %d" % (cmd, ret))


class SysHelper:
    def __init__(self):
        self.tap_ifname = get_iface_name(get_tap_iface())
        self.tap_ifname = '"' + self.tap_ifname + '"'
        self.default_ifname = get_iface_name(get_default_iface())
        self.default_ifname = '"' + self.default_ifname + '"'
        self.default_ifgateway = get_iface_gateway_ipv4(get_default_iface())

        self.ipv4_addr = None
        self.ipv4_gateway = None
        self.ipv4_network = None
        self.ipv4_netmask = None

    def init_network(self, server_addr, ipv4_addr, ipv4_gateway, ipv4_network, ipv4_netmask):
        self.ipv4_addr = '.'.join([str(item) for item in ipv4_addr])
        self.ipv4_gateway = '.'.join([str(item) for item in ipv4_gateway])
        self.ipv4_network = '.'.join([str(item) for item in ipv4_network])
        self.ipv4_netmask = '.'.join([str(item) for item in ipv4_netmask])

        # set metric!=0
        execute("netsh interface ipv4 set route 0.0.0.0/0 %s metric=100 store=active" % (self.default_ifname))

        # setup interface
        execute("netsh interface ip set address %s static %s %s" % (self.tap_ifname, self.ipv4_addr, self.ipv4_netmask))
        execute("netsh interface ipv4 add address name=%s address=%s mask=%s" % (self.tap_ifname, self.ipv4_addr, self.ipv4_netmask))
        execute("netsh interface ipv4 set interface interface=%s forwarding=enable metric=0 mtu=1300" % (self.tap_ifname,))

        # add server address
        execute("netsh interface ipv4 add route %s/32 %s %s metric=0" % (server_addr, self.default_ifname, self.default_ifgateway))

        # setup dns server
        execute("netsh interface ipv4 set dns name=%s static 8.8.8.8" % (self.tap_ifname,))
        execute("netsh interface ipv4 set dns name=%s static 8.8.4.4 index=2" % (self.tap_ifname,))

    def uninit_network(self, server_addr):
        # recover interface metric
        execute("netsh interface ipv4 set interface interface=%s metric=256" % (self.tap_ifname,))

        # delete server address
        execute("netsh interface ipv4 delete route %s/32 %s" % (server_addr, self.default_ifname))

        self.ipv4_addr = None
        self.ipv4_gateway = None
        self.ipv4_network = None
        self.ipv4_netmask = None

    def add_route_white(self, ip):
        if self.ipv4_gateway is None:
            return
        execute("netsh interface ipv4 add route %s %s %s metric=0" % (ip, self.tap_ifname, self.ipv4_gateway,))

    def del_route_white(self, ip):
        if self.ipv4_gateway is None:
            return
        execute("netsh interface ipv4 delete route %s %s %s" % (ip, self.tap_ifname, self.ipv4_gateway,))

    def add_route_black(self, ip):
        execute("netsh interface ipv4 add route %s %s %s metric=0" % (ip, self.default_ifname, self.default_ifgateway,))

    def del_route_black(self, ip):
        execute("netsh interface ipv4 delete route %s %s %s" % (ip, self.default_ifname, self.default_ifgateway,))

    def install_tap():
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("%s\\tap\\tapinstall.exe install %s\\tap\\OemVista.inf tap0901" % (dirname, dirname))

    def uninstall_tap():
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("%s\\tap\\tapinstall.exe remove tap0901" % (dirname,))

    def fix_netsh():
        execute("netsh winsock reset")
        execute("route -f")

    def restart_pc():
        execute("shutdown /r /t 0")
