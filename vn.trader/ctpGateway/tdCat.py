#!/usr/bin/python
# encoding: UTF-8
from PyQt4 import QtCore
import sys
from tradeapi import *
from config import *

def test():

    app = QtCore.QCoreApplication(sys.argv)

    reconfig()
    # 开盘前重新初始化交易参数
    now = datetime.now()
    if ((now.time() > datetime.strptime('20:30:00', '%H:%M:%S').time())
        and (now.time() < datetime.strptime('21:00:00', '%H:%M:%S').time())):
        reconfig()

    eventEngine = EventEngine()
    eventEngine.start()

    #连接登录
    gateway = tradeAPI(eventEngine)
    gateway.connect()

    #订阅行情
    for symbol in config.tradeSymbol:
        subscribeReq = VtSubscribeReq()
        subscribeReq.symbol = symbol
        gateway.subscribe(subscribeReq)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()