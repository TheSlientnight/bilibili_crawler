from common.get_urls import UpSpace


if __name__ == '__main__':
    my_url = str(input("请输入Up主的视频空间:"))
    up = UpSpace(my_url)
    up.get_page_nums()
    up.get_space_info()
    up.get_video_info()
    up.time_handle()
    up.data_write()
    up.get_comment()
    up.get_barrage()
