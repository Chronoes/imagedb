import json
import os
import os.path

def _get_path(raw_path):
    if os.path.isabs(raw_path):
        return raw_path

    return os.path.join(os.path.dirname(__file__), raw_path)

def load_config(path=None):
    path = _get_path(path or os.environ.get('CONFIG_PATH', 'config.json'))

    with open(path) as f:
        config = json.load(f)

    config['database']['path'] = _get_path(config['database']['path'])
    for key in config['groups']:
        config['groups'][key] = _get_path(config['groups'][key])

    return config
