#!/usr/bin/python
# encoding: UTF-8
from PyQt4 import QtCore
import sys
from ctpGateway import *
from weixin import *
from config import *


def pLog(event):
    log = event.dict_['data']
    loginfo = ':'.join([log.logTime, log.logContent])
    # send_msg(loginfo)
    print loginfo


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
    subscribeReq.symbol = config.tradeSymbol
    gateway.subscribe(subscribeReq)

    subscribeReq = VtSubscribeReq()
    subscribeReq.symbol = config.analysisSymbol
    gateway.subscribe(subscribeReq)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()