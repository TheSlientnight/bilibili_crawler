import time
from pathlib import Path
from random import uniform

from common.video_crawler import *

lock = threading.Lock()
pool = threadpool.ThreadPool(1)


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
                    # time.sleep(uniform(1.2, 3.0))
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
            p = r"\.|\/|\?"
            self.name = re.sub(p, "", self.title_list[self.aid_list.index(aid)])
            video_comment = get_comments(aid)
            self.__save_comment(video_comment, self.name)

    def get_barrage(self):
        for vurl in self.url_list:
            p = r"\.|\/|\?"
            self.name = re.sub(p, "", self.title_list[self.url_list.index(vurl)])
            barrage_url = get_cid(vurl)
            txt = get_barrages(barrage_url)
            p_data = parse_html(txt)
            self.__data_preprocess(p_data, self.name)

    def __make_cwd(self):
        self.__count_words(self.sentence, self.name)
        gen_cwd(self.sentence, self.name)

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
            self.sentence = "".join(sentence)
            self.__make_cwd()
        except Exception as e:
            logging.error("处理弹幕时发生错误:{}".format(e))

    # 处理评论
    def __save_comment(self, comment, file_name):
        comment_dict = {
            "comment": comment
        }
        pd_data = pd.DataFrame(comment_dict)
        try:
            logging.info("向{}_评论.csv中写入评论".format(file_name))
            if Path(f"data/csv/{self.space}/{file_name}").absolute().is_dir() is not True:
                logging.debug(f"创建目录:{self.space}/{file_name}")
                Path(f"data/csv/{self.space}/{file_name}").absolute().mkdir()
            pd_data.to_csv(f"data/csv/{self.space}/{file_name}/{file_name}_评论.csv", index=False, header=False, mode="w",
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
            self.sentence = "".join(sentence)
        except Exception as e:
            logging.error("处理评论时发生错误:{}".format(e))

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
