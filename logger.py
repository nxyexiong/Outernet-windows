import os
import logging
from datetime import datetime

if not os.path.exists('log'):
    os.makedirs('log')
DT_STR = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGFILE = 'log/log_%s.log' % DT_STR

logging.basicConfig(level=logging.INFO, filename=LOGFILE, filemode='w+', format='[%(asctime)s][%(levelname).1s] %(message)s')
LOGGER = logging.getLogger()
