"""Entry point for the sample project."""

from utils import parse_config, validate, ConfigError


def run(path):
    """Load a config, validate it, and print a summary."""
    cfg = parse_config(path)
    if not validate(cfg):
        raise ConfigError("missing required keys")
    print(f"Loaded {cfg['name']} v{cfg['version']}")
    return cfg


if __name__ == "__main__":
    run("app.json")
