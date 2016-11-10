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

    #查询账户
    gateway.qryAccount()

    #查询持仓
    gateway.qryPosition()

    #订阅行情
    subscribeReq = VtSubscribeReq()
    subscribeReq.symbol = 'RM701'
    gateway.mdApi.subscribe(subscribeReq)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()