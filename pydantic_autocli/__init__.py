from pydantic import BaseModel, Field
from .cli import AutoCLI, param
import logging

def set_log_level(level):
    """Set the log level for pydantic-autocli.

    Args:
        level: A logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logger = logging.getLogger("pydantic_autocli")
    logger.setLevel(level)


__all__ = [
    "BaseModel",
    "Field",
    "AutoCLI",
    "param",
    "set_log_level",
]
