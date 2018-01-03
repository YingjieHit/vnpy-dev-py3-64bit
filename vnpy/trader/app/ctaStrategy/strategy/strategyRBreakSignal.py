# -*- coding;utf-8 -*-

"""
R-Break改进策略

1. 标的：国债, 周期：15分钟策略

2.未编辑

编程：张英杰

"""

import datetime
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.signalTemplate import (SignalTemplate,
                                                          BarManager,
                                                          ArrayManager2,
                                                          DailyArrayManager)



########################################################################

class RBreakStrategy5(SignalTemplate):
    """改进型RBreak策略"""
    className = "RBreakStrategy"
    autor = "中融致信"

    def __init__(self, ctaEngine, setting):
        """Constructor"""
        # 策略参数
        self.initDays = 10  # 数据初始化天数
        self.N2 = 8.5
        self.N3 = 5.0
        self.N4 = 6.0
        self.N5 = 7.5
        self.N6 = 4.5
        self.fixedSize = 1  # 每次交易数量

        # 基类的构造方法有读取参数配置的方法故放置在此处
        super(RBreakStrategy5, self).__init__(ctaEngine, setting)


        # 策略变量
        self.intraTradeHigh = 0.0   # 移动止损用的持仓期内最高价
        self.intraTradeLow = 0.0    # 移动止损用的持仓期内最低价
        self.open_price = None     # 最新开仓价格
        self.order_list = []        # 下单列表

        self.date = None      # 日期
        self.pre_date = None  # 上个交易日日期
        # 基础数据获取
        self.HH1 = 0.  # 上个交易日收盘bar最高价
        self.LL1 = 0.  # 上个交易日收盘bar最低价
        self.CC1 = 0.  # 上个交易日收盘价
        self.HH2 = 0.  # 前个交易日收盘bar最高价
        self.LL2 = 0.  # 前个交易日收盘bar最低价

        self.C1 = 0.  # 当日开盘价
        self.MN1 = 0.  # MN1=当日开盘价/2 + (昨日最高+昨日最低+昨日收盘)/6
        self.RANGE1 = 0.  # RANGE1 = (昨日最高-昨日最低)*0.65 + (前日最高-前日最低)*0.35
        self.SIZECK1 = 0.  # SIZECK1 = (当前BAR收盘价 - 当前BAR开盘价)的绝对值/当前BAR收盘价   < 0.5%  振幅不超过0.5%
        self.SIZECK2 = 0.
        #
        self.U2 = 0.  # 追买中轴线
        self.U3 = 0.  # 追买止损线
        self.U4 = 0.  # 卖出止损线
        self.U5 = 0.  # 卖出中轴线
        self.U6 = 0.  # 突破做空

        self.D6 = 0.  # 突破做多
        self.D5 = 0.  # 做多中轴线
        self.D4 = 0.  # 做多止损线
        self.D3 = 0.  # 追卖止损线
        self.D2 = 0.  # 追卖中轴线

    d