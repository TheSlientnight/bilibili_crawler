# BiliBili弹幕与评论爬虫

可以通过UP主的视频空间地址爬取该UP下的全部视频弹幕以及评论，并统一生成词云
* 注:评论下的评论暂不支持全量获取

支持并发爬取，仅需调整/common/get_urls.py中的pool=threadpool.ThreadPool(x)即可，但需要注意，B站采用令牌桶机制，并发量过大会导致IP短暂被封禁
