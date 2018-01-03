# -*- coding: utf-8 -*-
"""
苹果期货新上市策略
1. 重心 = （open + high + low + close） / 4
2. 如果当期bar重心 > 上一个bar重心 ，并且当期bar的close > 当期bar重心，认为是上升趋势，反之判断下降趋势
3. 上升趋势保持持有多头，下降趋势保持持有空头，趋势反转做反手，判断不出趋不做动作（有仓不平，无仓不开）
4. 追单成交，如果不成交，下一个bar直接撤单。
5. 收盘前全部平仓（2:58）
"""

import datetime

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)


class AppleStartStrategy2(CtaTemplate):
    """苹果期货新上市策略"""
    className = 'AppleStartStrategy2'
    author = '中融致信投资技术部'

    # 策略参数
    # 3900成交价格
    initDays = 1 # 数据初始化天数
    open_pos_time = datetime.time(hour=9, minute=1, second=0)    # 开仓时间
    stop_open_pos_time = datetime.time(hour=14, minute=54, second=0) # 停止开仓时间
    close_pos_time = datetime.time(hour=14, minute=58, second=0) # 清仓时间
    fixedSize = 1  # 每次交易的数量

    # faxing_price = 7800.00  # 苹果发行价格
    # faxing_price = 3801.00  # 螺纹结算价格
    open_slip = 0
    close_slip = 0


    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(AppleStartStrategy2, self).__init__(ctaEngine, setting)

        self.bm = BarManager(self.onBar)  # 创建K线合成器对象
        self.am = ArrayManager(size=100)

        self.pre_zhongxin = None  # 上一个bar的重心
        # self.zhangting_price = round(self.faxing_price * 1.1, 2)  # 涨停价
        # self.dieting_price = round(self.faxing_price * 0.9, 2)    # 跌停价

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog('%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

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

    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        # 如果k先还没有初始化完成，就不执行
        if not am.inited:
            return

        # 先撤销之前没有成交的单子
        self.cancelAll()

        # 获取当前时间
        time_now = bar.datetime.time()

        # 收集计算数据
        zhongxin = (bar.open + bar.high + bar.low + bar.close) / 4  # 重心
        # 第一个bar先略过
        if self.pre_zhongxin is None:
            self.pre_zhongxin = zhongxin
            return

        # 开仓时间
        if time_now >= self.open_pos_time and time_now < self.stop_open_pos_time:
            # 判断该做空还是做多
            trend = 0  # 趋势，-1 空， 0 无趋势， 1 多
            if zhongxin > self.pre_zhongxin and bar.close > zhongxin:
                trend = 1
            elif zhongxin < self.pre_zhongxin and bar.close < zhongxin:
                trend = -1

            if self.pos == 0:
                # 空仓趋势多头直接开多
                if trend == 1:
                    # self.buy(price=bar.close+self.open_slip, volume=self.fixedSize)
                    self.short(price=bar.close - self.open_slip, volume=self.fixedSize)
                # 空仓趋势空头直接开空
                elif trend == -1:
                    # self.short(price=bar.close-self.open_slip, volume=self.fixedSize)
                    self.buy(price=bar.close + self.open_slip, volume=self.fixedSize)

            # 持有多投仓位
            elif self.pos > 0:
                # 趋势反转，反手做空
                # if trend == -1:
                #     self.sell(price=bar.close-self.close_slip, volume=self.fixedSize)
                #     self.short(price=bar.close-self.open_slip, volume=self.fixedSize)
                if trend == 1:
                    self.sell(price=bar.close-self.close_slip, volume=self.fixedSize)
                    self.short(price=bar.close-self.open_slip, volume=self.fixedSize)

            # 持有空头仓位
            elif self.pos < 0:
                # 趋势反转，反手做多
                # if trend == 1:
                if trend == -1:
                    self.cover(price=bar.close+self.close_slip, volume=self.fixedSize)
                    self.buy(price=bar.close+self.open_slip, volume=self.fixedSize)

        # 尾盘强制平仓
        if time_now >= self.close_pos_time:
            if self.pos != 0:
                self.closeAllPosition(bar)

        # 为下一个bar数据做准备
        self.pre_zhongxin = zhongxin




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
            self.sell(price=bar.close-self.close_slip, volume=self.fixedSize)
        elif self.pos < 0:
            self.cover(price=bar.close+self.close_slip, volume=self.fixedSize)
