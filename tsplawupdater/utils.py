"""Utility functions.
"""

import os
import shutil
import pathlib

import appdirs
import toml

from tsplawupdater import info


def get_config_from_toml(config_path):
    """Get configuration from TOML file.

    Args:
        config_path (pathlib.Path|str): Path to config file (user expanded)

    Returns:
        dict: Config
    """

    return toml.load(pathlib.Path(config_path).expanduser())


def get_config_from_env(config_path):
    """Get configuration from environment variable.

    Args:
        config_path (pathlib.Path): Path to config file

    Raises:
        exceptions.ConfigError: Could not find config file

    Returns:
        dict: Config
    """

    try:
        return get_config_from_toml(config_path)
    except FileNotFoundError as err:
        raise FileNotFoundError('Could not find general config file {}'.format(config_path)) from err


def get_config_from_default(config_dir, default_config_path, config_name):
    """Get config from default location.
    Create default config file if there is none.

    Args:
        config_dir (pathlib.Path): [description]
        default_config_path (pathlib.Path): [description]
        config_name (pathlib.Path): [description]

    Raises:
        exceptions.ConfigError: Could not find config file

    Returns:
        dict: Config
    """

    config_path = config_dir / config_name
    try:
        return get_config_from_toml(config_path)
    except FileNotFoundError as err:
        shutil.copyfile(default_config_path , config_path)
        raise FileNotFoundError(('Could not find config.toml. First time run? '
                                 'Created one in {}. Please edit it.').format(config_path)) from err


def get_config():
    """Get configuration from default path
    or path defined via environment variable.

    Returns:
        dict: Config
    """

    env_var = os.getenv(info.CONFIG_ENVVAR)
    if env_var is not None:
        return get_config_from_env(pathlib.Path(env_var))

    info.CONFIG_DIR.mkdir(exist_ok=True)
    return get_config_from_default(info.CONFIG_DIR,
                                   info.DEFAULT_CONFIG_PATH,
                                   info.CONFIG_NAME)


def setup_logging_file():
    info.LOGGING_DIR.parent.mkdir(exist_ok=True)
    info.LOGGING_DIR.mkdir(exist_ok=True)