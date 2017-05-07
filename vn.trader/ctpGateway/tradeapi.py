# encoding: UTF-8
import os
from ctpGateway import *

class tradeAPI(CtpGateway):

    def __init__(self, eventEngine, gatewayName='CTP'):
        super(tradeAPI, self).__init__(eventEngine, gatewayName)

        self.accountInfo = VtAccountData()
        self.recodeAccount = False
        self.tickDf = {}
        # 注册事件处理函数
        self.registeHandle()
        self.initRecodeTick()

    # ----------------------------------------------------------------------
    def tradeStopWin(self, tick):
        '''止盈函数'''
        if not self.tradeDict[tick.symbol].stopWin:
            return
        if self.tradeDict[tick.symbol].closeing:
            self.tradeDict[tick.symbol].stopWin = False
            return
        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'
        if (longPosition in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[longPosition].pos.beClosed):
            if tick.lastPrice >= self.tdApi.posBufferDict[longPosition].pos.stopWinPrice:  # 最新价格大于止盈价格
                logContent = u'[止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.writeLog(logContent)
                send_msg(logContent.encode('utf-8'))
                #发单
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].winCount += 1
                self.tdApi.posBufferDict[longPosition].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
        if (shortPosition in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[shortPosition].pos.beClosed):  # 空单
            if tick.lastPrice <= self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice:  # 最新价格小于止盈价格
                logContent = u'[止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.writeLog(logContent)
                send_msg(logContent.encode('utf-8'))
                #发单
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].winCount += 1
                self.tdApi.posBufferDict[shortPosition].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
        self.tradeDict[tick.symbol].stopWin = False

    # ----------------------------------------------------------------------
    def tradeStopLoss(self, tick):
        '''止损函数'''
        if not self.tradeDict[tick.symbol].stopLoss:
            return
        if self.tradeDict[tick.symbol].closeing:
            self.tradeDict[tick.symbol].stopLoss = False
            return
        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'
        if (longPosition in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[longPosition].pos.beClosed):
            if tick.lastPrice <= self.tdApi.posBufferDict[longPosition].pos.stopLossPrice:  # 最新价格小于止损价格
                logContent = u'[止损单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.writeLog(logContent)
                send_msg(logContent.encode('utf-8'))
                #发单
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[longPosition].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].stopCount += 1
                self.tradeDict[tick.symbol].closeing = True
        if (shortPosition in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[shortPosition].pos.beClosed):  # 空单
            if tick.lastPrice >= self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice:  # 最新价格大于止损价格
                logContent = u'[止损单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.writeLog(logContent)
                send_msg(logContent.encode('utf-8'))
                # 发单
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[shortPosition].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].stopCount += 1
                self.tradeDict[tick.symbol].closeing = True
        self.tradeDict[tick.symbol].stopLoss = False

    # ----------------------------------------------------------------------
    def tradeGetMaxWin(self, tick):
        '''摸顶止盈，当价格达到目标收益后，开始摸顶，从最高价回撤达到阈值，平仓止盈'''
        if tick.lastPrice > self.tradeDict[tick.symbol].todayHigh:     #更新最高价
            self.tradeDict[tick.symbol].todayHigh = tick.lastPrice
        elif tick.lastPrice < self.tradeDict[tick.symbol].todayLow:      #更新最低价
            self.tradeDict[tick.symbol].todayLow = tick.lastPrice
        else:
            pass

        if self.tradeDict[tick.symbol].closeing:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.tradeDict[tick.symbol].todayHigh >= self.tdApi.posBufferDict[symbol].pos.price / 10 + self.tradeDict[tick.symbol].winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice <= self.tradeDict[tick.symbol].todayHigh - self.tradeDict[tick.symbol].maxDrawDown:     #达到最大回撤
                        logContent = u'[摸顶止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.writeLog(logContent)
                        send_msg(logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].closeing = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.tradeDict[tick.symbol].todayLow <= self.tdApi.posBufferDict[symbol].pos.price / 10 - self.tradeDict[tick.symbol].winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice >= self.tradeDict[tick.symbol].todayLow + self.tradeDict[tick.symbol].maxDrawDown:     #达到最大回撤
                        logContent = u'[摸顶止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.writeLog(logContent)
                        send_msg(logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].closeing = True
            else:
                pass

    # ----------------------------------------------------------------------
    def shortPolicy1(self, tick):
        '''持仓到收盘，没有做多或者做空倾向，两边交易区间一致'''
        print '============================='
        print 'symbol:',tick.symbol
        print 'lastPrice:',tick.lastPrice
        print 'openPrice:',tick.openPrice
        print 'stopCount:',self.tradeDict[tick.symbol].stopCount
        print 'ststus:', self.tradeDict[tick.symbol].status
        print 'wincount:', self.tradeDict[tick.symbol].winCount
        print 'closeing:',self.tradeDict[tick.symbol].closeing

        highThreshold = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 2
        lowThreshold = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 2

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损价位，打开止损开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = highThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            # 跌停价止盈
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = tick.lowerLimit
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif tick.lastPrice <= lowThreshold:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
        else:
            pass


        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = lowThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            # 涨停价止盈
            self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = tick.upperLimit
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif tick.lastPrice >= highThreshold:
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
        else:
            pass

        #涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.tradeDict[tick.symbol].stopLong = True
        #跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.tradeDict[tick.symbol].stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed): #存在空单
                #空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed): #存在多单
                #多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def shortPolicy2(self, tick):
        '''有倾向性做多或做空，两边交易区间不一致'''
        print '============================='
        print 'symbol:', tick.symbol
        print 'lastPrice:', tick.lastPrice
        print 'openPrice:', tick.openPrice
        print 'stopCount:', self.tradeDict[tick.symbol].stopCount
        print 'closeing:', self.tradeDict[tick.symbol].closeing
        if self.tradeDict[tick.symbol].currentMode == 'long':
            highThreshold = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 5
            lowThreshold = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 15
        elif self.tradeDict[tick.symbol].currentMode == 'short':
            highThreshold = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 15
            lowThreshold = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 5
        else:
            return

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损价位，打开止损开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = highThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            # 跌停价止盈
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = tick.lowerLimit
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif tick.lastPrice <= lowThreshold:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
        else:
            pass


        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = lowThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            # 涨停价止盈
            self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = tick.upperLimit
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif tick.lastPrice >= highThreshold:
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
        else:
            pass

        #涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.tradeDict[tick.symbol].stopLong = True
        #跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.tradeDict[tick.symbol].stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed): #存在空单
                #空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed): #存在多单
                #多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def shortPolicy3(self, tick):
        '''在开盘价两边来回做，两边各做一次，大幅止损'''
        print '============================='
        print 'symbol:', tick.symbol
        print 'lastPrice:', tick.lastPrice
        print 'openPrice:', tick.openPrice
        print 'ststus:', self.tradeDict[tick.symbol].status
        print 'wincount:', self.tradeDict[tick.symbol].winCount
        print 'stopCount:', self.tradeDict[tick.symbol].stopCount
        print 'closeing:', self.tradeDict[tick.symbol].closeing

        highThreshold = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 3
        lowThreshold = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 3
        longStopLoss = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].stopTickPrice
        shortStopLoss = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].stopTickPrice

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损价位，打开止损开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = shortStopLoss
            self.tradeDict[tick.symbol].stopLoss = False
            # 跌停价止盈
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = lowThreshold
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif tick.lastPrice >= highThreshold:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
        else:
            pass

        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = longStopLoss
            self.tradeDict[tick.symbol].stopLoss = False
            # 涨停价止盈
            self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = highThreshold
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif tick.lastPrice <= lowThreshold:
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
        else:
            pass

        # 涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.tradeDict[tick.symbol].stopLong = True
        # 跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.tradeDict[tick.symbol].stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (
            nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (
                not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed):  # 存在空单
                # 空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,
                                                      self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (
                not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed):  # 存在多单
                # 多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,
                                                       self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def shortPolicy4(self, tick):
        '''在开盘价两边来回做，大幅止损，抓住大走势'''
        print '============================='
        print 'symbol:', tick.symbol
        print 'lastPrice:', tick.lastPrice
        print 'openPrice:', tick.openPrice
        print 'stopCount:', self.tradeDict[tick.symbol].stopCount
        print 'closeing:', self.tradeDict[tick.symbol].closeing
        x1 = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 25
        x2 = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 5
        x3 = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 5
        x4 = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 25

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损价位，打开止损开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            if self.tdApi.posBufferDict[shortPosition].pos.price > tick.openPrice:
                self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = x1
                self.tradeDict[tick.symbol].stopLoss = True
                # 跌停价止盈
                self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = x3
                self.tradeDict[tick.symbol].stopWin = True
            else:
                self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = x3
                self.tradeDict[tick.symbol].stopLoss = True
                # 跌停价止盈
                self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = tick.lowerLimit
                self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif tick.lastPrice >= x2 and tick.lastPrice < x1:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
        elif tick.lastPrice <= x4:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
            self.tradeDict[tick.symbol].stopLong = True
        else:
            pass

        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            if self.tdApi.posBufferDict[longPosition].pos.price < tick.openPrice:
                self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = x4
                self.tradeDict[tick.symbol].stopLoss = True
                # 涨停价止盈
                self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = x2
                self.tradeDict[tick.symbol].stopWin = True
            else:
                self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = x2
                self.tradeDict[tick.symbol].stopLoss = True
                # 涨停价止盈
                self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = tick.upperLimit
                self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif tick.lastPrice <= x3 and tick.lastPrice > x4:
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
        elif tick.lastPrice >= x1:
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
            self.tradeDict[tick.symbol].stopShort = True
        else:
            pass

        # 涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.tradeDict[tick.symbol].stopLong = True
        # 跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.tradeDict[tick.symbol].stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (
                    nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed):  # 存在空单
                # 空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,
                                                    self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed):  # 存在多单
                # 多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,
                                                    self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def shortPolicy5(self, tick):
        '''回撤达到阈值，反向开仓'''
        print '============================='
        print 'symbol:', tick.symbol
        print 'lastPrice:', tick.lastPrice
        print 'openPrice:', tick.openPrice
        print 'stopCount:', self.tradeDict[tick.symbol].stopCount
        print 'closeing:', self.tradeDict[tick.symbol].closeing

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损价位，打开止损开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].stopTickPrice
            self.tradeDict[tick.symbol].stopLoss = True
            # 跌停价止盈
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].winTickPrice
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif ((tick.highPrice - tick.openPrice) >= (self.tradeDict[tick.symbol].maxDrawDown * self.tradeDict[tick.symbol].tickPrice)) and (tick.lastPrice <= tick.openPrice):
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'short'
        else:
            pass

        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].stopTickPrice
            self.tradeDict[tick.symbol].stopLoss = True
            # 涨停价止盈
            self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].winTickPrice
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif ((tick.openPrice - tick.lowPrice) >= (self.tradeDict[tick.symbol].maxDrawDown * self.tradeDict[tick.symbol].tickPrice)) and (tick.lastPrice >= tick.openPrice):
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = 'long'
        else:
            pass

        # 涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.tradeDict[tick.symbol].stopLong = True
        # 跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.tradeDict[tick.symbol].stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (
                    nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed):  # 存在空单
                # 空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,
                            self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed):  # 存在多单
                # 多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,
                            self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def ruPolicy(self, tick):
        '''橡胶策略'''
        print '============================='
        print 'symbol:', tick.symbol
        print 'lastPrice:', tick.lastPrice
        print 'openPrice:', tick.openPrice
        print 'stopCount:', self.tradeDict[tick.symbol].stopCount
        print 'closeing:', self.tradeDict[tick.symbol].closeing
        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        if self.tradeDict[tick.symbol].currentMode == 'long':
            if longPosition in self.tdApi.posBufferDict.keys():
                self.tdApi.posBufferDict[longPosition].pos.stopLossPrice = self.tdApi.posBufferDict[longPosition].pos.price - self.tradeDict[tick.symbol].tickPrice * 20
                self.tdApi.posBufferDict[longPosition].pos.stopWinPrice = self.tdApi.posBufferDict[longPosition].pos.price + self.tradeDict[tick.symbol].tickPrice * 10
                self.tradeDict[tick.symbol].stopLoss = True
                self.tradeDict[tick.symbol].stopWin = True
            else:
                self.tradeDict[tick.symbol].openFlag = True
                self.tradeDict[tick.symbol].openDirection = 'long'
        if self.tradeDict[tick.symbol].currentMode == 'short':
            if shortPosition in self.tdApi.posBufferDict.keys():
                self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = self.tdApi.posBufferDict[shortPosition].pos.price + self.tradeDict[tick.symbol].tickPrice * 20
                self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = self.tdApi.posBufferDict[shortPosition].pos.price - self.tradeDict[tick.symbol].tickPrice * 10
                self.tradeDict[tick.symbol].stopLoss = True
                self.tradeDict[tick.symbol].stopWin = True
            else:
                self.tradeDict[tick.symbol].openFlag = True
                self.tradeDict[tick.symbol].openDirection = 'short'

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (
                    nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].closeing == True:
                return
            if (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed):  # 存在空单
                # 空单清仓
                print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,
                            self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.3'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) and (
                    not self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed):  # 存在多单
                # 多单清仓
                print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,
                            self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tdApi.posBufferDict[tick.symbol + '.2'].pos.beClosed = True  # 标记仓位已被平
                self.tradeDict[tick.symbol].closeing = True
            self.tradeDict[tick.symbol].stopLong = True
            self.tradeDict[tick.symbol].stopShort = True

    # ----------------------------------------------------------------------
    def tradeOpen(self, tick):
        '''开仓函数'''

        print 'in tradeOpen:',self.tradeDict[tick.symbol].opening
        # 开仓标志位false
        if not self.tradeDict[tick.symbol].openFlag:
            return
        # 停止开多仓
        if self.tradeDict[tick.symbol].stopLong and (self.tradeDict[tick.symbol].openDirection == 'long'):
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 停止开空仓
        if self.tradeDict[tick.symbol].stopShort and (self.tradeDict[tick.symbol].openDirection == 'short'):
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 存在未成交的开仓单
        if self.tradeDict[tick.symbol].opening:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 今天止损达到1次
        if self.tradeDict[tick.symbol].stopCount >= 7:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 今天止盈达到1次
        if self.tradeDict[tick.symbol].winCount >= 4:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 存在持仓
        print self.tdApi.posBufferDict.keys()
        if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) or (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()):
            self.tradeDict[tick.symbol].openFlag = False
            return

        #其他情况，执行开仓指令
        if self.tradeDict[tick.symbol].openDirection == 'long':
            orderReq = self.makeBuyOpenOrder(tick.symbol, tick.askPrice1, self.tradeDict[tick.symbol].tradeVolume)
        elif self.tradeDict[tick.symbol].openDirection == 'short':
            orderReq = self.makeSellOpenOrder(tick.symbol, tick.bidPrice1, self.tradeDict[tick.symbol].tradeVolume)
        else:
            self.tradeDict[tick.symbol].openFlag = False
            return
        self.sendOrder(orderReq)
        self.tradeDict[tick.symbol].opening = True
        print 'change opening true:',self.tradeDict[tick.symbol].opening
        self.tradeDict[tick.symbol].openFlag = False

        #记录日志
        logContent = u'[开仓单]合约代码：%s，价格：%s，数量：%s，方向：%s' % (
            tick.symbol, tick.bidPrice1, self.tradeDict[tick.symbol].tradeVolume, self.tradeDict[tick.symbol].openDirection)
        self.writeLog(logContent)
        send_msg(logContent.encode('utf-8'))

    # ----------------------------------------------------------------------
    def writeLog(self, loginfo):
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = loginfo
        self.onLog(log)

    # ----------------------------------------------------------------------
    def initRecodeTick(self):
        '''重置实时行情缓存'''
        self.tickCount = 0
        for symbol in config.tradeSymbol:
            self.tickDf[symbol] = pd.DataFrame(columns=['symbol', 'date', 'time', 'lastPrice', 'lastVolume', 'bidPrice1', 'askPrice1', 'bidVolume1', 'askVolume1'])

    # ----------------------------------------------------------------------
    def recodeTick(self, tick):
        '''记录实时行情'''
        newTick = pd.DataFrame([[tick.symbol, tick.date, tick.time, tick.lastPrice, tick.lastVolume, tick.bidPrice1, tick.askPrice1, tick.bidVolume1, tick.askVolume1]],
                           columns=['symbol', 'date','time','lastPrice', 'lastVolume','bidPrice1','askPrice1','bidVolume1', 'askVolume1'])

        self.tickDf[tick.symbol] = pd.concat([self.tickDf[tick.symbol], newTick], ignore_index=True)
        self.tickCount += 1
        if self.tickCount >= 50 * len(config.tradeSymbol):
            self.today = datetime.now().date().strftime('%Y-%m-%d')
            for symbol in self.tickDf.keys():
                # filename = '/home/myctp/vn.trader/ctpGateway/tickData/%s' % (config.analysisSymbol + '-' + self.today + '.csv')
                filename = '/home/myctp/vn.trader/ctpGateway/tickData/%s' % (symbol + '-' + self.today + '.csv')
                if os.path.exists(filename):
                    tickBuffer = pd.read_csv(filename)
                    tickBuffer = pd.concat([tickBuffer, self.tickDf[symbol]], ignore_index=True)
                    tickBuffer.to_csv(filename, index=False)
                else:
                    self.tickDf[symbol].to_csv(filename, index=False)
            self.initRecodeTick()

    # ----------------------------------------------------------------------
    def pTick(self, event):
        '''tick事件处理机，当接收到行情时执行'''
        tick = event.dict_['data']
        self.recodeTick(tick)
        if self.tradeDict[tick.symbol].tickCount <= 1:
            self.tradeDict[tick.symbol].tickCount += 1
            return
        self.sendOrderMsg = True    # 只有在交易时间才允许记录成交日志和订单日志，以及发送微信消息

        if (tick.openPrice > self.tradeDict[tick.symbol].perHigh) or (tick.openPrice < self.tradeDict[tick.symbol].perLow):
            self.tradeDict[tick.symbol].status = 1

        # 获取到持仓信息后执行策略
        if self.tradeDict[tick.symbol].status == 0:
            self.shortPolicy3(tick)
        else:
            self.shortPolicy1(tick)

        # 止损
        self.tradeStopLoss(tick)

        # 止盈
        self.tradeStopWin(tick)

        #更新状态
        if self.tradeDict[tick.symbol].status == 0:
            if self.tradeDict[tick.symbol].winCount >= 3:
                self.tradeDict[tick.symbol].status = 1          #切换状态
                self.tradeDict[tick.symbol].openFlag = False    #本次开仓无效
                self.tradeDict[tick.symbol].winCount = 0
            if self.tradeDict[tick.symbol].stopCount >= 1:
                self.tradeDict[tick.symbol].stopLong = True
                self.tradeDict[tick.symbol].stopShort = True
        else:
            if self.tradeDict[tick.symbol].winCount >= 1:
                self.tradeDict[tick.symbol].stopLong = True
                self.tradeDict[tick.symbol].stopShort = True
            if self.tradeDict[tick.symbol].stopCount >= 7:
                self.tradeDict[tick.symbol].stopLong = True
                self.tradeDict[tick.symbol].stopShort = True

        # 开仓
        self.tradeOpen(tick)

    # ----------------------------------------------------------------------
    def pTrade(self, event):
        '''成交事件处理机，当订单成交回报时执行'''
        trade = event.dict_['data']
        if self.sendOrderMsg:
            logContent = u'[成交回报]合约代码：%s，订单编号：%s，价格：%s，数量：%s，方向：%s，开平仓：%s，成交编号：%s，成交时间：%s' % (
                trade.symbol, trade.orderID, trade.price, trade.volume, trade.direction, trade.offset, trade.tradeID,trade.tradeTime)
            self.writeLog(logContent)
            send_msg(logContent.encode('utf-8'))

    # ----------------------------------------------------------------------
    def pOrder(self, event):
        '''订单事件处理机，当收到订单回报时执行'''
        order = event.dict_['data']
        if order.symbol not in self.tradeDict.keys():
            return
        if order.offset == u'开仓' and order.status == u'全部成交':
            # self.getPosition = False
            self.qryPosition()  # 查询并更新持仓
            self.tradeDict[order.symbol].todayHigh = 0
            self.tradeDict[order.symbol].todayLow = 100000
            # if order.direction == u'空':
            #     self.tradeDict[order.symbol].tradeList.append(0)
            # elif order.direction == u'多':
            #     self.tradeDict[order.symbol].tradeList.append(1)
            # else:
            #     pass
        # 非开仓，全部成交，视为平仓全部成交，因为可能为未知或者平今，所以没有限定为平仓
        elif order.status == u'全部成交':
            # self.getPosition = False
            self.qryPosition()  # 查询并更新持仓
            self.tradeDict[order.symbol].closeing = False
            self.tradeDict[order.symbol].closeCount += 1
        else:
            pass
        # TODO
        # 此处考虑到本策略不止盈，所以将平仓次数与止损次数视为相等，不使用此策略时，应该修改。
        # 不止盈的话，只有程序启动时，平仓次数才会大于止损次数，因此，程序中断后，通过此处获取当天止损次数
        # if self.tradeDict[order.symbol].closeCount > self.tradeDict[order.symbol].stopCount:
        #     self.tradeDict[order.symbol].stopCount = self.tradeDict[order.symbol].closeCount
        #     self.tradeDict[order.symbol].winCount = self.tradeDict[order.symbol].closeCount

        if self.sendOrderMsg:
            logContent = u'[订单回报]合约代码：%s，订单编号：%s，价格：%s，数量：%s，方向：%s，开平仓：%s，订单状态：%s，报单时间：%s' % (
                order.symbol, order.orderID, order.price, order.totalVolume, order.direction, order.offset,order.status, order.orderTime)
            self.writeLog(logContent)
            # send_msg(logContent.encode('utf-8'))

    # ----------------------------------------------------------------------
    def pPosition(self,event):
        '''持仓事件处理机，当收到持仓消息时执行'''
        pos = event.dict_['data']
        self.getPosition = True
        if pos.symbol not in self.tradeDict.keys():
            return
        if pos.direction == u'多':
            positionName = pos.symbol + '.2'
        else:
            positionName = pos.symbol + '.3'
        # print 'in pPosition :',self.tdApi.posBufferDict.keys()
        if positionName in self.tdApi.posBufferDict.keys():
            if not self.tdApi.posBufferDict[positionName].pos.beClosed:
                self.tradeDict[pos.symbol].opening = False
            print '###############################'
            print 'position info:'
            # print 'change opening false:',self.tradeDict[pos.symbol].opening
            print self.tdApi.posBufferDict[positionName].pos.symbol
            print self.tdApi.posBufferDict[positionName].pos.direction.encode('utf-8')
            print self.tdApi.posBufferDict[positionName].pos.position
            print self.tdApi.posBufferDict[positionName].pos.frozen
            print self.tdApi.posBufferDict[positionName].pos.price
            print self.tdApi.posBufferDict[positionName].pos.stopLossPrice
            print self.tdApi.posBufferDict[positionName].pos.stopWinPrice
            print self.tdApi.posBufferDict[positionName].pos.vtPositionName.encode('utf-8')

        # for positionName in self.tdApi.posBufferDict.keys():
        #     print '###############################'
        #     print 'position info:'
        #     print self.tdApi.posBufferDict[positionName].pos.symbol
        #     print self.tdApi.posBufferDict[positionName].pos.direction.encode('utf-8')
        #     print self.tdApi.posBufferDict[positionName].pos.position
        #     print self.tdApi.posBufferDict[positionName].pos.frozen
        #     print self.tdApi.posBufferDict[positionName].pos.price
        #     print self.tdApi.posBufferDict[positionName].pos.stopLossPrice
        #     print self.tdApi.posBufferDict[positionName].pos.stopWinPrice
        #     print self.tdApi.posBufferDict[positionName].pos.vtPositionName.encode('utf-8')

    # ----------------------------------------------------------------------
    def pAccount(self, event):
        '''账户信息事件处理机，当收到账户信息时执行'''
        account = event.dict_['data']
        self.accountInfo.accountID = account.accountID
        self.accountInfo.preBalance = account.preBalance    # 昨日账户结算净值
        self.accountInfo.balance = account.balance          # 账户净值
        self.accountInfo.available = account.available      # 可用资金
        self.accountInfo.commission = account.commission    # 今日手续费
        self.accountInfo.margin = account.margin            # 保证金占用
        self.accountInfo.closeProfit = account.closeProfit  # 平仓盈亏
        self.accountInfo.positionProfit = account.positionProfit  # 持仓盈亏

        nowTime = datetime.now().time()
        if (nowTime > datetime.strptime('15:00:30', '%H:%M:%S').time()) and (nowTime < datetime.strptime('15:01:30', '%H:%M:%S').time())\
                and (not self.recodeAccount):
            fileName = config.BALANCE_file
            fp = file(fileName, 'a+')
            today = datetime.now().date().strftime('%Y-%m-%d')
            info = today + ',' + str(self.accountInfo.accountID) + ',' + str(self.accountInfo.preBalance) + ',' +\
                str(self.accountInfo.balance) + ',' + str(self.accountInfo.available) + ',' +\
                str(self.accountInfo.commission) + ',' + str(self.accountInfo.closeProfit) + '\n'
            fp.write(info)
            fp.close()
            self.recodeAccount = True

    # ----------------------------------------------------------------------
    def registeHandle(self):
        '''注册处理机'''
        self.eventEngine.register(EVENT_LOG, self.pLog)
        self.eventEngine.register(EVENT_TICK, self.pTick)
        self.eventEngine.register(EVENT_TRADE, self.pTrade)
        self.eventEngine.register(EVENT_ORDER, self.pOrder)
        self.eventEngine.register(EVENT_POSITION, self.pPosition)
        self.eventEngine.register(EVENT_CONTRACT, self.pContract)
        self.eventEngine.register(EVENT_ACCOUNT, self.pAccount)
        self.eventEngine.register(EVENT_ERROR, self.pError)
        self.eventEngine.register(EVENT_CONTRACT, self.pContract)



if __name__ == '__main__':

    if 6 > 3:
        print '1'
    elif 6 > 5:
        print '2'
    else:
        pass
