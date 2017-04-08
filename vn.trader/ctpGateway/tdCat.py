#!/usr/bin/python
# encoding: UTF-8
from PyQt4 import QtCore
import sys
from ctpGateway import *
from config import *

def test():

    app = QtCore.QCoreApplication(sys.argv)

    eventEngine = EventEngine()
    eventEngine.start()

    #连接登录
    gateway = CtpGateway(eventEngine)
    gateway.connect()

    #订阅行情
    for symbol in config.tradeSymbol:
        subscribeReq = VtSubscribeReq()
        subscribeReq.symbol = symbol
        gateway.subscribe(subscribeReq)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()