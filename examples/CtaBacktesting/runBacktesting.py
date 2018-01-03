# encoding: UTF-8

"""
展示如何执行策略回测。
"""



# 载入回测引擎和数据库名称
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME


if __name__ == '__main__':
    # 载入KkStrategy策略
    # from vnpy.trader.app.ctaStrategy.strategy.strategyKingKeltner import KkStrategy
    from vnpy.trader.app.ctaStrategy.strategy.strategyRBreak import RBreakStrategy
    # from vnpy.trader.app.ctaStrategy.strategy.strategyLastGold import LastGoldStrategy
    # from vnpy.trader.app.ctaStrategy.strategy.strategyAppleStart import AppleStartStrategy
    from vnpy.trader.app.ctaStrategy.strategy.strategyDualThrustZR5 import DualThrustStrategyZR5
    strategy_class = DualThrustStrategyZR5  #



    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    # 不一定为日k，仅仅是排除tick模式，可日k可分钟k
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    # 细节：时间有数据开始日期和策略开始日期，输入的参数是数据开始日期，默认策略开始日期要往后10个自然日
    #engine.setStartDate('20120101')
    engine.setStartDate("20171001")
    
    # 设置产品相关参数
    engine.setSlippage(0.005)     # 股指1跳  滑点
    engine.setRate(0.3/10000)   # 万0.3  手续费
    engine.setSize(1000)         # 股指合约大小
    engine.setPriceTick(0.005)    # 股指最小价格变动


    # 设置使用的历史数据库
    # 设置数据库为分钟数据库。合约名为IF000
    # engine.setDatabase(MINUTE_DB_NAME, 'IF0000')
    engine.setDatabase(MINUTE_DB_NAME, 'T1803') # 10年国债
    #engine.setDatabase(MINUTE_DB_NAME, 'j1805')
    # engine.setDatabase(MINUTE_DB_NAME, 'rb1805') # 螺纹钢
    
    # 在引擎中创建策略对象
    d = {}  # d为策略的setting，设置
    # engine.initStrategy(KkStrategy, d)
    engine.initStrategy(strategy_class, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    engine.showBacktestingResult()
