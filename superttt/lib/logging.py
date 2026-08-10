import logging
from digiformatter import logger as digilogger

def setup() -> None:
    logging.basicConfig(level=logging.INFO)
    dfhandler = digilogger.DigiFormatterHandler()
    dfhandlersource = digilogger.DigiFormatterHandler(showsource=True)

    logger = logging.getLogger("superttt")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    logger.propagate = False
    logger.addHandler(dfhandler)

    arcadelogger = logging.getLogger("arcade")
    arcadelogger.setLevel(logging.WARNING)
    arcadelogger.handlers = []
    arcadelogger.propagate = False
    arcadelogger.addHandler(dfhandlersource)
