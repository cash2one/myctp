# encoding: UTF-8

import os
import json
from copy import copy

from vnctpmd import MdApi
from vnctptd import TdApi
from ctpDataType import *
from vtGateway import *
from config import *
from weixin import *
import pandas as pd
from ctpGateway import CtpGateway

class BaseTrade(object):
    def __init__(self):
        self.currentMode = 1  # 当前运行模式：1:多，0:空
        self.winTarget = 10  # 盈利目标点数，浮盈达到该点数，止盈
        self.stopTarget = 20  # 止损目标点数，浮亏达到该点数，止损
        self.winTargetPrice = 100000      #止盈目标价位，当前价格达到该价格，止盈
        self.stopTargetPrice = 0          #止损目标价位，当前价格达到该价格，止损
        self.preSellPrice = 0             #上次平仓价位
        self.maxDrawDown = 3  # 允许最大回撤点数，从最高价格回撤达到该点数，止盈
        self.stopLoss = False  # 是否止损
        self.stopWin = False  # 是否止盈
        self.tradeVolume = 1  # 交易数量
        self.openFlag = False  # 开仓标志
        self.noTrading = False  # 是否存在未成交订单
        self.tradeList = []
        self.stopCount = 0  # 止损次数


    # ----------------------------------------------------------------------
    def makeOrder(self, _symbol, _price, _volume, _direction, _offset, _priceType):
        orderReq = VtOrderReq()
        orderReq.symbol = _symbol  # 代码
        orderReq.price = _price  # 价格
        orderReq.volume = _volume  # 数量

        orderReq.priceType = _priceType  # 限价单或市价单
        orderReq.direction = _direction  # 买卖方向
        orderReq.offset = _offset  # 开平仓
        return orderReq

    # ----------------------------------------------------------------------
    def makeBuyOpenOrder(self, _symbol, _price, _volume, _priceType=PRICETYPE_LIMITPRICE):
        '''买开单'''
        return self.makeOrder(_symbol, _price, _volume, DIRECTION_LONG, OFFSET_OPEN, _priceType)

    # ----------------------------------------------------------------------
    def makeBuyCloseOrder(self, _symbol, _price, _volume, _priceType=PRICETYPE_LIMITPRICE):
        '''买平单'''
        return self.makeOrder(_symbol, _price, _volume, DIRECTION_LONG, OFFSET_CLOSE, _priceType)

    # ----------------------------------------------------------------------
    def makeSellOpenOrder(self, _symbol, _price, _volume, _priceType=PRICETYPE_LIMITPRICE):
        '''卖开单'''
        return self.makeOrder(_symbol, _price, _volume, DIRECTION_SHORT, OFFSET_OPEN, _priceType)

    # ----------------------------------------------------------------------
    def makeSellCloseOrder(self, _symbol, _price, _volume, _priceType=PRICETYPE_LIMITPRICE):
        '''卖开单'''
        return self.makeOrder(_symbol, _price, _volume, DIRECTION_SHORT, OFFSET_CLOSE, _priceType)

    # ----------------------------------------------------------------------
    def tradeStopWin(self, tick):
        '''止盈函数'''
        if self.noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice > ((self.tdApi.posBufferDict[symbol].pos.price / 10) + config.winTarget):  # 最新价格大于止盈价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice < ((self.tdApi.posBufferDict[symbol].pos.price / 10) - config.winTarget):  # 最新价格小于止盈价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.noTrading = True
            else:
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[未知类型订单]合约代码：%s' % symbol
                self.onLog(log)

    # ----------------------------------------------------------------------
    def tradeStopLoss(self, tick):
        '''止损函数'''
        if self.noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice < ((self.tdApi.posBufferDict[symbol].pos.price / 10) - config.stopTarget):  # 最新价格小于止损价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止损单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice > ((self.tdApi.posBufferDict[symbol].pos.price / 10) + config.stopTarget):  # 最新价格大于止损价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止损单]空单买入，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    send_msg(log.logContent.encode('utf-8'))
                    # 发单
                    orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.noTrading = True
                    print "================[STOP LOSS]==========================="
            else:
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[未知类型订单]合约代码：%s' % symbol
                self.onLog(log)

    # ----------------------------------------------------------------------
    def tradeGetMaxWin(self, tick):
        '''摸顶止盈，当价格达到目标收益后，开始摸顶，从最高价回撤达到阈值，平仓止盈'''
        if self.noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.todayHigh >= self.tdApi.posBufferDict[symbol].pos.price / 10 + config.winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice <= self.todayHigh - config.maxDrawDown:     #达到最大回撤
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.todayLow <= self.tdApi.posBufferDict[symbol].pos.price / 10 - config.winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice >= self.todayLow + config.maxDrawDown:     #达到最大回撤
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.noTrading = True
            else:
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[未知类型订单]合约代码：%s' % symbol
                self.onLog(log)



class police(BaseTrade):
    def __init__(self, symbol):
        BaseTrade.__init__(self)
        self.symbol = symbol

    def function(self, tick, position):
        pass


if __name__ == '__main__':
    a = police('rm709')
    print a.symbol
    print a.winTarget
    a.man()