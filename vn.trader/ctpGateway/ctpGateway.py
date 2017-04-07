# encoding: UTF-8

'''
vn.ctp的gateway接入

考虑到现阶段大部分CTP中的ExchangeID字段返回的都是空值
vtSymbol直接使用symbol
'''


import os
import json
from copy import copy

from ctpmdapi import CtpMdApi
from ctptdapi import CtpTdApi
from vtGateway import *
from policy import *
from config import *
from weixin import *
import pandas as pd


########################################################################
class CtpGateway(VtGateway):
    """CTP接口"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='CTP'):
        """Constructor"""
        super(CtpGateway, self).__init__(eventEngine, gatewayName)
        
        self.mdApi = CtpMdApi(self)     # 行情API
        self.tdApi = CtpTdApi(self)     # 交易API
        
        self.mdConnected = False        # 行情API连接状态，登录完成后为True
        self.tdConnected = False        # 交易API连接状态
        
        self.qryEnabled = True         # 是否要启动循环查询，查询账户信息和持仓信息

        self.tradeDict = {}
        self.checkCount = 0
        self.initTrade()
        self.initRecodeTick()
        # self.loadTradeConfig()

        # 注册事件处理函数
        self.registeHandle()
        
    #----------------------------------------------------------------------
    def connect(self):
        """连接"""
        # 载入json文件
        # fileName = self.gatewayName + '_connect.json'
        # fileName = os.getcwd() + '/' + fileName
        fileName = config.CTP_configPath
        
        try:
            f = file(fileName)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取连接配置出错，请检查'
            self.onLog(log)
            return
        
        # 解析json文件
        setting = json.load(f)
        try:
            userID = str(setting['userID'])
            password = str(setting['password'])
            brokerID = str(setting['brokerID'])
            tdAddress = str(setting['tdAddress'])
            mdAddress = str(setting['mdAddress'])
        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return            
        
        # 创建行情和交易接口对象
        self.mdApi.connect(userID, password, brokerID, mdAddress)
        self.tdApi.connect(userID, password, brokerID, tdAddress)
        
        # 初始化并启动查询
        self.initQuery()
        self.qryAccount()

    # ----------------------------------------------------------------------
    def disconnect(self):
        """断开连接"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'断开行情和交易接口'
        self.onLog(log)

        #注销查询函数
        if self.qryEnabled:
            self.eventEngine.unregister(EVENT_TIMER, self.query)

        # 断开行情和交易接口对象
        if self.mdConnected:
            self.mdApi.close()
        if self.tdConnected:
            self.tdApi.close()

    # ----------------------------------------------------------------------
    def isTradeTime(self):
        '''是否为交易时间'''
        now = datetime.now()
        if (((now.time() > datetime.strptime('08:58:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('11:32:00', '%H:%M:%S').time()))
            or ((now.time() > datetime.strptime('13:28:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('15:02:00', '%H:%M:%S').time()))
            or ((now.time() > datetime.strptime('20:58:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('23:32:00', '%H:%M:%S').time()))):
            return True
        else:
            return False

    # ----------------------------------------------------------------------
    def checkConnect(self):
        self.checkCount += 1
        if self.checkCount == 5:
            self.checkCount = 0
            if self.isTradeTime() and (not self.tdConnected):
                self.connect()
            if not self.isTradeTime() and self.tdConnected:
                self.disconnect()

    # ----------------------------------------------------------------------
    def loadTradeConfig(self):
        try:
            f = file(config.TRADE_configPath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取交易配置出错，请检查'
            self.onLog(log)
            return

        # 解析json文件
        setting = json.load(f)
        try:
            config.currentMode = int(setting['todayMode'])
            self.tradeList = list(setting['todayTrade'])
        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'交易配置缺少字段，请检查'
            self.onLog(log)
            return

    # ----------------------------------------------------------------------
    def initTrade(self):
        for symbol in config.tradeSymbol:
            self.tradeDict[symbol] = tradeBar(symbol)
        if 'm1709' in self.tradeDict.keys():    #豆粕10点止盈
            self.tradeDict['m1709'].stopWin = True
            self.tradeDict['m1709'].winTarget = 10

    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        self.mdApi.subscribe(subscribeReq)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        return self.tdApi.sendOrder(orderReq)
        
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.tdApi.cancelOrder(cancelOrderReq)
        
    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户资金"""
        self.tdApi.qryAccount()
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.tdApi.qryPosition()
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        if self.mdConnected:
            self.mdApi.close()
        if self.tdConnected:
            self.tdApi.close()
        
    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryAccount, self.qryPosition]      #查询账户信息和持仓信息
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 2         # 查询触发点，查询周期，2为每两秒查询一次
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
    
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled

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
        if self.tradeDict[tick.symbol].noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice > ((self.tdApi.posBufferDict[symbol].pos.price / 10) + self.tradeDict[tick.symbol].winTarget):  # 最新价格大于止盈价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    # send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.tradeDict[tick.symbol].noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice < ((self.tdApi.posBufferDict[symbol].pos.price / 10) - self.tradeDict[tick.symbol].winTarget):  # 最新价格小于止盈价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    # send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.tradeDict[tick.symbol].noTrading = True
            else:
                pass

    # ----------------------------------------------------------------------
    def tradeStopLoss(self, tick):
        '''止损函数'''
        if self.tradeDict[tick.symbol].noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice < ((self.tdApi.posBufferDict[symbol].pos.price / 10) - self.tradeDict[tick.symbol].stopTarget):  # 最新价格小于止损价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止损单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    # send_msg(log.logContent.encode('utf-8'))
                    #发单
                    orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.tradeDict[tick.symbol].noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if tick.lastPrice > ((self.tdApi.posBufferDict[symbol].pos.price / 10) + self.tradeDict[tick.symbol].stopTarget):  # 最新价格大于止损价格
                    log = VtLogData()
                    log.gatewayName = self.gatewayName
                    log.logContent = u'[止损单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.onLog(log)
                    # send_msg(log.logContent.encode('utf-8'))
                    # 发单
                    orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                    self.sendOrder(orderReq)
                    self.tradeDict[tick.symbol].noTrading = True
            else:
                pass

    # ----------------------------------------------------------------------
    def tradeGetMaxWin(self, tick):
        '''摸顶止盈，当价格达到目标收益后，开始摸顶，从最高价回撤达到阈值，平仓止盈'''
        if self.tradeDict[tick.symbol].noTrading:
            return
        for symbol in self.tdApi.posBufferDict.keys():
            if symbol == (tick.symbol + '.2'):  # 多单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.tradeDict[tick.symbol].todayHigh >= self.tdApi.posBufferDict[symbol].pos.price / 10 + self.tradeDict[tick.symbol].winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice <= self.tradeDict[tick.symbol].todayHigh - self.tradeDict[tick.symbol].maxDrawDown:     #达到最大回撤
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        # send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].noTrading = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.tradeDict[tick.symbol].todayLow <= self.tdApi.posBufferDict[symbol].pos.price / 10 - self.tradeDict[tick.symbol].winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice >= self.tradeDict[tick.symbol].todayLow + self.tradeDict[tick.symbol].maxDrawDown:     #达到最大回撤
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        # send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].noTrading = True
            else:
                pass

    # ----------------------------------------------------------------------
    def Dual_Thrust(self, tick):
        if config.currentMode == 1:
            if tick.lastPrice >= tick.openPrice + 5 and (1 not in self.tradeList):
                self.openFlag = True
                self.openDirection = u'多'
            elif tick.lastPrice <= tick.openPrice - 15 and (0 not in self.tradeList):
                self.openFlag = True
                self.openDirection = u'空'
            else:
                pass
        elif config.currentMode == 0:
            if tick.lastPrice >= tick.openPrice + 15 and (1 not in self.tradeList):
                self.openFlag = True
                self.openDirection = u'多'
            elif tick.lastPrice <= tick.openPrice - 5 and (0 not in self.tradeList):
                self.openFlag = True
                self.openDirection = u'空'
            else:
                pass

    def shortPolicy(self, tick):
        # print '============================='
        # print 'symbol:',tick.symbol
        # print 'lastPrice:',tick.lastPrice
        # print 'openPrice:',tick.openPrice
        # print 'stopCount:',self.tradeDict[tick.symbol].stopCount
        # print 'noTrading:',self.tradeDict[tick.symbol].stopCount
        if self.tradeDict[tick.symbol].stopCount >= 4 or self.tradeDict[tick.symbol].noTrading:
            # print 'step1'
            return
        elif tick.lastPrice >= tick.openPrice + 2:
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys(): #存在空单
                # print 'step3'
                #空单止损
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].noTrading = True
                self.tradeDict[tick.symbol].stopCount += 1
            if tick.symbol + '.2' not in self.tdApi.posBufferDict.keys():     #无持仓
                # print 'step4'
                #开多单
                self.tradeDict[tick.symbol].openFlag = True
                self.tradeDict[tick.symbol].openDirection = u'多'
        elif tick.lastPrice <= tick.openPrice - 2:
            if tick.symbol + '.2' in self.tdApi.posBufferDict.keys(): #存在多单
                # print 'step6'
                #多单止损
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].noTrading = True
                self.tradeDict[tick.symbol].stopCount += 1
            if tick.symbol + '.3' not in self.tdApi.posBufferDict.keys():     #无持仓
                # print 'step7'
                #开空单
                self.tradeDict[tick.symbol].openFlag = True
                self.tradeDict[tick.symbol].openDirection = u'空'
        else:
            # print 'step8'
            pass

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time() and nowTime < datetime.strptime('15:00:05', '%H:%M:%S').time():
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys(): #存在空单
                #空单清仓
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].noTrading = True
            elif tick.symbol + '.2' in self.tdApi.posBufferDict.keys(): #存在多单
                #多单清仓
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].noTrading = True
            else:
                pass

    # ----------------------------------------------------------------------
    def tradeOpen(self, tick):
        '''开仓函数'''
        #存在持仓，不交易
        for symbol in self.tdApi.posBufferDict.keys():
            if tick.symbol in symbol:
                self.tradeDict[tick.symbol].openFlag = False
                return

        if self.tradeDict[tick.symbol].noTrading:
            return

        #无持仓，交易
        if self.tradeDict[tick.symbol].openDirection == u'多':
            orderReq = self.makeBuyOpenOrder(tick.symbol, tick.askPrice1, self.tradeDict[tick.symbol].tradeVolume)
        elif self.tradeDict[tick.symbol].openDirection == u'空':
            orderReq = self.makeSellOpenOrder(tick.symbol, tick.bidPrice1, self.tradeDict[tick.symbol].tradeVolume)
        else:
            return
        self.sendOrder(orderReq)
        self.tradeDict[tick.symbol].noTrading = True

        #记录日志
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[开仓单]合约代码：%s，价格：%s，数量：%s，方向：%s' % (
            tick.symbol, tick.bidPrice1, config.tradeVolume, self.tradeDict[tick.symbol].openDirection)
        self.onLog(log)
        # send_msg(log.logContent.encode('utf-8'))

        #重置最高价和最低价
        self.tradeDict[tick.symbol].todayLow = tick.lastPrice
        self.tradeDict[tick.symbol].todayHigh = tick.lastPrice

        #重置开仓标志
        self.tradeDict[tick.symbol].openFlag = False

    # ----------------------------------------------------------------------
    def initRecodeTick(self):
        '''重置实时行情缓存'''
        self.tickCount = 0
        self.tickDF1 = pd.DataFrame(columns=['symbol', 'date', 'time', 'lastPrice', 'lastVolume', 'bidPrice1', 'askPrice1', 'bidVolume1', 'askVolume1'])
        self.tickDF2 = pd.DataFrame(columns=['symbol', 'date', 'time', 'lastPrice', 'lastVolume', 'bidPrice1', 'askPrice1', 'bidVolume1', 'askVolume1'])

    # ----------------------------------------------------------------------
    def recodeTick(self, tick):
        '''记录实时行情'''
        newTick = pd.DataFrame([[tick.symbol, tick.date, tick.time, tick.lastPrice, tick.lastVolume, tick.bidPrice1, tick.askPrice1, tick.bidVolume1, tick.askVolume1]],
                           columns=['symbol', 'date','time','lastPrice', 'lastVolume','bidPrice1','askPrice1','bidVolume1', 'askVolume1'])
        if tick.symbol == config.tradeSymbol:
            self.tickDF1 = pd.concat([self.tickDF1, newTick], ignore_index=True)
        else: pass
        self.tickCount += 1
        if self.tickCount >= 50:
            self.today = datetime.now().date().strftime('%Y-%m-%d')
            # filename1 = '/home/myctp/vn.trader/ctpGateway/tickData/%s' % (config.analysisSymbol + '-' + self.today + '.csv')
            filename2 = '/home/myctp/vn.trader/ctpGateway/tickData/%s' % (config.tradeSymbol + '-' + self.today + '.csv')
            if os.path.exists(filename2):
                tickBuffer2 = pd.read_csv(filename2)
                tickBuffer2 = pd.concat([tickBuffer2, self.tickDF2], ignore_index=True)
                tickBuffer2.to_csv(filename2, index=False)
            else:
                self.tickDF2.to_csv(filename2, index=False)
            self.initRecodeTick()

    # ----------------------------------------------------------------------
    def pTick(self, event):
        '''tick事件处理机，当接收到行情时执行'''
        tick = event.dict_['data']

        # 获取当前时间
        now = datetime.now()

        # 休市
        if not self.isTradeTime():
            return

        self.shortPolicy(tick)

        if self.tradeDict[tick.symbol].stopLoss:
            self.tradeStopLoss(tick)

        if self.tradeDict[tick.symbol].stopWin:
            self.tradeStopWin(tick)

        if self.tradeDict[tick.symbol].openFlag:
            self.tradeOpen(tick)

    # ----------------------------------------------------------------------
    def pTick1(self, event):
        '''tick事件处理机，当接收到行情时执行'''
        tick = event.dict_['data']

        # 获取当前时间
        now = datetime.now()

        # 休市
        if not (((now.time() > datetime.strptime('09:00:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('11:31:00', '%H:%M:%S').time())) or \
                ((now.time() > datetime.strptime('13:30:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('15:31:00', '%H:%M:%S').time())) or \
                ((now.time() > datetime.strptime('21:00:00', '%H:%M:%S').time()) and (now.time() < datetime.strptime('23:31:00', '%H:%M:%S').time()))):
            return

        #记录行情
        if config.recodeTickFlag:
            self.recodeTick(tick)

        # 分析合约行情
        self.Dual_Thrust(tick)

        if tick.lastPrice > self.todayHigh:     #更新最高价
            self.todayHigh = tick.lastPrice
        if tick.lastPrice < self.todayLow:      #更新最低价
            self.todayLow = tick.lastPrice

        # print self.todayHigh
        # print self.todayLow
        # 平仓策略
        self.tradeGetMaxWin(tick)

        # 止盈
        if config.stopWin:
            self.tradeStopWin(tick)

        # 止损
        if config.stopLoss:
            self.tradeStopLoss(tick)

        #开仓
        if self.openFlag:
            self.tradeOpen(tick)

        # print config.currentMode
        # print self.tradeList
        # print self.todayHigh
        # print self.todayLow
        # print self.noTrading

    # ----------------------------------------------------------------------
    def pTrade(self, event):
        '''成交事件处理机，当订单成交回报时执行'''
        trade = event.dict_['data']
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[成交回报]合约代码：%s，订单编号：%s，价格：%s，数量：%s，方向：%s，开平仓：%s，成交编号：%s，成交时间：%s' % (
            trade.symbol, trade.orderID, trade.price, trade.volume, trade.direction, trade.offset, trade.tradeID, trade.tradeTime)
        self.onLog(log)
        # send_msg(log.logContent.encode('utf-8'))
        self.qryPosition()  #查询并更新持仓
        self.tradeDict[trade.symbol].noTrading = False
        if trade.offset == u'开仓':
            self.tradeDict[trade.symbol].todayHigh = 0
            self.tradeDict[trade.symbol].todayLow = 100000
            if trade.direction == u'空':
                self.tradeDict[trade.symbol].tradeList.append(0)
            elif trade.direction == u'多':
                self.tradeDict[trade.symbol].tradeList.append(1)
            else:
                pass
        # # 记录开仓交易
        # json_dict = {}
        # json_dict['todayMode'] = config.currentMode
        # json_dict['todayTrade'] = self.tradeList
        # f = open(config.TRADE_configPath, 'w')
        # f.write(json.dumps(json_dict))
        # f.close()
        # print 'trade info:'
        # print trade.symbol
        # print trade.exchange
        # print trade.vtSymbol
        # print trade.tradeID
        # print trade.vtTradeID
        # print trade.orderID
        # print trade.vtOrderID
        # print trade.direction
        # print trade.offset
        # print trade.price
        # print trade.volume
        # print trade.tradeTime
        # print '###############################'

    # ----------------------------------------------------------------------
    def pOrder(self, event):
        '''订单事件处理机，当收到订单回报时执行'''
        order = event.dict_['data']
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[订单回报]合约代码：%s，订单编号：%s，价格：%s，数量：%s，方向：%s，开平仓：%s，订单状态：%s，报单时间：%s' % (
            order.symbol, order.orderID, order.price, order.totalVolume, order.direction, order.offset, order.status, order.orderTime)
        self.onLog(log)

        # print 'order info:'
        # print order.symbol
        # print order.exchange
        # print order.vtSymbol
        # print order.orderID
        # print order.vtOrderID
        # print order.direction
        # print order.offset
        # print order.price
        # print order.totalVolume
        # print order.tradedVolume
        # print order.status
        # print order.orderTime
        # print order.cancelTime
        # print order.frontID
        # print order.sessionID
        # print '###############################'

    # ----------------------------------------------------------------------
    def pPosition(self,event):
        '''持仓事件处理机，当收到持仓消息时执行'''
        pos = event.dict_['data']
        # for positionName in self.tdApi.posBufferDict.keys():
        #     print '###############################'
        #     print 'position info:'
        #     print self.tdApi.posBufferDict[positionName].pos.symbol
        #     print self.tdApi.posBufferDict[positionName].pos.direction
        #     print self.tdApi.posBufferDict[positionName].pos.position
        #     print self.tdApi.posBufferDict[positionName].pos.frozen
        #     print self.tdApi.posBufferDict[positionName].pos.price
        #     print self.tdApi.posBufferDict[positionName].pos.vtPositionName

    # ----------------------------------------------------------------------
    def pAccount(self, event):
        '''账户信息事件处理机，当收到账户信息时执行'''
        account = event.dict_['data']
        # print 'account info:'
        # print account.accountID
        # print account.vtAccountID
        # print account.preBalance
        # print account.balance
        # print account.available
        # print account.commission
        # print account.margin
        # print account.closeProfit
        # print account.positionProfit
        # print '###############################'

    # ----------------------------------------------------------------------
    def pError(self, event):
        error = event.dict_['data']
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[错误信息]错误代码：%s，错误信息：%s' % (error.errorID, error.errorMsg)
        self.onLog(log)
        if error.errorID == '30':
            #平仓量超过持仓量
            for symbol in self.tradeDict.keys():
                self.tradeDict[symbol].noTrading = False

        # print 'errorid:',error.errorID
        # print 'errormsg:',error.errorMsg

    # ----------------------------------------------------------------------
    def pLog(self, event):
        log = event.dict_['data']
        loginfo = ':'.join([log.logTime, log.logContent])
        # send_msg(loginfo)
        # print loginfo
        self.today = datetime.now().date().strftime('%Y-%m-%d')
        filename = '/home/myctp/vn.trader/ctpGateway/log/%s' % ('tradeLog' + '-' + self.today + '.txt')
        if os.path.exists(filename):
            fp = file(filename, 'a+')
            try:
                fp.write(loginfo.encode('utf-8') + '\n')
            finally:
                fp.close()
        else:
            fp = file(filename, 'wb')
            try:
                fp.write(loginfo.encode('utf-8') + '\n')
            finally:
                fp.close()

    # ----------------------------------------------------------------------
    def pContract(self, event):
        contract = event.dict_['data']
        # print 'contract info:'
        # print contract.symbol
        # print contract.exchange
        # print contract.vtSymbol
        # print contract.name
        # print contract.productClass
        # print contract.size
        # print contract.priceTick
        # print '###############################'

    # ----------------------------------------------------------------------
    def registeHandle(self):
        '''注册处理机'''
        self.eventEngine.register(EVENT_TIMER, self.checkCount)
        self.eventEngine.register(EVENT_LOG, self.pLog)
        self.eventEngine.register(EVENT_TICK, self.pTick)
        self.eventEngine.register(EVENT_TRADE, self.pTrade)
        self.eventEngine.register(EVENT_ORDER, self.pOrder)
        self.eventEngine.register(EVENT_POSITION, self.pPosition)
        self.eventEngine.register(EVENT_CONTRACT, self.pContract)
        self.eventEngine.register(EVENT_ACCOUNT, self.pAccount)
        self.eventEngine.register(EVENT_ERROR, self.pError)


########################################################################
def test():
    """测试"""
    from PyQt4 import QtCore
    import sys
    
    def print_log(event):
        log = event.dict_['data']
        print ':'.join([log.logTime, log.logContent])
    
    app = QtCore.QCoreApplication(sys.argv)    

    eventEngine = EventEngine()
    eventEngine.register(EVENT_LOG, print_log)
    eventEngine.start()
    
    gateway = CtpGateway(eventEngine)
    gateway.connect()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()