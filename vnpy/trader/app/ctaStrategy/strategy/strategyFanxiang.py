# encoding: UTF-8
"""反向操作即可赚钱的10债策略!!!"""

"""
R-Break改进策略

1. 标的：国债, 周期：15分钟策略

2. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略

编程：张英杰

"""
import datetime
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager2,
                                                     DailyArrayManager)


########################################################################

class RBreakStrategy(CtaTemplate):
    """改进型RBreak策略"""
    className = "RBreakStrategy"
    autor = "张英杰"

    # 策略参数
    initDays = 10  # 数据初始化天数
    N2 = 8.5
    N3 = 5.0
    N4 = 6.0
    N5 = 7.5
    N6 = 4.5
    fixedSize = 20  # 每次交易数量

    # 策略变量
    intraTradeHigh = 0.0  # 移动止损用的持仓期内最高价
    intraTradeLow = 0.0  # 移动止损用的持仓期内最低价
    open_price = None  # 最新开仓价格
    order_list = []  # 下单列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'autor',
                 'vtSymbol',

                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',

               ]

    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(RBreakStrategy, self).__init__(ctaEngine, setting)

        # 创建bar管理器(K线合成对象)，用于合成bar和处理自定义周期的bar回调函数
        self.bm = BarManager(onBar=self.onBar, xmin=15, onXminBar=self.onFifteenBar)
        # 创建k线序列管理工具
        self.am = ArrayManager2()
        self.dam = DailyArrayManager()

    def onInit(self):
        """初始化策略，必须由用户继承实现"""
        self.writeCtaLog("%s初始化策略" % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(days=self.initDays)
        # 预处理初始化的bar
        for bar in initData:
            self.onBar(bar)

        # 发出策略状态变化事件
        self.putEvent()

    def onStart(self):
        '''启动策略（必须由用户继承实现）'''
        self.writeCtaLog("%s策略启动" % self.name)

        # 发出策略状态变化事件
        self.putEvent()  # 目前的结论是回测时候该方法为pass，实盘通常用于通知界面更新

    def onStop(self):
        '''停止策略（必须由用户继承实现）'''
        self.writeCtaLog("%s策略停止" % self.name)

        # 发出策略状态变化事件
        self.putEvent()

    def onTick(self, tick):
        '''收到TICK推送，必须由用户继承实现'''
        # 更新tick，合成k线
        self.bm.updateTick(tick)

    def onBar(self, bar):
        """收到bar推送（必须由用户继承实现）"""
        self.bm.updateBar(bar)  # 一分钟一个bar，执行周期大于1分钟的策略在自定义的执行方法里，到时间了由bm.updataBar回调执行

    def onFifteenBar(self, bar):
        '''收到15分钟K线推送的回调函数'''

        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        # 如果k先还没有初始化完成，就不执行
        if not am.inited:
            return

        # 保存日K数据
        dam = self.dam
        dam.updateBar(bar)
        if not dam.inited:
            return

        # 基础数据获取
        HH1 = dam.high[-2]  # 上个交易日最高价
        LL1 = dam.low[-2]  # 上个交易日最低价
        CC1 = dam.close[-2]  # 上个交易日收盘价
        HH2 = dam.high[-3]  # 前个交易日最高价
        LL2 = dam.low[-3]  # 前个交易日最低价

        C1 = dam.close[-1]  # 当日收盘价
        MN1 = C1 / 2 + (HH1 + LL1 + CC1) / 6  # MN1=当日开票价/2 + (昨日最高+昨日最低+昨日收盘)/6
        RANGE1 = (HH1 - LL1) * 0.65 + (HH2 - LL2) * 0.35  # RANGE1 = (昨日最高-昨日最低)*0.65 + (前日最高-前日最低)*0.35
        SIZECK1 = abs(
            bar.close - bar.open) / bar.close < 5 / 1000  # SIZECK1 = (当前BAR收盘价 - 当前BAR开盘价)的绝对值/当前BAR收盘价   < 0.5%  振幅不超过0.5%
        SIZECK2 = abs(bar.close - bar.open) / bar.close < 5 / 1000

        # 参数计算
        U2 = MN1 + RANGE1 * self.N2 / 10  # 追买中轴线
        U3 = MN1 + RANGE1 * self.N3 / 10  # 追买止损线
        U4 = MN1 + RANGE1 * self.N4 / 10  # 卖出止损线
        U5 = MN1 + RANGE1 * self.N5 / 10  # 卖出中轴线
        U6 = MN1 + RANGE1 * self.N6 / 10  # 突破做空

        D6 = MN1 - RANGE1 * self.N6 / 10  # 突破做多
        D5 = MN1 - RANGE1 * self.N5 / 10  # 做多中轴线
        D4 = MN1 - RANGE1 * self.N4 / 10  # 做多止损线
        D3 = MN1 - RANGE1 * self.N3 / 10  # 追卖止损线
        D2 = MN1 - RANGE1 * self.N2 / 10  # 追卖中轴线

        # 交易决策
        # 1.观察区突破开仓
        time_now = bar.datetime.time()
        time_0915 = time_now.replace(hour=9, minute=15, second=0)
        time_1429 = time_now.replace(hour=14, minute=29, second=0)
        time_1500 = time_now.replace(hour=15, minute=0, second=0)
        time_last = time_now.replace(hour=15, minute=14, second=0)

        # 空仓
        if self.pos == 0:
            # 持有期内最高最低价
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            # self.open_price = None

            # 9:50 -- 14:29 之间
            if time_now >= time_0915 and time_now <= time_1429:
                # 价格下穿U6，股价前30个BAR（不包括当前）的收盘最高值大于U5，当前BAR振幅小于0.5%，开空头
                if am.close[-1] < U6 and am.close[-2] >= U6 and am.close[-3] > U6 and am.close[
                                                                                      -31: -1].max() > U5 and SIZECK2:
                    self.cancelAll()
                    self.short(price=bar.close - 0.01, volume=self.fixedSize)
                    # self.open_price = bar.close
                # 价格上穿D6，最近30个BAR收盘价（不包括当前）的最小值小于D5，当前BAR振幅小于0.5%，开多头
                if am.close[-1] > D6 and am.close[-2] <= D6 and am.close[-3] < D6 and am.close[
                                                                                      -31: -1].min() < D5 and SIZECK1:
                    self.cancelAll()
                    self.buy(price=bar.close + 0.01, volume=self.fixedSize)
                    # self.open_price = bar.close

            # 时间在9:50和14:29之间 TIME>0915 && TIME<1500
            if time_now >= time_0915 and time_now <= time_1500:
                # && CROSSUP(C,U2) && SIZECK1,BK 突破开仓
                if am.close[-1] > U2 and am.close[-2] <= U2 and am.close[-3] < U2 and SIZECK1:
                    self.cancelAll()
                    self.buy(price=bar.close + 0.01, volume=self.fixedSize)
                    # self.open_price = bar.close
                # CROSSDOWN(C,D2) && SIZECK2,SK;
                elif am.close[-1] < D2 and am.close[-2] >= D2 and am.close[-3] > D2 and SIZECK2:
                    self.cancelAll()
                    self.short(price=bar.close - 0.01, volume=self.fixedSize)
                    # self.open_price = bar.close

        # 持有多头：
        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

            #  价格上穿U6，止盈
            if am.close[-1] > U6 and am.close[-2] <= U6:
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)
            # 价格下穿D4，止损
            elif am.close[-1] < D4 and am.close[-2] >= U6:
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)
            # 价格下穿U3，平仓
            elif am.close[-1] < U3 and am.close[-2] >= U3:
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)
            # 上一次买入到现在（不含当前bar）的最高价 > 买入价格 * （1 + 0.002)， 并且 (当前收盘价 - 成本）<= （到目前为止收盘最高价 - 成本）* 0.5

            elif self.intraTradeHigh > self.open_price * (1 + 0.002) and (am.close[-1] - self.open_price) <= (
                self.intraTradeHigh - self.open_price) * 0.5:
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)
            # 价格下穿 开仓价格 * (1 - 0.9/1000) 止损
            elif am.close[-1] < self.open_price * (1 - 0.9 / 1000) and am.close[-2] >= self.open_price * (
                1 - 0.9 / 1000):
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)


        # 持有空头;
        elif self.pos < 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

            # 价格下穿D6，平掉空头，止盈
            if am.close[-1] < D6 and am.close[-2] >= D6:
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)
            # 价格上穿U4，平掉空头（止损）
            elif am.close[-1] > U4 and am.close[-2] <= U4:
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)
            # 价格上穿D3，平仓
            elif am.close[-1] > D3 and am.close[-2] <= D3:
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)
            # 上一次买入到现在（不含当前bar）的最低价 < 买入价格 * （1 + 0.002)， 并且 （成本 - 当前收盘价）<= （成本 - 到目前为止收盘最低价）* 0.5  止盈
            elif self.intraTradeLow < self.open_price * (1 - 0.002) and self.open_price - bar.close <= (
                self.open_price - self.intraTradeLow) * 0.5:
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)
            # 价格上 开仓价格 * (1 + 0.9 / 1000) 止损
            elif am.close[-1] > self.open_price * (1 + 0.9 / 1000) and am.close[-2] <= self.open_price * (
                1 + 0.9 / 1000):
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)

        # 当天收盘则平仓所有
        if time_now >= time_last:
            self.closeAllPosition()

        self.putEvent()

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    def onTrade(self, trade):
        """收到交易发生事件推送"""
        if trade.offset == "平仓":
            self.open_price = None

        if trade.offset == "开仓":
            self.open_price = trade.price

        self.putEvent()

    def onStopOrder(self, so):
        """收到停止单事件推送"""
        self.putEvent()

    def closeAllPosition(self, bar):
        self.cancelAll()
        if self.pos > 0:
            self.sell(price=bar.close - 0.01, volume=self.fixedSize)
        elif self.pos < 0:
            self.cover(price=bar.close + 0.01, volume=self.fixedSize)







