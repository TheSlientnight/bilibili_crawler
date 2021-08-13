import math
import re
import string
import threading
import time
import requests
from pathlib import Path
from random import uniform

import bs4
import jieba
import numpy as np
import pandas as pd
import threadpool
from PIL import Image
from jsonpath import jsonpath
from matplotlib import colors
from wordcloud import WordCloud
from common.logs import logging

lock = threading.Lock()
pool = threadpool.ThreadPool(1)


def get_comments(aid) -> list:
    comment_list = []

    def get_comment(page):
        res = requests.get("https://api.bilibili.com/x/v2/reply?pn={}&type=1&oid={}&sort=1"
                           .format(page, aid)).json()
        comment = jsonpath(res, r"$..data[replies]..[content][message]")
        lock.acquire()
        comment_list.extend(comment)
        lock.release()

    for i in range(3):
        try:
            num_res = requests.get("https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={}&sort=1".format(aid)).json()
            comment_count = jsonpath(num_res, "$..data[page].count")[0]
            page_num = math.ceil(comment_count / 20) + 1
            logging.debug(f"共计{page_num}页评论")
            pg_list = [pg for pg in range(1, page_num)]
            tasks = threadpool.makeRequests(get_comment, pg_list)
            [pool.putRequest(task) for task in tasks]
            pool.wait()
        except Exception as e:
            logging.error("爬取评论时发生错误,错误详情:{}".format(e))
            continue
        if comment_list:
            return comment_list
        else:
            logging.error("爬取评论时发生错误,任务终止")
            break


def get_barrages(burl) -> str:
    """
    :param burl:弹幕接口
    :return:爬取结果的xml文件
    """
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.66 "
    }
    for i in range(3):
        try:
            logging.info(f"正在爬取{burl}的弹幕")
            res = requests.get(burl, headers=HEADERS).content.decode("utf-8")
            return res
        except Exception as e:
            logging.error(f"爬取{burl}的弹幕失败，错误原因:{e}")
            continue


def parse_html(text):
    """
    :param text:上一步获取的xml的text格式
    :return: 弹幕列表
    """
    logging.debug("弹幕数据处理中")
    soup = bs4.BeautifulSoup(text, "html.parser")
    # 获取d标签内的内容，并提取出来
    barrage_list = []
    for i in soup.findAll(name='d'):
        barrage_list.append(i.text)
    if barrage_list:
        logging.debug("弹幕处理完毕")
        return barrage_list[1:]
    else:
        logging.warning("当前视频没有弹幕")


def get_cid(bvid):
    barrage_url = ""
    # 重试三次
    for i in range(3):
        try:
            logging.debug("正在获取cid")
            res = requests.get("https://api.bilibili.com/x/player/pagelist?bvid={}&jsonp=jsonp".
                               format(bvid)).json()
            cid = jsonpath(res, "$..data[0]")[0]['cid']
            barrage_url = f"https://comment.bilibili.com/{cid}.xml"
            return barrage_url
        except Exception as e:
            logging.error("获取cid失败,错误原因:{}".format(e))
            if i == 2:
                raise e
            else:
                continue
    return barrage_url


