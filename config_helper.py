import yaml

CONFIG_FILE = 'config.yaml'


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
