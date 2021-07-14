"""Information needed by various parts."""

from pathlib import Path

import appdirs

APP_NAME = 'tsplawupdater'
AUTHOR = 'ns_tsp_usovietnam'

default_dirs = appdirs.AppDirs(APP_NAME, AUTHOR)
CONFIG_DIR = Path(default_dirs.user_config_dir)
LOGGING_DIR = Path(default_dirs.user_log_dir)

CONFIG_ENVVAR = 'TSPLU_CONFIG'
CONFIG_NAME = 'config.toml'
CONFIG_PATH = CONFIG_DIR / CONFIG_NAME
# Default configuration path for copying to proper place
DEFAULT_CONFIG_PATH = Path('tsplawupdater') / CONFIG_NAME

LOGGING_PATH = LOGGING_DIR / 'nsdu_log.log'
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'TSPLawUpdaterFormatter': {
            'format': '[%(asctime)s %(name)s %(levelname)s] %(message)s'
        }
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'TSPLawUpdaterFormatter',
            'stream': 'ext://sys.stdout'
        }
    },

    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
}