import yaml

CONFIG_FILE = 'config.yaml'
TRAFFIC_FILE = 'traffic.yaml'


def load_config():
    try:
        config = yaml.load(open(CONFIG_FILE))
        return config
    except Exception:
        print('missing config file or format incorrect')
        return None


def save_config(config):
    try:
        f = open(CONFIG_FILE, 'w+')
        yaml.dump(config, f)
        return True
    except Exception:
        print('error writing configuration')
        return False

def load_traffic():
    try:
        traffic = yaml.load(open(TRAFFIC_FILE))
        return traffic
    except Exception:
        print('missing traffic file or format incorrect')
        return None


def save_traffic(traffic):
    try:
        f = open(TRAFFIC_FILE, 'w+')
        yaml.dump(traffic, f)
        return True
    except Exception:
        print('error writing traffic')
        return False
