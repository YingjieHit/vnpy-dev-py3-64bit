# encoding: UTF-8

"""
夜盘尾盘买，早盘卖策略:
1. 22:58 的价格 - 22:30的价格 > 0.5% * 22:58 的价格，买入开仓， 对应22:58的价格 - 22:30的价格 < 0.5% * 22:58 的价格，卖出开仓
2. 22:58 的价格 - 21:00的价格 > 0.5% * 22:58 的价格，买入开仓， 对应22:58的价格 - 21:00的价格 > 0.5% * 22:58 的价格，卖出开仓
3. 9:05 强制平仓
"""
import datetime

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager2)


#######################################################################################
class LastGoldStrategy(CtaTemplate):
    """基于King Keltner通道的交易策略"""
    className = 'LastGoldStrategy'
    author = '中融致信投资技术部'

    # 策略参数
    initDays = 10  # 数据初始化天数


    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(LastGoldStrategy, self).__init__(ctaEngine, setting)

        self.bm = BarManager(self.onBar)  # 创建K线合成器对象
        # self.am = ArrayManager2(size=120)

        self.fixedSize = 1           # 每次交易的数量
        self.night_open_price = None # 夜盘开盘价 (21:00)
        self.night_mid_price = None  # 盘中参考价（22:30）


    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog('%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        #     self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog('%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog('%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 保存K线数据
        # am = self.am
        # am.updateBar(bar)
        # 如果k先还没有初始化完成，就不执行
        # if not am.inited:
        #     return
        # 获取当前时间
        time_now = bar.datetime.time()
        # 21:00:00 记住开盘价
        if time_now == datetime.time(hour=21,minute=0,second=0):
            self.night_open_price = bar.open
        # 记住22:30:00的价格
        elif time_now == datetime.time(hour=22,minute=30,second=0):
            self.night_mid_price = bar.open

        # 没有加载到比较数据，直接返回
        if self.night_open_price is None or self.night_mid_price is None:
            return

        # 22:58分开仓
        if time_now == datetime.time(hour=22,minute=58,second=0):
            if self.pos == 0:
                # 趋势: 1向上， -1向下，0无趋势
                trend_l = 0 # 长趋势
                trend_s = 0 # 短趋势
                if bar.close - self.night_mid_price > bar.close * 0.005:
                    trend_s = 1
                if bar.close - self.night_open_price > bar.close * 0.005:
                    trend_l = 1
                if bar.close - self.night_mid_price < 0 - bar.close * 0.005:
                    trend_s = -1
                if bar.close - self.night_open_price < 0 - bar.close * 0.005:
                    trend_l = -1

                # 有其中一个趋势或者趋势共振
                if trend_s + trend_l >= 1:
                    self.buy(price=bar.close + 0.0, volume=self.fixedSize)

                elif trend_s + trend_l <= -1:
                    self.short(price=bar.close - 0.0, volume=self.fixedSize)

        # 9:05平仓所有
        elif time_now == datetime.time(hour=9, minute=4, second=0):
            self.closeAllPosition(bar)

        # 如果没有开仓成功则撤单
        elif time_now == datetime.time(hour=23, minute=28, second=0):
            self.cancelAll()



    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    def onTrade(self, trade):
        """收到交易发生事件推送"""
        pass

    def onStopOrder(self, so):
        """收到停止单事件推送"""
        self.putEvent()

    def closeAllPosition(self, bar):
        """平掉所有仓位"""
        self.cancelAll()
        if self.pos > 0:
            self.sell(price=bar.close - 3.0, volume=self.fixedSize)
        elif self.pos < 0:
            self.cover(price=bar.close + 3.0, volume=self.fixedSize)



