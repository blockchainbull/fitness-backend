# silence_sqlalchemy.py
import logging
import sqlalchemy.engine

# Monkey patch the SQLAlchemy engine logger
sqlalchemy.engine.Engine._should_log_debug = lambda *args, **kwargs: False

# Also disable the loggers directly
logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL)
logging.getLogger('sqlalchemy.engine').setLevel(logging.CRITICAL)
logging.getLogger('sqlalchemy.pool').setLevel(logging.CRITICAL)
logging.getLogger('sqlalchemy.orm').setLevel(logging.CRITICAL)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.CRITICAL)