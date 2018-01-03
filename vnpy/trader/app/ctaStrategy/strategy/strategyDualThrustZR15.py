# -*- coding;utf-8 -*-
"""
国债DualTrust策略
编程：张英杰
"""

import datetime
import talib
import numpy as np
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager2,
                                                     DailyArrayManager)


class DualThrustStrategyZR15(CtaTemplate):
    """DualThrust策略"""
    className = "DualThrustStrategyZR15"
    autor = "张英杰"

    # 策略参数
    initDays = 30 # 数据初始化天数
    X1 = 1.3
    X2 = 1.5

    fixedSize = 1  # 每次交易数量

    open_time = datetime.time(hour=9, minute=15, second=0)   # 开仓开始时间
    close_time = datetime.time(hour=15, minute=0, second=0)  # 开仓结束时间

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
        super(DualThrustStrategyZR15, self).__init__(ctaEngine, setting)

        # 创建bar管理器(K线合成对象)，用于合成bar和处理自定义周期的bar回调函数
        self.bm = BarManager(onBar=self.onBar, xmin=15, onXminBar=self.onFifteenBar)
        # 创建k线序列管理工具
        self.am = ArrayManager2(size=300)
        self.dam = DailyArrayManager()

        # 创建变量
        # self.NN = None  # 昨天离今天的k线个数,即目前为今天的第几根bar，文华需要，nvpy不需要
        self.HH1 = None  # 昨天所有bar的收盘最高价
        self.LL1 = None  # 昨天所有bar的收盘价最低价
        self.CC1 = None  # 昨天收盘价

        self.HH2 = None  # 前天所有bar最高收盘价
        self.LL2 = None  # 前天所有bar最低收盘价
        self.CC2 = None  # 前天收盘价

        self.RANGE0 = None  # 这两天的波幅
        self.RANGE1 = None  #

        self.YJS = None  # 昨天的结算价
        self.DTC = None  # 根据昨天计算价判断今天是否会有跌停和涨停的风险

        self.OO1 = None  # 今天的开盘价
        self.MN1 = None  # 中轴价  偏向于趋势

        self.UBUY = None  # 追买中轴线
        self.DSELL = None  # 追卖中轴线

        self.USELL = None  # 卖出中轴线
        self.DBUY = None   # 做多中轴线

        self.USELL1 = None  # 卖出中轴线
        self.DBUY1 = None   # 做多中轴线

        self.DGKX = np.zeros(68*3)
        self.DGKX_count = 0
        self.SIZEK = None

        self.ZS = None
        self.KK = None

        self.now_date = None  # 当前日期
        self.pre_date = None  # 上个交易日日期
        self.now_time = None  # 当前时间

        self.last_trade_price = None    # 最后成交价格

        self.intraTradeHigh = None  # 持有期内最高价
        self.intraTradeLow = None  # 持有期内最低价

        # 为了计算DGKX 和 SIZEK


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
        self.putEvent() # 目前的结论是回测时候该方法为pass，实盘通常用于通知界面更新

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
        self.bm.updateBar(bar) # 一分钟一个bar，执行周期大于1分钟的策略在自定义的执行方法里，到时间了由bm.updataBar回调执行

    def onFifteenBar(self, bar):
        """收到5分钟bar推送"""
        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        # 保存日K数据
        dam = self.dam
        dam.updateBar(bar)

        self.now_time = bar.datetime.time()
        # 初始化
        if self.now_date is None:
            self.now_date = bar.date
            return
        # 日期改变
        elif self.now_date != bar.date:
            self.pre_date = self.now_date
            self.now_date = bar.date

            # 计算变量
            # 计算昨天、前天所有bar最高、最低收盘价，昨天结算价
            self.HH2 = self.HH1
            self.LL2 = self.LL1
            self.CC2 = self.CC1

            self.HH1 = am.close[-2]
            self.LL1 = am.close[-2]
            self.CC1 = am.close[-2]

            i = -3
            while am.date[i] == self.pre_date:
                if am.close[i] > self.HH1:
                    self.HH1 = am.close[i]
                if am.close[i] < self.LL1:
                    self.LL1 = am.close[i]
                i -= 1

            # 计算这两天的波幅
            if self.HH1 is not None and self.HH2 is not None:
                self.RANGE0 = (((self.HH1 - self.LL1) * 0.65 + (self.HH2 - self.LL2) * 0.35) / am.sma(68 * 2, array=True)[-2]) * 100
                self.RANGE1 = 6 if self.RANGE0 > 6 else self.RANGE0

            # 昨天的结算价
            tmp_sum = 0.
            volume_sum = 0.
            for i in range(-2, -2 - 15, -1):
                tmp_sum += self.am.close[i] * self.am.volume[i]
                volume_sum += self.am.volume[i]

            self.YJS = tmp_sum / volume_sum
            # 获取今日开盘价
            self.OO1 = bar.open

        # 数据足以支持计算DGKX
        if am.count >= 68 * 2:
            self.DGKX[0: self.DGKX.size-1] = self.DGKX[1: self.DGKX.size]
            if abs(bar.high - bar.low) / bar.close * 10000 < 4:
                self.DGKX[-1] = talib.SMA(abs(am.close-am.open), 68*2)[-1]
            else:
                self.DGKX[-1] = abs(bar.close - bar.open)
            self.DGKX_count += 1

            # 数据足以支持计算SIZEK
            if self.DGKX_count >= 68 * 3:
                self.SIZEK = talib.SMA(self.DGKX, 68*3)[-1] / talib.SMA(self.am.close, 68*3)[-1] * 1000
                self.ZS = (self.SIZEK ** 0.5) * 2
                self.KK = abs(bar.close - bar.open) / bar.open < 0.006

        # 如果k线还没有初始化完成，就不执行
        if not am.inited:
            return
        # 如果日k线还没有初始化完成，就不执行
        if not dam.inited:
            return
        #
        # if bar.date == "20171215":
        #     print(1)

        # 根据昨日计算价判断是否有涨停和跌停风险
        self.DTC = bar.close > self.YJS * (1 - 0.085) and bar.close < self.YJS * (1 + 0.085)


        self.MN1 = (self.OO1 + (self.HH1 + self.LL1 + self.CC1) / 3) / 2    # 中轴价，偏向于趋势

        self.UBUY = self.MN1 * (1 + self.X1 * self.RANGE1 / 100)    # 追买中轴线
        self.DSELL = self.MN1 * (1 - self.X2 * self.RANGE1 / 100)   # 追买中轴线

        self.USELL = self.MN1 * (1 + 1.3 * self.RANGE1 / 100)   # 卖出中轴线
        self.DBUY = self.MN1 * (1 - 1.6 * self.RANGE1 / 100)    # 做多中轴线

        self.USELL1 = self.USELL * (1 + 0.2 * self.RANGE1 / 100)  # 卖出中轴线
        self.DBUY1 = self.DBUY * (1 - 0.2 * self.RANGE1 / 100)    # 做多中轴线



        # 开仓时间

        if self.pos == 0:
            self.intraTradeHigh = bar.close
            self.intraTradeLow = bar.close

            if self.now_time >= self.open_time and self.now_time <= self.close_time:
                # 金叉开仓
                if self.am.close[-1] > self.UBUY and self.am.close[-2] <= self.UBUY and self.am.close[-3] < self.UBUY and self.KK:
                    self.cancelAll()
                    self.buy(price=bar.close+0.01, volume=self.fixedSize)
                # 死叉做空
                elif self.am.close[-1] < self.DSELL and self.am.close[-2] >= self.DSELL and self.am.close[-3] > self.DSELL and self.KK:
                    self.cancelAll()
                    self.short(price=bar.close-0.01, volume=self.fixedSize)

        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.close)
            self.intraTradeLow = min(self.intraTradeLow, bar.close)
            is_sell = False

            if self.intraTradeHigh > self.last_trade_price * (1 + self.ZS/1000*3) and bar.close - self.last_trade_price <= (self.intraTradeHigh - self.last_trade_price) * 0.4:
                is_sell = True
            if self.intraTradeHigh > self.last_trade_price * (1 + self.ZS/1000*6) and bar.close - self.last_trade_price <= (self.intraTradeHigh - self.last_trade_price) * 0.5:
                is_sell = True

            yuzhi = self.last_trade_price * (1 - self.ZS/1000) # 阈值缓存
            if self.am.close[-1] < yuzhi and self.am.close[-2] >= yuzhi:
                is_sell = True
            yuzhi = self.last_trade_price * (1 + 10 * self.ZS / 1000)
            if self.am.close[-1] > yuzhi and self.am.close[-2] <= yuzhi:
                is_sell = True
            if is_sell:
                self.cancelAll()
                self.sell(price=bar.close - 0.01, volume=self.fixedSize)

        elif self.pos < 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.close)
            self.intraTradeLow = min(self.intraTradeLow, bar.close)
            is_cover = False

            if self.intraTradeLow < self.last_trade_price * (1 - self.ZS/1000*3) and self.last_trade_price - bar.close <= (self.last_trade_price - self.intraTradeLow) * 0.5:
                is_cover = True
            if self.intraTradeLow < self.last_trade_price * (1 - self.ZS/1000*6) and self.last_trade_price - bar.close <= (self.last_trade_price - self.intraTradeLow) * 0.7:
                is_cover = True

            yuzhi = self.last_trade_price * (1 + self.ZS/1000)
            if self.am.close[-1] > yuzhi and self.am.close[-2] <= yuzhi:
                is_cover = True
            yuzhi = self.last_trade_price * (1 - 10 * self.ZS / 1000)
            if self.am.close[-1] < yuzhi and self.am.close[-2] >= yuzhi:
                is_cover = True
            if is_cover:
                self.cancelAll()
                self.cover(price=bar.close + 0.01, volume=self.fixedSize)


    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    def onTrade(self, trade):
        """收到交易发生事件推送"""
        self.last_trade_price = trade.price
        print("发生交易")
        print(trade.__dict__)
        print("\n")
        self.putEvent()

    def onStopOrder(self, so):
        """收到停止单事件推送"""
        self.putEvent()

    def closeAllPosition(self, bar):
        self.cancelAll()
        if self.pos > 0:
            self.sell(price=bar.close - 0.01, volume=self.fixedSize)
        elif self.pos < 0:
            self.cover(price=bar.close  + 0.01, volume=self.fixedSize)
