import os
import logging


migrate_logger = logging.getLogger("migration")


def init_logger(config):
    migrate_logger.handlers = []

    handlers = [logging.StreamHandler()]
    if "logging" in config:
        log_path_base = config["logging"]["logging-folder"] + os.sep
        if not os.path.exists(log_path_base):
            os.makedirs(log_path_base)

        handlers.append(
            logging.FileHandler(log_path_base + config["logging"]["migration-log-file"])
        )

        handlers.append(
            logging.FileHandler(log_path_base + config["logging"]["common-log-file"])
        )

        for h in handlers:
            h.setFormatter(
                logging.Formatter(
                    config["logging"]["basic-log-format"] + "{msg}",
                    style="{",
                    datefmt=config["logging"]["basic-time-format"],
                )
            )

    for h in handlers:
        migrate_logger.addHandler(h)

    migrate_logger.setLevel(logging.INFO)


def migrate_log(msg: str):
    migrate_logger.info(msg)
