# encoding: UTF-8

"""
对接wind，目前仅用于采集合约的历史数据
1.wind数据会把开盘集中竞价的数据也显示，而vnpy和文华财经则把集中竞价的成交量与第一根k线做了合成，故需要清洗数据:
2.wind下午收盘会多出来一个bar,需要删除
"""
import time
from threading import Thread

from WindPy import w
from vnpy.trader.vtObject import VtBarData

from .field_dict import WIND_FIELD_DICT
from .utils import split_dt_list
# from .utils import get_modified_date

# wind数据字段
wind_data_field = "open,high,low,close,volume,oi"

# 连接wind
w.start()
while not w.isconnected():
    time.sleep(0.001)


class WindApi():
    """wind行情接口"""

    def __init__(self):
        """constructor"""
        pass



    def download_minute_bar(self, symbol, start_date, end_date, data_callback_func=None, task_callback_func=None):
        """
        下载数据
        :param symbol: 合约名称
        :param start_date: 起始时间
        :param end_date: 终止时间
        :param data_callback_func: 数据回调函数，采集行情后触发,，用于存储数据
        :param task_callback_func: 任务回调函数，用于
        :return:
        """
        # 多线程执行
        def func():
            dt_tuple = split_dt_list(start_date, end_date)
            # 分时间段采集
            print("*" * 20 + "开始采集合约" + symbol + " " + start_date + " -- " + end_date + " 时段数据" + "*" * 20)
            for sub_start_date, sub_end_date in dt_tuple:
                # 被分段的时间
                minute_bar_list = self.get_minute_bar(symbol, sub_start_date, sub_end_date)
                if minute_bar_list:
                    data_callback_func(symbol, minute_bar_list)
                    print("合约"+ symbol + " "  + sub_start_date + " -- " + sub_end_date + " 时段数据采集完毕")
            print("*"*20 + "合约" + symbol + " " + start_date + " -- " + end_date + " 时段数据采集完毕"+ "*"*20)
            print("")
            task_callback_func(symbol)

        t = Thread(target=func)
        t.setDaemon(True)
        t.start()


    # 从wind请求数据
    def get_minute_bar(self, symbol, start_date, end_date):
        """
        从wind请求合约历史数据
        :param symbol:      合约代码
        :param start_date:  format: %Y-%m-%d %H:%S:%M
        :param end_date:    format: %Y-%m-%d %H:%S:%M
        :return:
        """
        # 将合约代码转换为wind合约代码
        wind_code = self.get_wind_code_by_symbol(symbol)
        # 获取数据
        wsi_data = w.wsi(wind_code, wind_data_field, start_date, end_date, "")

        # 判断是否正常获取数据
        error_code = wsi_data.ErrorCode
        if error_code != 0:
            # 无数据，可能该合约在该时段还没开始交易
            if error_code == -40520007:
                print("合约" + wind_code + "在 " + start_date + " -- " + end_date + " 时段还未开始交易")
                return []

            print(wind_code + u" wind数据获取错误，错误代码：")
            print(error_code)
            raise ValueError("get data from wind error")

        times = wsi_data.Times  # 时间列表
        # code = wsi_data.Codes[0]  # 合约代码
        data = wsi_data.Data  # 核心历史数据
        # modified_date = get_modified_date()  # 更新时间用于更新数据,用不用待定

        bar_list = []
        for i, dt in enumerate(times):
            bar = VtBarData()
            bar.vtSymbol = symbol  # vt系统代码，需要code转换
            bar.symbol = symbol    # 代码
            # bar.exchange = None  # 交易所代码，可以无
            bar.open = data[0][i]
            bar.high = data[1][i]
            bar.low = data[2][i]
            bar.close = data[3][i]
            bar.volume = data[4][i]
            bar.openInterest = data[5][i]

            bar.datetime = times[i]
            bar.date = bar.datetime.strftime("%Y%m%d")        # bar开始的日期
            bar.time = bar.datetime.strftime("%H:%M:%S")      # 时间

            bar_list.append(bar)

        return bar_list

    def get_wind_code_by_symbol(self, symbol):
        """
        根据合约代码获取wind对应的代码
        :return:
        """
        field_dict = WIND_FIELD_DICT
        # 截取合约名称不含日期
        if len(symbol) == 6:
            symbol_head = symbol[0: 2]
        elif len(symbol) == 5:
            symbol_head = symbol[0:1]
        else:
            raise ValueError(u"合约名称长度不合法")

        # 截取合约日期
        symbol_date = symbol[-4:]

        # 获取wind合约信息
        symbol_info_list = field_dict[symbol_head]
        # 获取合约名称和交易所代码
        wind_symbol_head = symbol_info_list[0]
        wind_exchange = symbol_info_list[1]  # 交易所代码

        # 合成windcode
        wind_code = wind_symbol_head + symbol_date + "." + wind_exchange

        return wind_code




