import re
import math

import requests as requests
from jsonpath import jsonpath
import bs4

# url = "https://www.bilibili.com/video/BV1t5411K79e?spm_id_from=333.5.b_67616d655f7374616e645f616c6f6e65.39"
# url2 = "https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid=930710044&sort=1"
# res = requests.get(url).text
# res2 = requests.get(url2).json()
# aid = re.search(r"(?<=aid\":)\d*", res).group()
# p = r"(?<=/video/).{12}"
# bvid = re.search(pattern=p, string=url).group()
# cid_url = "https://api.bilibili.com/x/player/pagelist?bvid={}&jsonp=jsonp".format(bvid)
# res = requests.get(cid_url).json()
# cid = jsonpath(res, "$..data[0]")[0]['cid']

if __name__ == '__main__':
    # print(res)
    # print(aid)
    # print(cid)
    # c = jsonpath(res2, "$..data[page].acount")[0]
    # print(c)
    res = requests.get(f"https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid=459511646&sort=1").json()
    comment_list = []
    comment_count = jsonpath(res, "$..data[page].count")[0]
    for i in range(math.ceil(comment_count/20)):
        res = requests.get(f"https://api.bilibili.com/x/v2/reply?pn={i + 1}&type=1&oid=459511646&sort=1").json()
        comment = jsonpath(res, r"$..data[replies]..[content][message]")
        comment_list.extend(comment)
    # print("{}haha".format(math.ceil(comment_count/20) + 1))
    print(comment_list)