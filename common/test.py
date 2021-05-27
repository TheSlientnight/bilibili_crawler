import re

import requests
from jsonpath import jsonpath
import bs4

url = "https://www.bilibili.com/video/BV17541147ui?from=search&seid=11535182145005403104"
res = requests.get(url).text
aid = re.search(r"(?<=aid\":)\d*", res).group()
# p = r"(?<=/video/).{12}"
# bvid = re.search(pattern=p, string=url).group()
# cid_url = "https://api.bilibili.com/x/player/pagelist?bvid={}&jsonp=jsonp".format(bvid)
# res = requests.get(cid_url).json()
# cid = jsonpath(res, "$..data[0]")[0]['cid']

if __name__ == '__main__':
    # print(res)
    print(aid)
    # print(cid)
