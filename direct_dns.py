import threading
import time

from queue import Queue
from logger import LOGGER
from dns_utils import re_resolve_dns


class DirectDNS:
    def __init__(self, filter_rule, packet_callback):
        LOGGER.debug("DirectDNS init")
        self.filter = filter_rule
        self.callback = packet_callback
        self.packet_queue = Queue()
        self.running = False

    def run(self):
        LOGGER.debug("DirectDNS run")
        self.running = True
        self.packet_thread = threading.Thread(target=self.handle_packet)
        self.packet_thread.start()

    def stop(self):
        LOGGER.debug("DirectDNS stop")
        self.running = False
        if self.packet_thread is not None:
            while self.packet_thread.is_alive():
                time.sleep(0.1)

    def resolve(self, packet):
        LOGGER.debug("DirectDNS resolve")
        self.packet_queue.put(packet)

    def handle_packet(self):
        LOGGER.debug("DirectDNS handle_packet")
        while self.running:
            try:
                packet = self.packet_queue.get(timeout=0.1)
            except Exception:
                continue

            packet, answers = re_resolve_dns(packet, [self.filter.default_dns_server])
            for key, value in answers.items():
                for item in value:
                    self.filter.hit_ip(item + '/32')

            self.callback(packet)
