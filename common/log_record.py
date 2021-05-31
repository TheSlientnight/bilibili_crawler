import time
from pathlib import Path


def archive_log(filepath="logs") -> str:
    """
    :param filepath:日志文件的存放地址
    :return: 将该月内的日志文件进行打包
    """
    dir_name = Path(filepath, time.strftime("%Y-%m"))
    if not Path.is_dir(dir_name):
        Path(dir_name).mkdir(parents=True, exist_ok=False)
    return str(Path(dir_name, "{}.log".format(time.strftime('%Y-%m-%d'))))
