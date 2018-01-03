# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
在原CtaTemplate类的基础上增加了必要的流程，保证策略编写规范化
'''

import datetime

import numpy as np
import talib

from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData

from .ctaBase import *


class CtaTemplate(object):
    """CTA策略模板"""

    # 策略类的名称和作者
    className = 'CtaTemplate'
    author = EMPTY_UNICODE

    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME

    # 策略的基本参数
    name = EMPTY_UNICODE  # 策略实例名称
    vtSymbol = EMPTY_STRING  # 交易的合约vt系统代码
    productClass = EMPTY_STRING  # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING  # 货币（只有IB接口需要）

    # 策略的基本变量，由引擎管理
    inited = False  # 是否进行了初始化
    trading = False  # 是否启动交易，由引擎管理
    pos = 0  # 持仓情况

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """收到停止单推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def buy(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, stop)

    # ----------------------------------------------------------------------
    def short(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, stop)

        # ----------------------------------------------------------------------

    def cover(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, stop)

    # ----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderIDList = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderIDList = self.ctaEngine.sendOrder(self.vtSymbol, orderType, price, volume, self)
            return vtOrderIDList
        else:
            # 交易停止时发单返回空字符串
            return []

    # ----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return

        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤单"""
        self.ctaEngine.cancelAll(self.name)

    # ----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)

    # ----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)

    # ----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    # ----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)

    # ----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType


########################################################################
class SignalTemplate(object):
    """
    中融策略模板，实现了策略的标准化，其特点包括：
    1. 交易信号与交易下单的分离。
    2. 重启系统数据不丢失。
    3. 重启系统错过下单时机自动补单（价格离开仓时机一定范围内补开仓单子，必然补平仓单子）。
    4. 支持一个策略多个并发
    5. 仅支持bar策略
    6. 仅支持全仓买卖
    """
    # 策略类的名称和作者
    className = 'SignalTemplate'
    author = "中融致信"

    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME


    def __init__(self, ctaEngine, setting):
        """
        Constructor
        :param ctaEngine: # cta执行引擎
        :param setting:   # 设置
        """
        self.ctaEngine = ctaEngine  # cta策略引擎
        self.initDays = 10  # 数据初始化天数

        # 策略的基本参数
        self.name = EMPTY_UNICODE  # 策略实例名称
        self.vtSymbol = EMPTY_STRING  # 交易的合约vt系统代码
        self.productClass = EMPTY_STRING  # 产品类型（只有IB接口需要）
        self.currency = EMPTY_STRING  # 货币（只有IB接口需要）

        # 策略的基本变量，由引擎管理
        self.inited = False  # 是否进行了初始化
        self.trading = False  # 是否启动交易，由引擎管理
        self.pos = 0  # 持仓情况
        self.target_pos = 0  # 目标持仓

        # 参数列表，保存了参数的名称,要设置的参数
        self.paramList = ['name',
                          'className',
                          'author',
                          'vtSymbol']

        # 变量列表，保存了变量的名称
        self.varList = ['inited',
                        'trading',
                        'pos']

        # 设置策略参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

        # 创建bar管理器(K线合成对象)，用于合成bar和处理自定义周期的bar回调函数
        self.bm = BarManager(onBar=self.onBar, xmin=5, onXminBar=self.onFifteenBar)
        # 创建k线序列管理工具（含日k数据）
        self.am = ArrayManager2()
        self.dam = DailyArrayManager()



    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略"""
        self.writeCtaLog("%s初始化策略" % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(days=self.initDays)
        # 预处理初始化的bar
        for bar in initData:
            self.onBar(bar)

        # 发出策略状态变化事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略"""
        self.writeCtaLog("%s策略启动" % self.name)

        # 发出策略状态变化事件
        self.putEvent()  # 目前的结论是回测时候该方法为pass，实盘通常用于通知界面更新

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略"""
        self.writeCtaLog("%s策略停止" % self.name)

        # 发出策略状态变化事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送"""
        # 更新tick，合成k线
        self.bm.updateTick(tick)

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        self.writeCtaLog("%s策略发出委托单：" % self.name)
        self.writeCtaLog(order.__dict__)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        self.writeCtaLog("%s策略发生交易：" % self.name)
        self.writeCtaLog(trade.__dict__)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bm.updateBar(bar)  # 一分钟一个bar，执行周期大于1分钟的策略在自定义的执行方法里，到时间了由bm.updataBar回调执行

    # ----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到x分钟Bar推送"""
        # 保存K线数据
        am = self.am
        am.updateBar(bar)

        # 1. 产生交易信号
        self.generateSignal(bar)

        # 2. 产生持仓目标结果
        self.setTargetPos()

        # 3. 交易达到目的仓位
        self.trade()

    def generateSignal(self, bar):
        """产生交易信号（必须由用户继承实现）"""
        raise NotImplementedError

    def setTargetPos(self):
        """设定目标仓位（必须由用户继承实现）"""
        raise NotImplementedError

    def trade(self):
        """执行交易（必须由用户继承实现）"""
        raise NotImplementedError


    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """收到停止单推送（必须由用户继承实现）"""
        self.putEvent()

    # ----------------------------------------------------------------------
    def buy(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, stop)

    # ----------------------------------------------------------------------
    def short(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, stop)

    # ----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderIDList = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderIDList = self.ctaEngine.sendOrder(self.vtSymbol, orderType, price, volume, self)
            return vtOrderIDList
        else:
            # 交易停止时发单返回空字符串
            return []

    # ----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return

        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤单"""
        self.ctaEngine.cancelAll(self.name)

    # ----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)

    # ----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)

    # ----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    # ----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)

    # ----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType

    # ----------------------------------------------------------------------
    # TODO: 未完美，应考虑获取涨跌停价格挂单，以应对特殊情况
    def cleanAll(self, bar, slip=0.01, force=None):
        """
        清仓所有持仓并且撤销所有订单
        :param bar:  当前bar，主要为了获得价格
        :param slip: 滑点，用于强行成交
        :return:
        """
        self.cancelAll()
        if self.pos > 0:
            self.sell(price=bar.close - slip, volume=self.fixedSize)
        elif self.pos < 0:
            self.cover(price=bar.close + slip, volume=self.fixedSize)



################################################################################
class BarManager(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60），
       因为判断依据是分钟而不是数量
    """
    






























