import logging

LOGFILE = 'log.log'

logging.basicConfig(level=logging.INFO, filename=LOGFILE, filemode='w+', format='[%(asctime)s][%(levelname).1s] %(message)s')
LOGGER = logging.getLogger()
