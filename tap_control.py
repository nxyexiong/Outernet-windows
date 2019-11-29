import winreg as reg
import win32file
import win32event
import winerror
import pywintypes
import threading
import time

from queue import Queue
from constants import REG_CONTROL_CLASS, TAP_COMPONENT_ID
from logger import LOGGER


def get_tuntap_ComponentId():
    with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, REG_CONTROL_CLASS) as adapters:
        try:
            for i in range(10000):
                key_name = reg.EnumKey(adapters, i)
                with reg.OpenKey(adapters, key_name) as adapter:
                    try:
                        component_id = reg.QueryValueEx(adapter, 'ComponentId')[0]
                        if component_id == TAP_COMPONENT_ID:
                            return reg.QueryValueEx(adapter, 'NetCfgInstanceId')[0]
                    except WindowsError:
                        pass
        except WindowsError:
            pass


def CTL_CODE(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method


def TAP_CONTROL_CODE(request, method):
    return CTL_CODE(34, request, method, 0)


TAP_IOCTL_SET_MEDIA_STATUS        = TAP_CONTROL_CODE( 6, 0)
TAP_IOCTL_CONFIG_TUN              = TAP_CONTROL_CODE(10, 0)


def open_tun_tap(ipv4_addr, ipv4_network, ipv4_netmask):
    '''
    \brief Open a TUN/TAP interface and switch it to TUN mode.

    \return The handler of the interface, which can be used for later
        read/write operations.
    '''

    LOGGER.debug("open_tun_tap")

    # retrieve the ComponentId from the TUN/TAP interface
    componentId = get_tuntap_ComponentId()

    # create a win32file for manipulating the TUN/TAP interface
    tuntap = win32file.CreateFile(
        r'\\.\Global\%s.tap' % componentId,
        win32file.GENERIC_READ    | win32file.GENERIC_WRITE,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_SYSTEM | win32file.FILE_FLAG_OVERLAPPED,
        None
    )

    # have Windows consider the interface now connected
    win32file.DeviceIoControl(
        tuntap,
        TAP_IOCTL_SET_MEDIA_STATUS,
        b'\x01\x00\x00\x00',
        1
    )

    # prepare the parameter passed to the TAP_IOCTL_CONFIG_TUN commmand.
    # This needs to be a 12-character long string representing
    # - the tun interface's IPv4 address (4 characters)
    # - the tun interface's IPv4 network address (4 characters)
    # - the tun interface's IPv4 network mask (4 characters)
    configTunParam = []
    configTunParam += ipv4_addr
    configTunParam += ipv4_network
    configTunParam += ipv4_netmask
    configTunParam = bytes(configTunParam)

    # switch to TUN mode (by default the interface runs in TAP mode)
    win32file.DeviceIoControl(
        tuntap,
        TAP_IOCTL_CONFIG_TUN,
        configTunParam,
        1
    )

    # return the handler of the TUN interface
    return tuntap


def close_tun_tap(tuntap):
    win32file.CloseHandle(tuntap)


class TAPControl:
    def __init__(self, tuntap):
        LOGGER.debug("TAPControl init")
        # store params
        self.tuntap = tuntap
        # local variables
        self.mtu = 1300
        self.overlappedRx = pywintypes.OVERLAPPED()
        self.overlappedRx.hEvent = win32event.CreateEvent(None, 0, 0, None)
        self.rxOffset = self.overlappedRx.Offset
        self.overlappedTx = pywintypes.OVERLAPPED()
        self.overlappedTx.hEvent = win32event.CreateEvent(None, 0, 0, None)
        self.txOffset = self.overlappedTx.Offset
        self.read_callback = None
        self.write_queue = Queue()
        self.timeout = 100  # 0.1s
        self.goOn = False

    def run(self):
        LOGGER.debug("TAPControl run")
        self.goOn = True
        self.read_thread = threading.Thread(target=self.handle_read)
        self.read_thread.start()
        self.write_thread = threading.Thread(target=self.handle_write)
        self.write_thread.start()

    def handle_read(self):
        LOGGER.debug("TAPControl handle_read")
        rxbuffer = win32file.AllocateReadBuffer(self.mtu)

        # read
        ret = None
        p = None
        data = None
        while self.goOn:
            try:
                # wait for data
                ret, p = win32file.ReadFile(self.tuntap, rxbuffer, self.overlappedRx)
                while win32event.WaitForSingleObject(self.overlappedRx.hEvent, self.timeout) == win32event.WAIT_TIMEOUT:
                    if not self.goOn:
                        return
                self.rxOffset = self.rxOffset + len(p)
                self.overlappedRx.Offset = self.rxOffset & 0xffffffff
                self.overlappedRx.OffsetHigh = self.rxOffset >> 32
                data = bytes(p.obj)
            except Exception:
                continue

            LOGGER.debug("TAPControl read packet %s" % data)

            send_data = None
            if data[0] & 0xf0 == 0x40:  # ipv4
                # get length
                total_length = 256 * data[2] + data[3]
                # ready to handle
                send_data = data[:total_length]
                data = data[total_length:]
            elif data[0] & 0xf0 == 0x60:  # todo: ipv6
                # get length
                total_length = 256 * data[4] + data[5] + 40
                # ready to handle
                data = data[total_length:]

            if send_data and self.read_callback:
                self.read_callback(send_data)

    def write(self, data):
        LOGGER.debug("TAPControl write packet %s" % data)
        if not self.goOn:
            return
        self.write_queue.put(data)

    def handle_write(self):
        while self.goOn:
            try:
                data = self.write_queue.get(timeout=0.001)
            except Exception:
                continue

            try:
                # write over tuntap interface
                win32file.WriteFile(self.tuntap, data, self.overlappedTx)
                while win32event.WaitForSingleObject(self.overlappedTx.hEvent, self.timeout) == win32event.WAIT_TIMEOUT:
                    if not self.goOn:
                        return
                self.txOffset = self.txOffset + len(data)
                self.overlappedTx.Offset = self.txOffset & 0xffffffff
                self.overlappedTx.OffsetHigh = self.txOffset >> 32
            except Exception:
                continue

    def close(self):
        LOGGER.debug("TAPControl close")
        self.goOn = False
        while self.read_thread.is_alive():
            time.sleep(0.1)
        while self.write_thread.is_alive():
            time.sleep(0.1)
