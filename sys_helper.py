import os
import sys
import subprocess

from iface_helper import get_default_iface, get_iface_gateway_ipv4, get_iface_name, get_tap_iface

NET_CONFIG_FILE = 'network_config.dat'


def execute(cmd):
    CREATE_NO_WINDOW = 0x08000000
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)


def execute_with_shell(cmd):
    CREATE_NO_WINDOW = 0x08000000
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW, shell=True)


class SysHelper:
    def __init__(self):
        self.tap_ifname = get_iface_name(get_tap_iface())
        self.tap_ifname = '"' + self.tap_ifname + '"'
        self.default_ifname = get_iface_name(get_default_iface())
        self.default_ifname = '"' + self.default_ifname + '"'
        self.default_ifgateway = get_iface_gateway_ipv4(get_default_iface())

    def init_network(self, server_addr, ipv4_addr, ipv4_gateway, ipv4_network, ipv4_netmask):
        ipv4_addr = '.'.join([str(item) for item in ipv4_addr])
        ipv4_gateway = '.'.join([str(item) for item in ipv4_gateway])
        ipv4_network = '.'.join([str(item) for item in ipv4_network])
        ipv4_netmask = '.'.join([str(item) for item in ipv4_netmask])

        # save network config
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute_with_shell("netsh interface dump > %s\\%s" % (dirname, NET_CONFIG_FILE))

        # delete metric=0
        execute("route delete 0.0.0.0 metric 25")
        execute("route delete %s metric 25" % (server_addr,))

        # setup interface
        execute("netsh interface ip set address %s static %s %s" % (self.tap_ifname, ipv4_addr, ipv4_netmask))
        execute("netsh interface ipv4 add address name=%s address=%s mask=%s" % (self.tap_ifname, ipv4_addr, ipv4_netmask))
        execute("netsh interface ipv4 set interface interface=%s forwarding=enable metric=0 mtu=1300" % (self.tap_ifname,))

        # add route table
        execute("netsh interface ipv4 add route 0.0.0.0/0 %s %s metric=0" % (self.tap_ifname, ipv4_gateway,))

        # add server address
        execute("netsh interface ipv4 add route %s/32 %s %s metric=0" % (server_addr, self.default_ifname, self.default_ifgateway))

        # setup dns server
        execute("netsh interface ipv4 set dnsserver %s address=8.8.8.8 index=0" % (self.tap_ifname,))
        execute("netsh interface ipv4 add dnsserver %s address=8.8.4.4 index=2" % (self.tap_ifname,))

    def uninit_network(self, server_addr):
        # recover interface metric
        execute("netsh interface ipv4 set interface interface=%s metric=256" % (self.tap_ifname,))

        # delete server address
        execute("netsh interface ipv4 delete route %s/32 %s" % (server_addr, self.default_ifname))

        # delete tap route
        execute("netsh interface ipv4 delete route 0.0.0.0/0 %s" % (self.tap_ifname,))

        # restore network config
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("netsh exec %s\\%s" % (dirname, NET_CONFIG_FILE))

    def install_tap():
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("%s\\tap\\tapinstall.exe install %s\\tap\\OemVista.inf tap0901" % (dirname, dirname))

    def uninstall_tap():
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("%s\\tap\\tapinstall.exe remove tap0901" % (dirname,))

    def fix_netsh():
        dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        execute("netsh exec %s\\%s" % (dirname, NET_CONFIG_FILE))
        execute("netsh winsock reset")

    def restart_pc():
        execute("shutdown /r")
