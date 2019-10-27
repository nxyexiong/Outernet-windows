import threading
import socket
import select
import time

from cipher import Chacha20Cipher
from config_helper import load_traffic, save_traffic
from logger import LOGGER

TRAFFIC_SAVE_INTERVAL = 60


class Client:

    def __init__(self, host, port, identification, secret, recv_callback, handshake_callback):
        LOGGER.debug("Client init")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.server_addr = (host, port)
        self.recv_cb = recv_callback
        self.handshake_cb = handshake_callback
        self.cipher = Chacha20Cipher(secret)
        self.identification = identification
        self.running = False
        # traffic
        traffic = load_traffic()
        self.rx_rate = 0
        self.tx_rate = 0
        self.rx_tmp = 0
        self.tx_tmp = 0
        if traffic:
            self.rx_total = traffic.get('rx', 0)
            self.tx_total = traffic.get('tx', 0)
        else:
            self.rx_total = 0
            self.tx_total = 0

    def run(self):
        LOGGER.debug("Client run")
        self.running = True
        self.handshake_thread = threading.Thread(target=self.handle_handshake)
        self.handshake_thread.start()

    def start_vpn(self):
        LOGGER.debug("Client start_vpn")
        self.running = True
        self.recv_thread = threading.Thread(target=self.handle_recv)
        self.recv_thread.start()
        self.traffic_thread = threading.Thread(target=self.handle_traffic)
        self.traffic_thread.start()

    def stop(self):
        LOGGER.debug("Client stop")
        self.running = False
        if self.handshake_thread is not None:
            while self.handshake_thread.is_alive():
                time.sleep(0.1)
        if self.recv_thread is not None:
            while self.recv_thread.is_alive():
                time.sleep(0.1)
        if self.traffic_thread is not None:
            while self.traffic_thread.is_alive():
                time.sleep(0.1)
        self.sock.close()

    def send(self, data):
        LOGGER.debug("Client send data: %s" % data)
        send_data = self.wrap_data(data)
        self.tx_tmp += len(send_data)
        self.sock.sendto(send_data, self.server_addr)

    def handle_handshake(self):
        LOGGER.debug("Client handle_handshake")
        send_data = b'\x01' + self.identification
        while self.running:
            self.sock.sendto(self.wrap_data(send_data), self.server_addr)
            try:
                self.sock.settimeout(5)
                data, _ = self.sock.recvfrom(2048)
                self.sock.settimeout(None)
            except socket.timeout:
                LOGGER.warning("Client handshake timeout")
                continue
            data = self.unwrap_data(data)
            if len(data) != 11 or data[0] != 0x01:
                continue
            LOGGER.debug("Client handshake recved")
            tun_ip_raw = data[1:5]
            dst_ip_raw = data[5:9]
            port = data[9] * 256 + data[10]
            self.server_addr = (self.server_addr[0], port)
            self.handshake_cb(tun_ip_raw, dst_ip_raw)
            self.start_vpn()
            break

    def handle_recv(self):
        LOGGER.debug("Client handle_recv")
        while self.running:
            readable, _, _ = select.select([self.sock, ], [], [], 1)
            if not readable:
                continue
            data, _ = self.sock.recvfrom(2048)
            data = self.unwrap_data(data)
            LOGGER.debug("Client recv data: %s" % data)
            self.rx_tmp += len(data)
            self.recv_cb(data)

    def handle_traffic(self):
        LOGGER.debug("Client handle_traffic")
        tick = 0
        while self.running:
            self.rx_rate = self.rx_tmp
            self.tx_rate = self.tx_tmp
            self.rx_total += self.rx_tmp
            self.tx_total += self.tx_tmp
            self.rx_tmp = 0
            self.tx_tmp = 0

            if tick % TRAFFIC_SAVE_INTERVAL == 0:
                traffic = {}
                traffic['rx'] = self.rx_total
                traffic['tx'] = self.tx_total
                save_traffic(traffic)

            time.sleep(1)
            tick += 1

        # save on stop
        traffic = {}
        traffic['rx'] = self.rx_total
        traffic['tx'] = self.tx_total
        save_traffic(traffic)

    def clear_traffic(self):
        LOGGER.debug("Client clear_traffic")
        self.rx_total = 0
        self.tx_total = 0
        traffic = {}
        traffic['rx'] = self.rx_total
        traffic['tx'] = self.tx_total
        save_traffic(traffic)

    def wrap_data(self, data):
        data = self.cipher.encrypt(data)
        return data

    def unwrap_data(self, data):
        data = self.cipher.decrypt(data)
        return data
