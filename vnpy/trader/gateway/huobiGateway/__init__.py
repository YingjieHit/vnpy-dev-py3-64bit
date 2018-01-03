# encoding: UTF-8

from vnpy.trader import vtConstant
from .huobiGateway import HuobiGateway

gatewayClass = HuobiGateway
gatewayName = 'HUOBI'
gatewayDisplayName = '火币'
gatewayType = vtConstant.GATEWAYTYPE_BTC
gatewayQryEnabled = True

