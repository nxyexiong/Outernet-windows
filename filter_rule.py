import threading
import time
import re

FILTER_BLACK = 0
FILTER_WHITE = 1
IP_ROUTE_ALL = "0.0.0.0/0"


class FilterRule:
    def __init__(self, sys_helper):
        self.sys_helper = sys_helper
        self.mode = None
        self.domains = None
        self.ips = None
        self.iptable_cache = set()
        self.inited = False

    # dont call this while running
    def init_filter(self, mode, domainlist, iplist):
        if self.inited:
            return
        self.mode = mode
        self.domains = domainlist
        self.ips = iplist
        self.clear_iptable()

        if self.mode == FILTER_BLACK:
            self.sys_helper.add_route_white(IP_ROUTE_ALL)
            for item in self.ips:
                self.sys_helper.add_route_black(item)
                self.iptable_cache.add(item)
        elif self.mode == FILTER_WHITE:
            for item in self.ips:
                self.sys_helper.add_route_white(item)
                self.iptable_cache.add(item)

        self.inited = True

    def uninit_filter(self):
        if not self.inited:
            return
        self.inited = False

        if self.mode == FILTER_BLACK:
            self.sys_helper.del_route_white(IP_ROUTE_ALL)
        self.clear_iptable()
        self.domains = None
        self.ips = None
        self.mode = None

    def match_domain(self, domain):
        if not self.inited:
            return False
        for item in self.domains:
            if re.fullmatch(item, domain):
                return True

    def hit_ip(self, hitip):
        if not self.inited:
            return
        if hitip in self.iptable_cache:
            return
        if self.mode == FILTER_BLACK:
            self.sys_helper.add_route_black(hitip)
            self.iptable_cache.add(hitip)
        elif self.mode == FILTER_WHITE:
            self.sys_helper.add_route_white(hitip)
            self.iptable_cache.add(hitip)

    def clear_iptable(self):
        if self.mode == FILTER_BLACK:
            for item in self.iptable_cache:
                self.sys_helper.del_route_black(item)
        elif self.mode == FILTER_WHITE:
            for item in self.iptable_cache:
                self.sys_helper.del_route_white(item)
        self.iptable_cache.clear()