# -*- coding: utf-8 -*-

import os
import yaml


DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~/.kimai'), 'config')


class Config(object):
    def __init__(self, values=None):
        self.values = {} if values is None else values

    def get(self, key: str, default=None):
        if key in self.values:
            return self.values[key]

        return default

    def set(self, key: str, value):
        self.values[key] = value

    def delete(self, key):
        del self.values[key]

    def __repr__(self):
        return self.values


def config_path():
    return os.environ.get('KIMAI_CONFIG_PATH', DEFAULT_CONFIG_PATH)


def load_config():
    """Loads the config values from the configured path and returns
    a config object."""
    if not os.path.exists(config_path()):
        conf = Config()
    else:
        with open(config_path(), 'r') as file:
            conf = Config(yaml.load(file))
    return conf


def flush_config(config: Config):
    """Write the contents of the given config to disk."""
    os.makedirs(os.path.dirname(config_path()), exist_ok=True)

    with open(DEFAULT_CONFIG_PATH, 'w') as outfile:
        yaml.dump(config.values, outfile, default_flow_style=False)


config = load_config()
