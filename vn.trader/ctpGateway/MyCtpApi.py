#!/usr/bin/python
# encoding: UTF-8
from PyQt4 import QtCore
import sys
from ctpGateway import *


def pLog(event):
    log = event.dict_['data']
    print ':'.join([log.logTime, log.logContent])


def test():

    app = QtCore.QCoreApplication(sys.argv)

    eventEngine = EventEngine()
    eventEngine.register(EVENT_LOG, pLog)
    eventEngine.start()

    #连接登录
    gateway = CtpGateway(eventEngine)
    gateway.connect()

    #订阅行情
    subscribeReq = VtSubscribeReq()
    subscribeReq.symbol = 'RM701'
    gateway.subscribe(subscribeReq)

    # 查询账户
    gateway.qryAccount()

    # 查询持仓
    gateway.qryPosition()

    orderReq= VtOrderReq()
    orderReq.symbol = 'RM701'  # 代码
    orderReq.price = 2425  # 价格
    orderReq.volume = 1  # 数量

    orderReq.priceType = PRICETYPE_MARKETPRICE  # 价格类型
    orderReq.direction = DIRECTION_SHORT  # 买卖
    orderReq.offset = OFFSET_OPEN  # 开平
    gateway.sendOrder(orderReq)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()