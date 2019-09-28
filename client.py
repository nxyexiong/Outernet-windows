import threading
import socket
import select
import time

from cipher import AESCipher


class Client:

    def __init__(self, host, port, identification, secret, recv_callback, handshake_callback):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.server_addr = (host, port)
        self.recv_cb = recv_callback
        self.handshake_cb = handshake_callback
        self.cipher = AESCipher(secret)
        self.identification = identification
        self.running = False

    def run(self):
        self.running = True
        self.handshake_thread = threading.Thread(target=self.handle_handshake)
        self.handshake_thread.start()

    def start_vpn(self):
        self.running = True
        self.recv_thread = threading.Thread(target=self.handle_recv)
        self.recv_thread.start()

    def stop(self):
        self.running = False
        if self.handshake_thread is not None:
            while self.handshake_thread.is_alive():
                time.sleep(1)
        if self.recv_thread is not None:
            while self.recv_thread.is_alive():
                time.sleep(1)
        self.sock.close()

    def send(self, data):
        self.sock.sendto(self.wrap_data(data), self.server_addr)

    def handle_handshake(self):
        send_data = b'\x01' + self.identification
        while self.running:
            print("sending handshake...")
            self.sock.sendto(self.wrap_data(send_data), self.server_addr)
            try:
                self.sock.settimeout(5)
                data, _ = self.sock.recvfrom(2048)
                self.sock.settimeout(None)
            except socket.timeout:
                continue
            data = self.unwrap_data(data)
            if len(data) != 11 or data[0] != 0x01:
                continue
            tun_ip_raw = data[1:5]
            dst_ip_raw = data[5:9]
            port = data[9] * 256 + data[10]
            self.server_addr = (self.server_addr[0], port)
            self.handshake_cb(tun_ip_raw, dst_ip_raw)
            self.start_vpn()
            break

    def handle_recv(self):
        while self.running:
            readable, _, _ = select.select([self.sock, ], [], [], 1)
            if not readable:
                continue
            data, _ = self.sock.recvfrom(2048)
            data = self.unwrap_data(data)
            self.recv_cb(data)

    def wrap_data(self, data):
        data = self.cipher.encrypt(data)
        return data

    def unwrap_data(self, data):
        data = self.cipher.decrypt(data)
        return data
