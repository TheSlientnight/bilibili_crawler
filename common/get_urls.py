import requests
import pandas as pd
import re
from jsonpath import jsonpath
from common.logs import logging


class UpSpace:
    p = r"(?<=\w\/)(\d*)"

    def __init__(self, url):
        self.mid = re.search(UpSpace.p, url)
        self.pn = 0

    def get_page_nums(self):
        for i in range(3):
            try:
                res = requests.get(f"https://api.bilibili.com/x/space/arc/search?mid={self.mid}&pn=1&ps=25&index=1"
                                   f"&jsonp=jsonp").json()
                counts = jsonpath(res, "$.data..page.count")[0]
                page_nums = counts / 25
                self.pn = page_nums
                return page_nums
            except Exception as e:
                logging.error("获取页面失败,错误原因:{}".format(e))
                continue

    def get_video_info(self):
        title_list = []
        for i in range(self.pn):
            for times in range(3):
                try:
                    res = requests.get("https://api.bilibili.com/x/space/arc/search?"
                                       "mid={}&pn={}&ps=25&index=1&jsonp=jsonp"
                                       .format(self.mid, i)).json()
                    titles = jsonpath(res, "$..vlist..title")
                    title_list.extend(titles)
                    break
                except Exception as e:
                    logging.error("获取标题时发生错误,错误:{}".format(e))
                    continue
        return title_list