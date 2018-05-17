import os
import errno
import yaml


CONFIG_FOLDER = os.path.expanduser('~/.kimai')
CONFIG_PATH = os.path.join(CONFIG_FOLDER, 'config')


def _get_config():
    if not os.path.exists(CONFIG_PATH):
        return {}

    with open(CONFIG_PATH, 'r') as file:
        return yaml.load(file)


def write(attributes):
    """Replaces the existing config with the provided attributes."""
    try:
        os.makedirs(CONFIG_FOLDER)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    with open(CONFIG_PATH, 'w') as outfile:
        yaml.dump(attributes, outfile, default_flow_style=False)


def set(key, value):
    """Sets a single value in the config, overriding it if it
    already existed."""
    config = _get_config()
    config[key] = value
    write(config)


def merge(attributes):
    """Merges the existing config with the provided attributes
    overriding any values that already exist."""
    config = _get_config()
    write({**config, **attributes})


def get(key, default=None):
    """Retrieves a value from the config, returning the default
    if the key does not exist"""
    config = _get_config()

    if key not in config:
        return default

    return config[key]
