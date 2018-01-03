# encoding: UTF-8
"""wind数据清洗"""


import json
import datetime
from math import isnan

from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.vtObject import VtBarData
from tradingTimeSetting import TRADING_TIME, ERROR_TIME

# 加载配置
config = open("config.json")
setting = json.load(config)

MONGO_HOST = setting["MONGO_HOST"]
MONGO_PORT = setting["MONGO_PORT"]
SYMBOLS = setting["SYMBOLS"]

mc = MongoClient(MONGO_HOST, MONGO_PORT)  # Mongo连接
db = mc[MINUTE_DB_NAME]   # 数据库

def repairData(start_date, end_date):
    """修补数据，主要是修补交易时间内为nan的数据
       如果某一个bar成交量为0，那么所有数据包括持仓量和成交量都为nan
    """
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = datetime.datetime.strptime(end_date, "%Y%m%d")  - datetime.timedelta(days=125)
        start_date = start_date.strftime("%Y%m%d")
    # 再往前取10天的数据，以保证有足够的数据去修复之后的数据
    start_date = datetime.datetime.strptime(start_date, "%Y%m%d") - datetime.timedelta(days=10)
    start_date = start_date.strftime("%Y%m%d")

    print("_"*50)
    print("开始修补合约分钟数据")
    print("_"*50)

    # 添加修补任务
    task_list = SYMBOLS

    for symbol in task_list:
        # 获取合约开头
        symbol_head = symbol[0:2] if len(symbol) == 6 else symbol[0:1]

        col = db[symbol]
        field = ["open", "high", "low", "close", "volume", "datetime", "openInterest", "date", "time"]

        flt = {"date": {"$gte": start_date, "$lte": end_date}}

        cur = col.find(flt, field).sort("datetime", 1)

        # 遍历数据找到要修复的数据
        first_good_flag = False  # 第一次找到好的数据
        data_to_repair_list = list()
        for d in cur:
            # 寻找第一个好的数据
            if first_good_flag is False:
                if not isnan(d["volume"]):
                    first_good_flag = True
                    # last_open = d["open"]
                    last_high = d["high"]
                    last_low = d["low"]
                    last_close = d["close"]
                    # last_volume = d["volume"]
                    last_openInterest = d["openInterest"]

                continue

            else:
                if isnan(d["volume"]):
                    bar = VtBarData()
                    bar.symbol = symbol
                    bar.vtSymbol = symbol
                    bar.open = last_close
                    bar.high = last_high
                    bar.low = last_low
                    bar.close = last_close
                    bar.volume = 0
                    bar.openInterest = last_openInterest
                    bar.datetime = d["datetime"]
                    bar.date = d["date"]
                    bar.time = d["time"]
                    data_to_repair_list.append(bar)
                else:
                    last_high = d["high"]
                    last_low = d["low"]
                    last_close = d["close"]
                    last_openInterest = d["openInterest"]

        for bar in data_to_repair_list:
            d = bar.__dict__
            flt = {"datetime": bar.datetime}
            col.replace_one(flt, d, True)

    print("_" * 50)
    print("合约分钟线数据修复完成")
    print("_" * 50)




def cleanData(start_date, end_date):
    """
    清洗数据，主要目的是清洗头尾分钟k线，删除交易时间之外的数据
    :param start_date: %Y%m%d
    :param end_date:   %Y%m%d
    :return:
    """
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = datetime.datetime.strptime(end_date, "%Y%m%d")  - datetime.timedelta(days=125)
        start_date = start_date.strftime("%Y%m%d")

    print("_"*50)
    print("开始清洗合约分钟数据")
    print("_"*50)

    # 添加清洗任务
    task_list = SYMBOLS

    for symbol in task_list:
        # 获取合约开头
        symbol_head = symbol[0:2] if len(symbol) == 6 else symbol[0:1]
        # 获取关键时间
        symbol_trading_time = TRADING_TIME[symbol_head]
        open_time = symbol_trading_time[0]
        close_time = symbol_trading_time[1]
        ji_time = (datetime.datetime.strptime(open_time, "%H:%M:%S") - datetime.timedelta(minutes=1)).strftime("%H:%M:%S")
        pre_close_time = (datetime.datetime.strptime(close_time, "%H:%M:%S") - datetime.timedelta(minutes=1)).strftime("%H:%M:%S")

        # 获取数据库集合
        col = db[symbol]
        field = ["open", "high", "low", "close", "volume", "datetime"]

        # 处理集合竞价数据
        condition = {"time": ji_time, "date": {"$gte": start_date, "$lte": end_date}}
        ji_data = list(col.find(condition, field).sort("datetime", 1))  # 从小到大排列
        condition = {"time": open_time, "date": {"$gte": start_date, "$lte": end_date}}
        open_data = list(col.find(condition, field).sort("datetime", 1))

        for i, v in enumerate(ji_data):
            if len(ji_data) != len(open_data):
                break
            if not isnan(ji_data[i]["volume"]) and not isnan(open_data[i]["volume"]):
                # 仅仅成交量相加
                volume = ji_data[i]["volume"] + open_data[i]["volume"]
                # 开盘价替换
                open = ji_data[i]["open"]
                condition = {"datetime": open_data[i]["datetime"]}
                col.update(condition, {"$set":{"volume": volume, "open": open}})


        # 处理收盘数据
        condition = {"time": pre_close_time, "date": {"$gte": start_date, "$lte": end_date}}
        pre_close_data = list(col.find(condition, field).sort("datetime", 1))  # 从小到大排列
        condition = {"time": close_time, "date": {"$gte": start_date, "$lte": end_date}}
        close_data = list(col.find(condition, field).sort("datetime", 1))

        for i, v in enumerate(pre_close_data):
            if len(pre_close_data) != len(close_data):
                break
            if not isnan(pre_close_data[i]["volume"]) and not isnan(close_data[i]["volume"]):
                # 成交量相加
                volume = pre_close_data[i]["volume"] + close_data[i]["volume"]
                high = max(pre_close_data[i]["high"], close_data[i]["high"])
                low = max(pre_close_data[i]["low"], close_data[i]["low"])
                close = close_data[i]["close"]
                condition = {"datetime": pre_close_data[i]["datetime"]}
                col.update(condition, {"$set": {"volume": volume, "high": high, "low": low, "close": close}})


        col.delete_many({"symbol": symbol, "date": {"$gte": start_date, "$lte": end_date}, "time": {"$in": [ji_time, close_time]}})

        error_times = ERROR_TIME.get(symbol_head, [])
        # 清洗非交易时间的
        for s_time, e_time in error_times:
            col.delete_many({"symbol": symbol, "date": {"$gte": start_date, "$lte": end_date}, "time": {"$gte":s_time, "$lte": e_time}})

    print("_"*50)
    print("合约分钟线数据清洗完成")
    print("_"*50)




if __name__ == '__main__':
    # cleanData("20170101", "20171231")
    repairData("20170101", "20171231")

