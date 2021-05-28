import threading
import threadpool
import requests

pool = threadpool.ThreadPool(10)
lock = threading.Lock()

aList = []


def get_data(num):
    res = requests.get("https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid=455513434&sort=1").json()
    lock.acquire()
    aList.extend(res)
    lock.release()
    print(aList)


if __name__ == '__main__':
    li = [i for i in range(1, 11)]
    tasks = threadpool.makeRequests(get_data, li)
    [pool.putRequest(task) for task in tasks]
    pool.wait()