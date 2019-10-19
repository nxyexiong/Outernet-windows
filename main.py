import time
import ctypes
import hashlib
import threading
import socket

from sys_helper import SysHelper
from tap_control import open_tun_tap, close_tun_tap, TAPControl
from iface_helper import get_tap_iface
from config_helper import load_traffic, save_traffic, load_filter
from client import Client
from cipher import Chacha20Cipher
from filter_rule import FilterRule


FILTER_BLACK = 0
FILTER_WHITE = 1


class MainControl:
    def __init__(self):
        self.tuntap = None
        self.client = None
        self.tap_control = None
        self.sys_hper = SysHelper()
        self.running = False
        # callbacks
        self.connect_cb = None
        self.tuntapset_cb = None
        self.tapcontrolset_cb = None
        self.stop_cb = None
        # traffic init
        traffic = load_traffic()
        if traffic:
            self.rx_total_init = traffic.get('rx', 0)
            self.tx_total_init = traffic.get('tx', 0)
        else:
            self.rx_total_init = 0
            self.tx_total_init = 0
        # filter
        self.filter = FilterRule(self.sys_hper)

    def set_connect_cb(self, callback):
        self.connect_cb = callback

    def set_tuntapset_cb(self, callback):
        self.tuntapset_cb = callback

    def set_tapcontrolset_cb(self, callback):
        self.tapcontrolset_cb = callback

    def set_stop_cb(self, callback):
        self.stop_cb = callback

    def get_rx_rate(self):
        if self.client:
            return self.client.rx_rate
        else:
            return 0

    def get_tx_rate(self):
        if self.client:
            return self.client.tx_rate
        else:
            return 0

    def get_rx_total(self):
        if self.client:
            self.rx_total_init = self.client.rx_total
            return self.client.rx_total
        else:
            return self.rx_total_init

    def get_tx_total(self):
        if self.client:
            self.tx_total_init = self.client.tx_total
            return self.client.tx_total
        else:
            return self.tx_total_init

    def clear_traffic(self):
        if self.client:
            self.client.clear_traffic()
        else:
            traffic = {}
            traffic['rx'] = 0
            traffic['tx'] = 0
            save_traffic(traffic)
        self.rx_total_init = 0
        self.tx_total_init = 0

    def query_traffic_remain(self, server_ip, server_port, username, secret):
        secret = secret.encode('utf-8')
        cipher = Chacha20Cipher(secret)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        identification_raw = username.encode('utf-8')
        identification = hashlib.sha256(identification_raw).digest()
        send_data = b'\x02' + identification
        sock.sendto(cipher.encrypt(send_data), (server_ip, server_port))
        try:
            sock.settimeout(5)
            data, _ = sock.recvfrom(2048)
            data = cipher.decrypt(data)
            traffic_remain = int.from_bytes(data[1:5], 'big')
            return traffic_remain
        except Exception:
            return None

    def run(self, server_ip, server_port, username, secret):
        self.server_ip = server_ip
        self.server_port = server_port
        identification_raw = username.encode('utf-8')
        self.identification = hashlib.sha256(identification_raw).digest()
        self.secret = secret.encode('utf-8')
        self.running = True
        self.main_thread = threading.Thread(target=self.loop)
        self.main_thread.start()

    def stop(self):
        self.stop_thread = threading.Thread(target=self.handle_stop)
        self.stop_thread.start()

    def loop(self):
        self.client = Client(self.server_ip, self.server_port, self.identification, self.secret, self.client_recv_cb, self.client_handshake_cb)
        self.client.run()

        # waiting for client connecting to server
        while not self.tuntap:
            time.sleep(0.1)
            if not self.running:
                return
        if self.tuntapset_cb is not None:
            self.tuntapset_cb()

        print("start tap control")
        self.tap_control = TAPControl(self.tuntap)
        self.tap_control.read_callback = self.tap_read_cb
        self.tap_control.run()
        if self.tapcontrolset_cb is not None:
            self.tapcontrolset_cb()

    def handle_stop(self):
        print("terminating...")
        self.running = False
        self.filter.stop()
        if self.tap_control is not None:
            self.tap_control.close()
        if self.client is not None:
            self.client.stop()
        if self.tuntap is not None:
            close_tun_tap(self.tuntap)
        self.tap_control = None
        self.tuntap = None
        self.client = None
        self.sys_hper.uninit_network(self.server_ip)
        print("terminated")
        if self.stop_cb is not None:
            self.stop_cb()

    def client_handshake_cb(self, gateway_ip, interface_ip):
        if self.connect_cb is not None:
            self.connect_cb()
        ipv4_addr = list(interface_ip)
        ipv4_gateway = list(gateway_ip)
        ipv4_network = [10, 0, 0, 0]
        ipv4_netmask = [255, 255, 255, 0]
        print("handshaked success with interface ip:", ipv4_addr, "gateway ip:", ipv4_gateway)

        # preload filter
        ffilter = load_filter()
        filter_type = FILTER_BLACK
        filter_procs = []
        filter_ips = []
        if ffilter is not None:
            ftype = ffilter.get('type')
            procs = ffilter.get('procs')
            ips = ffilter.get('ips')
            if ftype == 'Blacklist':
                filter_type = FILTER_BLACK
            elif ftype == 'Whitelist':
                filter_type = FILTER_WHITE
            filter_procs = procs.strip().split('\n')
            filter_ips = ips.strip().split('\n')

        self.sys_hper.init_network(self.server_ip, ipv4_addr, ipv4_gateway, ipv4_network, ipv4_netmask, filter_type)
        self.tuntap = open_tun_tap(ipv4_addr, ipv4_network, ipv4_netmask)

        # start filter
        self.filter.set_filter(filter_type, filter_procs, filter_ips)
        self.filter.run()

    def client_recv_cb(self, data):
        self.tap_control.write(data)

    def tap_read_cb(self, data):
        self.client.send(data)


if __name__ == '__main__':
    # check privilige
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print('please run this as administrator')
        time.sleep(3)
        exit(1)

    # check tap
    while not get_tap_iface():
        print('not tap installed, installing...')
        SysHelper.install_tap()
        time.sleep(1)

    # enter ip
    print("please enter your server ip:")
    server_ip = str(input())

    # enter port
    print("please enter your server port:")
    server_port = int(input())

    # enter id
    print("please enter your identification:")
    username = str(input())

    # enter secret
    print("please enter your secret:")
    secret = str(input())

    # run
    main_control = MainControl()
    main_control.run(server_ip, server_port, username, secret)

    # listening keyboard interupt
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            main_control.stop()
            break
