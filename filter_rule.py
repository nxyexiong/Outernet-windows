import threading
import time
import psutil


REFRESH_INTERVAL = 0.1

class FilterRule:
    def __init__(self, sys_helper):
        self.sys_helper = sys_helper
        self.mode = None
        self.procs = None
        self.ips = None
        self.iptable_cache = set()
        self.running = False

    # dont call this while running
    def set_filter(self, mode, proclist, iplist):
        if self.running:
            return
        self.mode = mode
        self.procs = proclist
        self.ips = iplist

    def run(self):
        self.running = True
        self.filter_thread = threading.Thread(target=self.handle_filter)
        self.filter_thread.start()

    def stop(self):
        self.running = False
        while self.filter_thread.is_alive():
            time.sleep(0.1)
        self.clear_iptable()

    def handle_filter(self):
        while self.running:
            new_ips = set() # ips to replace self.iptable_cache

            # handle procs
            for proc_name in self.procs:
                proc = self.find_process_by_name(proc_name)
                if proc is None:
                    continue
                connections = proc.connections()
                for conn in connections:
                    if conn.family == 2 and conn.raddr: # AF_INET and has remote addr
                        new_ips.add(conn.raddr.ip + '/32')

            # handle ips
            new_ips |= set(self.ips)
            need_to_del = self.iptable_cache - new_ips
            need_to_add = new_ips - self.iptable_cache
            self.iptable_cache = new_ips

            # iptable
            if self.mode == 0: # blacklist mode
                for item in need_to_add:
                    self.sys_helper.add_route_black(item)
                for item in need_to_del:
                    self.sys_helper.del_route_black(item)
            else: # whitelist mode
                for item in need_to_add:
                    self.sys_helper.add_route_white(item)
                for item in need_to_del:
                    self.sys_helper.del_route_white(item)

            # sleep
            time.sleep(REFRESH_INTERVAL)

    def clear_iptable(self):
        if self.mode == 0:
            for item in self.iptable_cache:
                self.sys_helper.del_route_black(item)
        else:
            for item in self.iptable_cache:
                self.sys_helper.del_route_white(item)

    def find_process_by_name(self, name):
        for item in psutil.process_iter():
            if item.name() == name:
                return item
        return None


if __name__ == "__main__":
    from sys_helper import SysHelper
    sys_hp = SysHelper()
    filter_rule = FilterRule(sys_hp)
    filter_rule.set_filter(0, ['QQ.exe', 'chrome.exe'], ['1.2.3.4/32'])
    filter_rule.run()
    time.sleep(5)
    filter_rule.stop()
