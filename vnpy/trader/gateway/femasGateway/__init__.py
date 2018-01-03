# encoding: UTF-8

from vnpy.trader import vtConstant
from .femasGateway import FemasGateway

gatewayClass = FemasGateway
gatewayName = 'FEMAS'
gatewayDisplayName = '飞马'
gatewayType = vtConstant.GATEWAYTYPE_FUTURES
gatewayQryEnabled = True
