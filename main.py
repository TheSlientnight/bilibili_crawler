from common.video_crawler import *
import common.globalver as gl


def run_crawler(url):
    video_url = url
    barrage_data = get_barrage(video_url)
    vd_aid = get_av(video_url)
    name = gl.get_value("name")
    comments = get_comments(vd_aid)
    comment_sentence = save_comment(comments, name)
    count_words(comment_sentence, name)
    p_data = parse_html(barrage_data)
    my_sentence = data_preprocess(p_data, name)
    count_words(my_sentence, name)
    gen_cwd(my_sentence, name)


if __name__ == '__main__':
    space_url = input(str("请输入需要爬取的站点:"))
    run_crawler(space_url)