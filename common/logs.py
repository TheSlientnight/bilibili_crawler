import time

from loguru import logger

from common.log_record import archive_log


class Loggings:
    __instance = None
    logger.add("{}".format(archive_log(), time.strftime("%Y-%m-%d")), rotation="500MB", encoding="utf-8",
               enqueue=True,
               retention="10 days")

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(Loggings, cls).__new__(cls, *args, **kwargs)

        return cls.__instance

    def __init__(self):
        self.log = logger

    def info(self, msg):
        return self.log.info(msg)

    def debug(self, msg):
        return self.log.debug(msg)

    def warning(self, msg):
        return self.log.warning(msg)

    def error(self, msg):
        return self.log.error(msg)


logging = Loggings()

if __name__ == '__main__':
    logging.info("123456")