import yaml

from logger import LOGGER

CONFIG_FILE = 'config.yaml'
TRAFFIC_FILE = 'traffic.yaml'
FILTER_FILE = 'filter.yaml'


def load_config():
    try:
        config = yaml.load(open(CONFIG_FILE))
        return config
    except Exception:
        LOGGER.warning('missing config file or format incorrect')
        return None


def save_config(config):
    try:
        f = open(CONFIG_FILE, 'w+')
        yaml.dump(config, f)
        return True
    except Exception:
        LOGGER.warning('error writing configuration')
        return False

def load_traffic():
    try:
        traffic = yaml.load(open(TRAFFIC_FILE))
        return traffic
    except Exception:
        LOGGER.warning('missing traffic file or format incorrect')
        return None


def save_traffic(traffic):
    try:
        f = open(TRAFFIC_FILE, 'w+')
        yaml.dump(traffic, f)
        return True
    except Exception:
        LOGGER.warning('error writing traffic')
        return False


def load_filter():
    try:
        ffilter = yaml.load(open(FILTER_FILE))
        return ffilter
    except Exception:
        LOGGER.warning('missing filter file or format incorrect')
        return None


def save_filter(ffilter):
    try:
        f = open(FILTER_FILE, 'w+')
        yaml.dump(ffilter, f)
        return True
    except Exception:
        LOGGER.warning('error writing filter file')
        return False
