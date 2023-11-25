import json
import logging.config
from . import handlers


with open("log/conf.json", "r") as file:
    config = json.load(file)

logging.config.dictConfig(config)
logger = logging.getLogger("app_logger")
