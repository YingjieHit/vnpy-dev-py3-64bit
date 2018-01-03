# encoding: UTF-8

from vnpy.trader import vtConstant
from .xspeedGateway import XspeedGateway

gatewayClass = XspeedGateway
gatewayName = 'XSPEED'
gatewayDisplayName = '飞创'
gatewayType = vtConstant.GATEWAYTYPE_FUTURES
gatewayQryEnabled = True