class UpSpace:
    p_mid = r"(?<=\w\/)(\d*)"
    p_favorite = r"(?<=\"favorite\":)\d*"
    p_coin = r"(?<=\"coin\":)\d*"
    p_share = r"(?<=\"share\":)\d*"
    p_like = r"(?<=\"like\":)\d*"
    p_tag = r"(?<=tag_name\":\")([^\x00-\xff]*[\d]*[\w]*)"

    def __init__(self, url):
        self.mid = re.search(UpSpace.p_mid, url).group()
        self.pn = 0
        self.space = ""
        self.title_list = []
        self.url_list = []
        self.aid_list = []
        self.bvid_list = []
        self.play_list = []
        self.like_list = []
        self.coin_list = []
        self.favorite_list = []
        self.share_list = []
        self.time_list = []
        self.create_list = []
        self.tag_list = []
        self.sentence = ""
        self.name = ""

    def get_page_nums(self):
        for i in range(3):
            try:
                res = requests.get(f"https://api.bilibili.com/x/space/arc/search?mid={self.mid}&pn=1&ps=25&index=1"
                                   f"&jsonp=jsonp").json()
                counts = jsonpath(res, "$.data..page.count")[0]
                page_nums = math.ceil(counts / 25)
                self.pn = page_nums + 1
            except Exception as e:
                logging.error("获取页面失败,错误原因:{}".format(e))
                continue

    def get_space_info(self):
        for i in range(1, self.pn):
            for times in range(3):
                try:
                    res = requests.get("https://api.bilibili.com/x/space/arc/search?"
                                       "mid={}&pn={}&ps=25&index=1&jsonp=jsonp"
                                       .format(self.mid, i)).json()
                    self.space = jsonpath(res, "$..vlist..author")[0]
                    self.title_list.extend(jsonpath(res, "$..vlist..title"))
                    self.aid_list.extend(jsonpath(res, "$..vlist..aid"))
                    self.bvid_list.extend(jsonpath(res, "$..vlist..bvid"))
                    self.play_list.extend(jsonpath(res, "$..vlist..play"))
                    self.time_list.extend(jsonpath(res, "$..vlist..created"))
                    break
                except Exception as e:
                    logging.error("获取视频空间信息时发生错误,错误:{}".format(e))
                    continue

    def time_handle(self):
        for stpt in self.time_list:
            timeArray = time.localtime(stpt)
            create = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
            self.create_list.append(create)

    def get_video_info(self):
        for bvid in self.bvid_list:
            n = self.bvid_list.index(bvid)
            video_name = self.title_list[n]
            url = f"https://www.bilibili.com/video/{bvid}"
            self.url_list.append(url)
            for i in range(3):
                try:
                    logging.info(f"正在获取视频:{video_name}的信息")
                    res = requests.get(f"https://www.bilibili.com/video/{bvid}").text
                    like = re.search(UpSpace.p_like, res).group()
                    favorite = re.search(UpSpace.p_favorite, res).group()
                    coin = re.search(UpSpace.p_coin, res).group()
                    share = re.search(UpSpace.p_share, res).group()
                    tags = re.findall(UpSpace.p_tag, res)
                    self.tag_list.append(tags)
                    self.share_list.append(share)
                    self.like_list.append(like)
                    self.favorite_list.append(favorite)
                    self.coin_list.append(coin)
                    break
                except Exception as e:
                    logging.error(f"获取视频:{video_name}的信息时发生错误,错误:{e}")
                    continue

    def data_write(self):
        if self.title_list and self.aid_list and self.bvid_list and self.url_list and self.play_list \
                and self.create_list and self.coin_list and self.like_list and self.favorite_list \
                and self.share_list and self.tag_list:
            info_dict = {
                "视频标题": self.title_list,
                "创建时间": self.create_list,
                "视频标签": self.tag_list,
                "url": self.url_list,
                "aid": self.aid_list,
                "bvid": self.bvid_list,
                "播放量": self.play_list,
                "投币": self.coin_list,
                "点赞": self.like_list,
                "收藏": self.favorite_list,
                "分享": self.share_list
            }
            info_data = pd.DataFrame(info_dict)
            logging.info("正在写入UP主:{}的视频信息".format(self.space))
            if Path(f"data/csv/{self.space}").absolute().is_dir() is not True:
                logging.debug(f"创建目录:{self.space}")
                Path(f"data/csv/{self.space}").absolute().mkdir()
            info_data.to_csv(f"data/csv/{self.space}/{self.space}的全部视频信息(重要).csv", index=False, mode="w",
                             encoding="utf-8_sig")
        else:
            logging.error("没有获取到UP主的视频信息，请重试")

    def get_comment(self):
        for aid in self.aid_list:
            index = self.aid_list.index(aid)
            bvid = self.bvid_list[index]
            p = r"\.|\/|\?"
            self.name = re.sub(p, "", self.title_list[index])
            video_comment = get_comments(aid)
            self.__save_comment(video_comment, self.name)
            self.get_barrage(bvid)
            time.sleep(uniform(1.2, 3.0))

    def get_barrage(self, bvid):
        barrage_url = get_cid(bvid)
        txt = get_barrages(barrage_url)
        p_data = parse_html(txt)
        if p_data:
            self.__data_preprocess(p_data, self.name)
        else:
            self.__make_cwd()
        self.sentence = ""

    def __make_cwd(self):
        if self.sentence:
            self.gen_cwd(self.sentence, self.name)

    def __data_preprocess(self, barrage, file_name):
        data_dict = {
            "barrage": barrage
        }
        pd_data = pd.DataFrame(data_dict)

        try:
            logging.info(f"向{file_name}_弹幕.csv写入弹幕文件")
            if Path(f"data/csv/{self.space}/{file_name}").absolute().is_dir() is not True:
                logging.debug(f"创建目录:{self.space}/{file_name}")
                Path(f"data/csv/{self.space}/{file_name}").absolute().mkdir()
            pd_data.to_csv(f"data/csv/{self.space}/{file_name}/{file_name}_弹幕.csv", index=False, header=False, mode="w",
                           encoding="utf-8_sig")
        except Exception as e:
            logging.error(f"{file_name}_弹幕.csv写入过程发生错误,错误原因: {e}")
        try:
            logging.info(f"对{file_name}_弹幕.csv内的弹幕进行处理")
            with open(f"data/csv/{self.space}/{file_name}/{file_name}_弹幕.csv", mode="r", encoding="utf-8") as f:
                reader = f.read().replace("\n", "")
                # 加载停用词表
                stopwords = [line.strip() for line in open("data/stop_words.txt", encoding="utf-8").readlines()]
                # 去标点，去空白，去数字
                logging.debug("去除标点符号、空白符、数字")
                pun_num = string.punctuation + string.digits
                table = str.maketrans("", "", pun_num)
                reader = reader.translate(table)
                seg_list = jieba.lcut(reader, cut_all=True)  # 精确分词
                sentence = ""
                for word in seg_list:
                    if word not in stopwords and word.isspace() is False:
                        sentence += word
                        sentence += ","
                    sentence = sentence
            self.__count_words(sentence, self.name)
            self.sentence += "".join(sentence)
            self.__make_cwd()
        except Exception as e:
            logging.error("处理弹幕时发生错误:{}".format(e))

    # 处理评论
    def __save_comment(self, comment, file_name):
        if comment:
            comment_dict = {
                "comment": comment
            }
            pd_data = pd.DataFrame(comment_dict)
            try:
                logging.info("向{}_评论.csv中写入评论".format(file_name))
                if Path(f"data/csv/{self.space}/{file_name}").absolute().is_dir() is not True:
                    logging.debug(f"创建目录:{self.space}/{file_name}")
                    Path(f"data/csv/{self.space}/{file_name}").absolute().mkdir()
                pd_data.to_csv(f"data/csv/{self.space}/{file_name}/{file_name}_评论.csv", index=False, header=False,
                               mode="w",
                               encoding="utf-8_sig")
            except Exception as e:
                logging.error(f"{file_name}.csv写入过程发生错误,错误原因: {e}")
            try:
                logging.info(f"对{file_name}_评论.csv内的评论进行处理")
                with open(f"data/csv/{self.space}/{file_name}/{file_name}_评论.csv", mode="r", encoding="utf-8") as f:
                    reader = f.read().replace("\n", "")
                    # 加载停用词表
                    stopwords = [line.strip() for line in open("data/stop_words.txt", encoding="utf-8").readlines()]
                    # 去标点，去空白，去数字
                    logging.debug("去除标点符号、空白符、数字")
                    pun_num = string.punctuation + string.digits
                    table = str.maketrans("", "", pun_num)
                    reader = reader.translate(table)
                    seg_list = jieba.lcut(reader, cut_all=True)  # 精确分词
                    sentence = ""
                    for word in seg_list:
                        if word not in stopwords and word.isspace() is False:
                            sentence += word
                            sentence += ","
                        sentence = sentence
                self.__count_words(sentence, self.name)
                self.sentence += "".join(sentence)
            except Exception as e:
                logging.error("处理评论时发生错误:{}".format(e))
        else:
            logging.warning("当前视频:{}没有评论".format(file_name))

    def __count_words(self, text, file_name):
        """
        :param text: 处理后的弹幕
        :param file_name: 词频文件
        :return:
        """
        frequency = {}  # 使用字典存储 word-frequency的键值对
        words = text.split(",")
        for word in words:
            frequency[word] = frequency.get(word, 0) + 1
        pd_count = pd.DataFrame(frequency, index=["times"]).T.sort_values("times", ascending=False)
        pd_count.to_csv(f"data/csv/{self.space}/{file_name}/{file_name}_词频.csv", mode="a", header=None,
                        encoding="utf-8_sig")

    def gen_cwd(self, text, file_name):
        colormaps = colors.ListedColormap(['#4169E1', '#1E90FF', '#87CEFA'])
        mask = np.array(Image.open("data/img/imgs.png"))
        wcd = WordCloud(
            colormap=colormaps,
            # font_path="C:\\Windows\\Fonts\\STFANGSO.TTF",
            mask=mask,
            background_color="White",
            repeat=True,
            mode='RGBA',
            scale=5,
            collocations=False
        )
        logging.debug("正在生成:{} 的词云".format(file_name))
        image_produce = wcd.generate(text).to_image()
        if Path(f"data/WordCloud/{self.space}词云").absolute().is_dir() is not True:
            logging.debug(f"创建目录:{self.space}词云")
            Path(f"data/WordCloud/{self.space}词云").absolute().mkdir()
        image_produce.save("data/WordCloud/{}词云/{}.png".format(self.space, file_name))
