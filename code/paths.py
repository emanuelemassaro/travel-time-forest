"""Input and output locations, read from config.yaml at the package root."""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "config.yaml")) as _f:
    _cfg = yaml.safe_load(_f)


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


INPUT_DIR = _abs(os.environ.get("TTF_INPUT_DIR") or _cfg["input_dir"])
DERIVED_DIR = _abs(_cfg["derived_dir"])
FIG_DIR = _abs(_cfg["figures_dir"])


def inp(key):
    """Path of an input dataset: key in config.yaml 'package_inputs' (shipped) or 'inputs' (in input_dir)."""
    if key in _cfg.get("package_inputs", {}):
        return _abs(_cfg["package_inputs"][key])
    return os.path.join(INPUT_DIR, _cfg["inputs"][key])


def der(name):
    """Path of a derived file in derived_dir (folders are created when missing)."""
    p = os.path.join(DERIVED_DIR, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def fig(name):
    """Path of a figure in figures_dir."""
    os.makedirs(FIG_DIR, exist_ok=True)
    return os.path.join(FIG_DIR, name)
