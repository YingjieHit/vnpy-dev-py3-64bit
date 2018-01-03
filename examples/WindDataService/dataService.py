# encoding: UTF-8

import json
import datetime
import copy
from time import sleep

from pymongo import MongoClient, ASCENDING

from vnpy.data.wind.vnwind import WindApi
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from config import CONFIG

# 加载配置
# config = open("config.json")
# setting = json.load(config)
setting = CONFIG

MONGO_HOST = setting["MONGO_HOST"]
MONGO_PORT = setting["MONGO_PORT"]
SYMBOLS = setting["SYMBOLS"]

mc = MongoClient(MONGO_HOST, MONGO_PORT)  # Mongo连接
db = mc[MINUTE_DB_NAME]   # 数据库

task_list = []
api = WindApi()


def saveBar(symbol, bar_list):
    """存储bar数据"""
    cl = db[symbol]                                                   # 集合
    cl.ensure_index([('datetime', ASCENDING)], unique=True)         # 添加索引
    for bar in bar_list:
        # 将bar转换为dict
        d = bar.__dict__
        # 设置bar的datetime为更新过滤条件
        flt = {'datetime': bar.datetime}
        cl.replace_one(flt, d, True)

def taskRemove(symbol):
    # 移除已经完成的任务
    global task_list
    if symbol in task_list:
        task_list.remove(symbol)

def downloadMinuteBarBySymbol(symbol, start_date, end_date):
    """下载某一合约的分钟线数据"""
    api.download_minute_bar(symbol, start_date, end_date, saveBar, taskRemove)


def downloadAllMinuteBar(start_date=None, end_date=None):
    """下载配置中所有合约中的分钟数据"""
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = datetime.datetime.strptime(end_date, "%Y%m%d")  - datetime.timedelta(days=125)
        start_date = start_date.strftime("%Y%m%d")

    print("_"*50)
    print("开始下载合约分钟数据")
    print("_"*50)

    # 添加下载任务
    global task_list
    task_list = SYMBOLS
    task_list1 = copy.deepcopy(task_list)

    for symbol in task_list1:
        downloadMinuteBarBySymbol(str(symbol), start_date, end_date)

    while task_list:
        # 如果任务列表为空，则说明数据已经全部下载完成
        sleep(2)

    print("_"*50)
    print("合约分钟线数据下载完成")
    print("_"*50)


