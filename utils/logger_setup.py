# utils/logger_setup.py
import logging

# The main logging configuration (level, format, handlers) should be done once
# in your main bot script (e.g., main.py using logging.basicConfig).
# This file provides a utility to easily get a logger instance for different parts
# of your application, typically cogs.

def get_cog_logger(cog_name: str) -> logging.Logger:
    """
    Returns a logger instance with a standardized name for a cog.
    Example: 'cog.MyCommandsCog'
    """
    # Ensure the cog_name doesn't start with 'cogs.' if it's passed that way
    if cog_name.startswith('cogs.'):
        cog_name = cog_name.split('.', 1)[1] # Get the part after 'cogs.'

    logger_name = f"cog.{cog_name}"
    return logging.getLogger(logger_name)

# Example of how a cog might use this:
# from utils.logger_setup import get_cog_logger
# logger = get_cog_logger(__name__) # __name__ will be 'cogs.your_cog_filename'
# logger.info("This is a log message from the cog.")

# No need to call basicConfig here if it's done in main.py
# logging.info("Logger setup utility module loaded.") # This might log too early if basicConfig isn't set yet.
# It's better if main.py logs its own loading and then individual modules confirm loading via their own loggers.