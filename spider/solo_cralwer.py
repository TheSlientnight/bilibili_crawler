import math
import re
import string
import threading

import bs4
import jieba
import numpy as np
import pandas as pd
import requests
import threadpool
from PIL import Image
from jsonpath import jsonpath
from wordcloud import WordCloud
import common.globalver as gl
from common.logs import logging

lock = threading.Lock()
pool = threadpool.ThreadPool(1)


def get_av(url):
    """
    :param url:视频地址
    :return: 视频av号
    """
    p_av = r"(?<=aid\":)\d*"
    p_name = r"(?<=content=\")([^\x00-\xff]*[\d]*[\w]*)(?=_哔哩哔哩)"
    for i in range(3):
        try:
            res = requests.get(url).text
            logging.debug("正在提取视频av号")
            aid = re.search(p_av, res).group()
            name = re.search(p_name, res).group()
            gl.set_value("name", name)
            logging.debug("视频名称:{}, av号:{}".format(name, aid))
            return aid
        except Exception as e:
            logging.error("请求{}失败,失败原因:{}".format(url, e))
            continue


def get_cid(url):
    p = r"(?<=/video/).{12}"
    logging.debug("正在提取视频的bvid")
    bvid = re.search(p, url).group()
    barrage_url = ""
    # 重试三次
    for i in range(3):
        try:
            logging.debug("正在获取cid")
            res = requests.get("https://api.bilibili.com/x/player/pagelist?bvid={}&jsonp=jsonp".format(bvid)).json()
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


# 获取弹幕
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


# 爬取评论
def get_comments(aid) -> list:
    comment_list = []

    def get_comment(page):
        res = requests.get("https://api.bilibili.com/x/v2/reply?pn={}&type=1&oid={}&sort=1"
                           .format(page, aid)).json()
        try:
            comment = jsonpath(res, r"$..data[replies]..[content][message]")
            lock.acquire()
            comment_list.extend(comment)
            lock.release()
        except TypeError as e:
            logging.error("当前视频:%s 没有评论:%s" % (aid, e))

    for i in range(3):
        try:
            num_res = requests.get("https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={}&sort=1".format(aid)).json()
            comment_count = jsonpath(num_res, "$..data[page].count")[0]
            page_num = math.ceil(comment_count / 20) + 1
            logging.debug(f"共计{page_num}页")
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


# # 处理评论
# def save_comment(comment, file_name):
#     comment_dict = {
#         'comment': comment
#     }
#     pd_data = pd.DataFrame(comment_dict)
#     try:
#         logging.info("向{}_评论.csv中写入评论".format(file_name))
#         pd_data.to_csv(f'data/csv/{file_name}_评论.csv', index=False, header=False, mode='w', encoding="utf-8_sig")
#     except Exception as e:
#         logging.error(f"{file_name}.csv写入过程发生错误,错误原因: {e}")
#     try:
#         logging.info(f"对{file_name}_评论.csv内的评论进行处理")
#         with open(f"data/csv/{file_name}_评论.csv", mode='r', encoding="utf-8") as f:
#             reader = f.read().replace('\n', '')
#             # 加载停用词表
#             stopwords = [line.strip() for line in open('data/stop_words.txt', encoding='utf-8').readlines()]
#             # 去标点，去空白，去数字
#             logging.debug("去除标点符号、空白符、数字")
#             pun_num = string.punctuation + string.digits
#             table = str.maketrans('', '', pun_num)
#             reader = reader.translate(table)
#             seg_list = jieba.lcut(reader, cut_all=True)  # 精确分词
#             sentence = ''
#             for word in seg_list:
#                 if word not in stopwords and word.isspace() is False:
#                     sentence += word
#                     sentence += ","
#                 sentence = sentence
#         return sentence
#     except Exception as e:
#         logging.error("处理评论时发生错误:{}".format(e))


# 处理爬取结果
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


# # 存储并处理爬取到的弹幕
# def data_preprocess(barrage, file_name):
#     """
#     :param barrage:爬取到的弹幕列表，转化为dict后交给pandas转化为csv
#     :param file_name: 为存储文件取名
#     """
#     data_dict = {
#         'barrage': barrage
#     }
#     pd_data = pd.DataFrame(data_dict)
#     try:
#         logging.info(f"向{file_name}_弹幕.csv写入弹幕文件")
#         pd_data.to_csv(f'data/csv/{file_name}_弹幕.csv', index=False, header=False, mode='w', encoding="utf-8_sig")
#     except Exception as e:
#         logging.error(f"{file_name}_弹幕.csv写入过程发生错误,错误原因: {e}")
#     try:
#         logging.info(f"对{file_name}_弹幕.csv内的弹幕进行处理")
#         with open(f"data/csv/{file_name}_弹幕.csv", mode='r', encoding="utf-8") as f:
#             reader = f.read().replace('\n', '')
#             # 加载停用词表
#             stopwords = [line.strip() for line in open('data/stop_words.txt', encoding='utf-8').readlines()]
#             # 去标点，去空白，去数字
#             logging.debug("去除标点符号、空白符、数字")
#             pun_num = string.punctuation + string.digits
#             table = str.maketrans('', '', pun_num)
#             reader = reader.translate(table)
#             seg_list = jieba.lcut(reader, cut_all=True)  # 精确分词
#             sentence = ''
#             for word in seg_list:
#                 if word not in stopwords and word.isspace() is False:
#                     sentence += word
#                     sentence += ","
#                 sentence = sentence
#         return sentence
#     except Exception as e:
#         logging.error("处理弹幕时发生错误:{}".format(e))


# 记录词频
# def count_words(text, file_name):
#     """
#     :param text: 处理后的弹幕
#     :param file_name: 词频文件
#     :return:
#     """
#     frequency = {}  # 使用字典存储 word-frequency的键值对
#     words = text.split(',')
#     for word in words:
#         frequency[word] = frequency.get(word, 0) + 1
#     pd_count = pd.DataFrame(frequency, index=['times']).T.sort_values('times', ascending=False)
#     pd_count.to_csv(f'data/csv/{file_name}_词频.csv', mode='a', header=None, encoding="utf-8_sig")


# 生成词云
def gen_cwd(text, file_name):
    mask = np.array(Image.open("data/img/imgs.png"))
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
    logging.debug("正在生成:{} 的词云".format(file_name))
    image_produce = wcd.generate(text).to_image()
    image_produce.save("data/WordCloud/{}.png".format(file_name))


if __name__ == '__main__':
    gen_cwd("", "haha")
#     video_url = str(input("请输入需要爬取的视频地址:"))
#     barrage_data = get_barrages(video_url)
#     vd_aid = get_av(video_url)
#     comments = get_comments(vd_aid)
#     comment_sentence = save_comment(comments, NAME)
#     count_words(comment_sentence, NAME)
#     p_data = parse_html(barrage_data)
#     my_sentence = data_preprocess(p_data, NAME)
#     count_words(my_sentence, NAME)
#     gen_cwd(my_sentence, NAME)
