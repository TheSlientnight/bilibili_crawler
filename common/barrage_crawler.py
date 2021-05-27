import string
import time
import re
import math

import bs4
import jieba
import numpy as np
import requests
import pandas as pd
from jsonpath import jsonpath
from loguru import logger
from PIL import Image
from wordcloud import WordCloud

logger.add("../{}.log".format(time.strftime('%Y-%m-%d')))

NAME = ""


def get_av(url):
    """
    :param url:视频地址
    :return: 视频av号
    """
    p = r"(?<=aid\":)\d*"
    for i in range(3):
        try:
            res = requests.get(url).text
            logger.debug("正在提取视频av号")
            aid = re.search(p, res).group()
            return aid
        except Exception as e:
            logger.error("请求{}失败,失败原因:{}".format(url, e))
            continue


def get_cid(url):
    p = r"(?<=/video/).{12}"
    logger.debug("正在提取视频的bvid")
    bvid = re.search(p, url).group()
    barrage_url = ""
    global NAME
    # 重试三次
    for i in range(3):
        try:
            logger.debug("正在获取cid")
            res = requests.get("https://api.bilibili.com/x/player/pagelist?bvid={}&jsonp=jsonp".format(bvid)).json()
            cid = jsonpath(res, "$..data[0]")[0]['cid']
            barrage_url = f"https://comment.bilibili.com/{cid}.xml"
            NAME = cid
            return barrage_url
        except Exception as e:
            logger.error("获取cid失败,错误原因:{}".format(e))
            if i == 2:
                raise e
            else:
                continue
    return barrage_url


# 获取弹幕
def get_barrage(barrage_url) -> str:
    """
    :param barrage_url:视频地址
    :return:爬取结果的xml文件
    """
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.66 "
    }
    for i in range(3):
        try:
            logger.info(f"正在爬取{barrage_url}的弹幕")
            res = requests.get(barrage_url, headers=HEADERS).content.decode("utf-8")
            return res
        except Exception as e:
            logger.error(f"爬取{barrage_url}的弹幕失败，错误原因:{e}")
            continue


# 爬取评论
def get_comment(url):
    aid = get_av(url)
    comment_list = []
    for i in range(3):
        try:
            res = requests.get("https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={}&sort=1".format(aid)).json()
            comment_count = jsonpath(res, "$..data[page].count")[0]
            for i in range(math.ceil(comment_count / 20)):
                res = requests.get("https://api.bilibili.com/x/v2/reply?pn={}&type=1&oid={}&sort=1".format(i + 1, aid)).json()
                comment = jsonpath(res, r"$..data[replies]..[content][message]")
                comment_list.extend(comment)
                return comment_list
        except Exception as e:
            logger.error("爬取评论时发生错误,错误详情:{}".format(e))


# 处理爬取结果
def parse_html(text) -> list:
    """
    :param text:上一步获取的xml的text格式
    :return: 弹幕列表
    """
    logger.debug("弹幕数据处理中")
    soup = bs4.BeautifulSoup(text, "html.parser")
    # 获取d标签内的内容，并提取出来
    barrage_list = []
    for i in soup.findAll(name='d'):
        barrage_list.append(i.text)
    logger.debug("处理完毕")
    return barrage_list[1:]


# 存储并处理爬取到的弹幕
def data_preprocess(barrage, file_name):
    """
    :param barrage:爬取到的弹幕列表，转化为dict后交给pandas转化为csv
    :param file_name: 为存储文件取名
    """
    data_dict = {
        'barrage': barrage
    }
    pd_data = pd.DataFrame(data_dict)
    try:
        logger.info(f"向{file_name}.csv写入弹幕文件")
        pd_data.to_csv(f'../data/csv/{file_name}.csv', index=False, header=False, mode='w', encoding="utf-8-sig")
    except Exception as e:
        logger.error(f"{file_name}.csv写入过程发生错误,错误原因: {e}")
    try:
        logger.info(f"对{file_name}.csv内的弹幕进行处理")
        with open(f"../data/csv/{file_name}.csv", mode='r', encoding="utf-8") as f:
            reader = f.read().replace('\n', '')
            # 加载停用词表
            stopwords = [line.strip() for line in open('../data/stop_words.txt', encoding='utf-8').readlines()]
            # 去标点，去空白，去数字
            logger.debug("去除标点符号、空白符、数字")
            pun_num = string.punctuation + string.digits
            table = str.maketrans('', '', pun_num)
            reader = reader.translate(table)
            seg_list = jieba.lcut(reader, cut_all=True)  # 精确分词
            sentence = ''
            for word in seg_list:
                if word not in stopwords and word.isspace() is False:
                    sentence += word
                    sentence += ","
                sentence = sentence
        return sentence
    except Exception as e:
        logger.error("发生错误:{}".format(e))


# 记录词频
def count_words(text, file_name):
    """
    :param text: 处理后的弹幕
    :param file_name: 词频文件
    :return:
    """
    frequency = {}  # 使用字典存储 word-frequency的键值对
    words = text.split(',')
    for word in words:
        frequency[word] = frequency.get(word, 0) + 1
    pd_count = pd.DataFrame(frequency, index=['times']).T.sort_values('times', ascending=False)
    pd_count.to_csv(f'../data/csv/{file_name}_words_frequency.csv')


# 生成词云
def gen_cwd(text, file_name):
    mask = np.array(Image.open("../data/img/imgs.png"))
    wcd = WordCloud(
        colormap='Blues',  # 根据词频展示颜色，次数越多则越蓝
        font_path="C:\\Windows\\Fonts\\STFANGSO.TTF",
        mask=mask,
        background_color="White",
        repeat=True,
        mode='RGBA',
        scale=5,
        collocations=False
    )
    image_produce = wcd.generate(text).to_image()
    image_produce.save("../data/WordCloud/{}.png".format(file_name))


if __name__ == '__main__':
    video_url = str(input("请输入需要爬取的视频地址:"))
    barrage_data = get_barrage(video_url)
    p_data = parse_html(barrage_data)
    my_sentence = data_preprocess(p_data, NAME)
    count_words(my_sentence, NAME)
    gen_cwd(my_sentence, NAME)
