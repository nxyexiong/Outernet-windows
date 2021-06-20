CMD_UNKNOWN = 0x00
CMD_CLIENT_HANDSHAKE = 0x01
CMD_SERVER_HANDSHAKE = 0x02
CMD_CLIENT_DATA = 0x03
CMD_SERVER_DATA = 0x04


class Protocol:
    def __init__(self):
        self.cmd = CMD_UNKNOWN
        self.identification = b''  # 32 bytes user id
        self.tun_ip_raw = b''  # 4 bytes big endian
        self.dst_ip_raw = b''  # 4 bytes big endian
        self.data = b''

    def parse(self, data):
        parsed = 0
        if len(data) < 1:
            return parsed
        self.cmd = data[0]
        parsed += 1
        if self.cmd == CMD_CLIENT_HANDSHAKE:
            parsed += self.parse_client_handshake(data[1:])
        elif self.cmd == CMD_SERVER_HANDSHAKE:
            parsed += self.parse_server_handshake(data[1:])
        elif self.cmd == CMD_CLIENT_DATA:
            parsed += self.parse_client_data(data[1:])
        elif self.cmd == CMD_SERVER_DATA:
            parsed += self.parse_server_data(data[1:])
        return parsed

    def parse_client_handshake(self, data):
        if len(data) < 32:
            return 0
        self.identification = data[:32]
        return 32

    def parse_server_handshake(self, data):
        if len(data) < 8:
            return 0
        self.tun_ip_raw = data[:4]
        self.dst_ip_raw = data[4:8]
        return 8

    def parse_client_data(self, data):
        if len(data) < 32:
            return 0
        self.identification = data[:32]
        self.data = data[32:]
        return len(data)

    def parse_server_data(self, data):
        self.data = data
        return len(data)

    def get_bytes(self):
        data = bytes([self.cmd])
        if self.cmd == CMD_CLIENT_HANDSHAKE:
            data += self.get_bytes_client_handshake()
        elif self.cmd == CMD_SERVER_HANDSHAKE:
            data += self.get_bytes_server_handshake()
        elif self.cmd == CMD_CLIENT_DATA:
            data += self.get_bytes_client_data()
        elif self.cmd == CMD_SERVER_DATA:
            data += self.get_bytes_server_data()
        return data

    def get_bytes_client_handshake(self):
        return self.identification

    def get_bytes_server_handshake(self):
        return self.tun_ip_raw + self.dst_ip_raw

    def get_bytes_client_data(self):
        return self.identification + self.data

    def get_bytes_server_data(self):
        return self.data
