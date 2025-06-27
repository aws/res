#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import logging.handlers
import os
import sys
from functools import lru_cache
from typing import Optional

import res.constants as constants
from pyhocon import ConfigFactory, ConfigTree
from res.utils.cluster_settings_utils import build_config_from_db


def get_default_logging_config(profile: str = "default") -> ConfigTree:
    return ConfigFactory.from_dict(
        {
            "cluster": {
                "logging": {
                    "formatters": {
                        "default": {
                            "format": "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
                        }
                    },
                    "handlers": {
                        "console": {"class": "logging.handlers.StreamHandler"}
                    },
                    "profiles": {
                        "default": {
                            "formatter": "default",
                            "loggers": {
                                "app": {"level": "INFO", "handlers": ["console"]},
                                "root": {"level": "ERROR", "handlers": ["console"]},
                            },
                        },
                        "debug": {
                            "formatter": "default",
                            "loggers": {
                                "app": {"level": "DEBUG", "handlers": ["console"]},
                                "root": {"level": "ERROR", "handlers": ["console"]},
                            },
                        },
                    },
                }
            },
            "default": {
                "logging": {
                    "profile": profile,
                    "default_log_file_name": "application.log",
                }
            },
        }
    )


class ResLogging:
    def __init__(
        self,
        config: ConfigTree = None,
        module_id: str = "default",
        default_logging_profile: str = None,
    ):
        if not default_logging_profile:
            default_logging_profile = "default"

        if config and config.get_config(f"{module_id}.logging", None):
            self._config = config
            self.module_id = module_id
        else:
            self.module_id = "default"
            self._config = get_default_logging_config(profile=default_logging_profile)

        self._file_handlers = {}
        self._initialize_root_logger()
        logging.captureWarnings(True)

    def _initialize_root_logger(self):
        root = logging.getLogger()
        self._reset_logger(root)
        self.build_logger(logger_template=constants.LOGGER_TEMPLATE_ROOT)

    def get_log_dir(self) -> str:
        log_dir = self._config.get_string(
            f"{self.module_id}.logging.logs_directory", None
        )
        if log_dir and os.path.isabs(log_dir):
            return log_dir
        if not log_dir:
            log_dir = "logs"
        app_deploy_dir = os.environ.get("IDEA_APP_DEPLOY_DIR")
        return os.path.join(app_deploy_dir, log_dir)

    def _get_default_log_file_name(self):
        return self._config.get_string(
            f"{self.module_id}.logging.default_log_file_name", None
        )

    def _build_formatter(self, name):
        log_format = self._config.get_string(
            f"cluster.logging.formatters.{name}.format", None
        )
        return logging.Formatter(fmt=log_format)

    def _build_handler(self, handler_name, logger_name: Optional[str]):
        handler_config = self._config.get(
            f"cluster.logging.handlers.{handler_name}", None
        )

        handler_cls = handler_config["class"]

        if handler_cls == "logging.handlers.StreamHandler":
            return logging.StreamHandler(stream=sys.stdout)
        elif handler_cls == "logging.handlers.TimedRotatingFileHandler":
            create_separate_file = False
            separate_files = self._get_separate_files()
            if separate_files and len(separate_files) > 0:
                for separate_file in separate_files:
                    if logger_name.startswith(separate_file):
                        create_separate_file = True
                        break

            if create_separate_file:
                filename = logger_name
            else:
                filename = self._get_default_log_file_name()

            log_dir = self.get_log_dir()
            logfile = os.path.join(log_dir, filename)

            if logfile in self._file_handlers:
                return self._file_handlers[logfile]
            else:
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    filename=logfile,
                    encoding=constants.DEFAULT_ENCODING,
                    when=handler_config["when"],
                    interval=int(handler_config["interval"]),
                    backupCount=int(handler_config["backupCount"]),
                )
                self._file_handlers[logfile] = file_handler
                return file_handler
        else:
            raise Exception(f"logging handler: {handler_cls} not supported")

    def _get_profile(self):
        return self._config.get_string(f"{self.module_id}.logging.profile", None)

    def _get_separate_files(self):
        return self._config.get_list(f"{self.module_id}.logging.separate_files", [])

    def _get_enable_debug_logging(self):
        return self._config.get_list(
            f"{self.module_id}.logging.enable_debug_logging", []
        )

    def _get_profile_settings(self, profile=None):
        if not profile:
            profile = self._get_profile()
        return self._config.get(f"cluster.logging.profiles.{profile}", None)

    @staticmethod
    def _reset_logger(logger: logging.Logger):
        for handler in logger.handlers:
            logger.removeHandler(handler)

        for log_filter in logger.filters:
            logger.removeFilter(log_filter)

    @staticmethod
    def _build_default_logger(logger_template: str, logger: logging.Logger):
        if logger_template == "root":
            level = logging.CRITICAL
        else:
            level = logging.INFO

        logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
            )
        )
        logger.addHandler(handler)
        return logger

    def build_logger(self, logger_template: str = None, logger_name: str = None):
        if logger_template == constants.LOGGER_TEMPLATE_APP and not logger_name:
            logger_name = "app"

        logger = logging.getLogger(logger_name)
        if len(logger.handlers) > 0:
            return logger

        settings = self._get_profile_settings()

        if not settings:
            return self._build_default_logger(
                logger_template=logger_template, logger=logger
            )

        level = settings[f"loggers.{logger_template}.level"]

        # if root logger, skip debug overrides
        if logger_name:
            debug_logging = self._get_enable_debug_logging()
            if debug_logging and len(debug_logging) > 0:
                for debug_log in debug_logging:
                    if logger_name.startswith(debug_log):
                        level = logging.DEBUG

        logger.setLevel(level)

        for handler_name in settings[f"loggers.{logger_template}.handlers"]:
            handler = self._build_handler(
                handler_name=handler_name, logger_name=logger_name
            )
            handler.setLevel(level)
            handler.setFormatter(self._build_formatter(name=settings["formatter"]))
            logger.addHandler(handler)

        logger.propagate = False

        return logger


@lru_cache
def res_logging() -> ResLogging:
    return ResLogging(
        config=(
            build_config_from_db(".+\\.logging\\..+")
            if os.getenv("IDEA_MODULE_ID")
            else None
        ),
        module_id=os.getenv("IDEA_MODULE_ID"),
    )


def get_logger(logger_name: str) -> logging.Logger:
    return res_logging().build_logger(
        logger_template=constants.LOGGER_TEMPLATE_APP, logger_name=logger_name
    )
