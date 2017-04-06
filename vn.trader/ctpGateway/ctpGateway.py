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
from ctpDataType import *
from vtGateway import *
from config import *
from weixin import *
import pandas as pd


# 以下为一些VT类型和CTP类型的映射字典
# 价格类型映射
priceTypeMap = {}
priceTypeMap[PRICETYPE_LIMITPRICE] = defineDict["THOST_FTDC_OPT_LimitPrice"]
priceTypeMap[PRICETYPE_MARKETPRICE] = defineDict["THOST_FTDC_OPT_AnyPrice"]
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 

# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = defineDict['THOST_FTDC_D_Buy']
directionMap[DIRECTION_SHORT] = defineDict['THOST_FTDC_D_Sell']
directionMapReverse = {v: k for k, v in directionMap.items()}

# 开平类型映射
offsetMap = {}
offsetMap[OFFSET_OPEN] = defineDict['THOST_FTDC_OF_Open']
offsetMap[OFFSET_CLOSE] = defineDict['THOST_FTDC_OF_Close']
offsetMap[OFFSET_CLOSETODAY] = defineDict['THOST_FTDC_OF_CloseToday']
offsetMap[OFFSET_CLOSEYESTERDAY] = defineDict['THOST_FTDC_OF_CloseYesterday']
offsetMapReverse = {v:k for k,v in offsetMap.items()}

# 交易所类型映射
exchangeMap = {}
exchangeMap[EXCHANGE_CFFEX] = 'CFFEX'
exchangeMap[EXCHANGE_SHFE] = 'SHFE'
exchangeMap[EXCHANGE_CZCE] = 'CZCE'
exchangeMap[EXCHANGE_DCE] = 'DCE'
exchangeMap[EXCHANGE_SSE] = 'SSE'
exchangeMap[EXCHANGE_UNKNOWN] = ''
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# 持仓类型映射
posiDirectionMap = {}
posiDirectionMap[DIRECTION_NET] = defineDict["THOST_FTDC_PD_Net"]
posiDirectionMap[DIRECTION_LONG] = defineDict["THOST_FTDC_PD_Long"]
posiDirectionMap[DIRECTION_SHORT] = defineDict["THOST_FTDC_PD_Short"]
posiDirectionMapReverse = {v:k for k,v in posiDirectionMap.items()}

# 产品类型映射
productClassMap = {}
productClassMap[PRODUCT_FUTURES] = defineDict["THOST_FTDC_PC_Futures"]
productClassMap[PRODUCT_OPTION] = defineDict["THOST_FTDC_PC_Options"]
productClassMap[PRODUCT_COMBINATION] = defineDict["THOST_FTDC_PC_Combination"]
productClassMapReverse = {v:k for k,v in productClassMap.items()}



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

        #----交易策略使用的参数-----
        self.todayHigh = 0                          # 今天最高价
        self.todayLow = 1000000                     # 今天最低价
        self.preSellPrice = 0                       # 上次卖出价

        self.openFlag = False                       # 开仓标志
        self.noTrading = False                      #是否存在未成交订单
        self.tradeList = []
        self.stopCount = 0      #止损次数
        self.initRecodeTick()
        self.loadTradeConfig()

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
        # print 'lastPrice:',tick.lastPrice
        # print 'openPrice:',tick.openPrice
        # print 'stopCount:',self.stopCount
        # print 'noTrading:',self.noTrading
        if self.stopCount >= 4 or self.noTrading:
            # print 'step1'
            return
        elif tick.lastPrice >= tick.openPrice + 2:
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys(): #存在空单
                # print 'step3'
                #空单止损
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.noTrading = True
                self.stopCount += 1
            if tick.symbol + '.2' in self.tdApi.posBufferDict.keys():  # 存在多单
                # print 'step2'
                pass  # 不操作
            elif len(self.tdApi.posBufferDict.keys()) == 0:     #无持仓
                # print 'step4'
                #开多单
                orderReq = self.makeBuyOpenOrder(tick.symbol, tick.askPrice1, config.tradeVolume)
                self.sendOrder(orderReq)
                self.noTrading = True
        elif tick.lastPrice <= tick.openPrice - 2:
            if tick.symbol + '.2' in self.tdApi.posBufferDict.keys(): #存在多单
                # print 'step6'
                #多单止损
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.noTrading = True
                self.stopCount += 1
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys():  # 存在空单
                # print 'step5'
                pass  # 不操作
            elif len(self.tdApi.posBufferDict.keys()) == 0:     #无持仓
                # print 'step7'
                #开空单
                orderReq = self.makeSellOpenOrder(tick.symbol, tick.bidPrice1, config.tradeVolume)
                self.sendOrder(orderReq)
                self.noTrading = True
        else:
            # print 'step8'
            pass

        # 收盘清仓
        now = datetime.now()
        if now.time() > datetime.strptime('14:59:00', '%H:%M:%S').time():
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys(): #存在空单
                #空单清仓
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.noTrading = True
            elif tick.symbol + '.2' in self.tdApi.posBufferDict.keys(): #存在多单
                #多单清仓
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.noTrading = True
            else:
                pass


    # ----------------------------------------------------------------------
    def tradeOpen(self, tick):
        '''开仓函数'''
        #存在持仓，不交易
        for symbol in self.tdApi.posBufferDict.keys():
            if tick.symbol in symbol:
                self.openFlag = False
                return

        if self.noTrading:
            return

        #无持仓，交易
        if self.openDirection == u'多':
            orderReq = self.makeBuyOpenOrder(tick.symbol, tick.askPrice1, config.tradeVolume)
        elif self.openDirection == u'空':
            orderReq = self.makeSellOpenOrder(tick.symbol, tick.bidPrice1, config.tradeVolume)
        else:
            return
        self.sendOrder(orderReq)
        self.noTrading = True

        #记录日志
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[开仓单]合约代码：%s，价格：%s，数量：%s，方向：%s' % (
            tick.symbol, tick.bidPrice1, config.tradeVolume, self.openDirection)
        self.onLog(log)
        send_msg(log.logContent.encode('utf-8'))

        #重置最高价和最低价
        self.todayLow = tick.lastPrice
        self.todayHigh = tick.lastPrice

        #重置开仓标志
        self.openFlag = False

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
        if not (((now.time() > datetime.strptime('09:00:00', '%H:%M:%S').time()) and (
            now.time() < datetime.strptime('11:31:00', '%H:%M:%S').time())) or \
                ((now.time() > datetime.strptime('13:30:00', '%H:%M:%S').time()) and (
                now.time() < datetime.strptime('15:31:00', '%H:%M:%S').time())) or \
                ((now.time() > datetime.strptime('21:00:00', '%H:%M:%S').time()) and (
                now.time() < datetime.strptime('23:31:00', '%H:%M:%S').time()))):
            return

        # 记录行情
        if config.recodeTickFlag:
            self.recodeTick(tick)

        self.shortPolicy(tick)

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
        send_msg(log.logContent.encode('utf-8'))
        self.qryPosition()  #查询并更新持仓
        self.noTrading = False
        if trade.offset == u'开仓':
            self.todayHigh = 0
            self.todayLow = 100000
            if trade.direction == u'空':
                self.tradeList.append(0)
            elif trade.direction == u'多':
                self.tradeList.append(1)
            else:
                pass
        # 记录开仓交易
        json_dict = {}
        json_dict['todayMode'] = config.currentMode
        json_dict['todayTrade'] = self.tradeList
        f = open(config.TRADE_configPath, 'w')
        f.write(json.dumps(json_dict))
        f.close()
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
        self.eventEngine.register(EVENT_LOG, self.pLog)
        self.eventEngine.register(EVENT_TICK, self.pTick)
        self.eventEngine.register(EVENT_TRADE, self.pTrade)
        self.eventEngine.register(EVENT_ORDER, self.pOrder)
        self.eventEngine.register(EVENT_POSITION, self.pPosition)
        self.eventEngine.register(EVENT_CONTRACT, self.pContract)
        self.eventEngine.register(EVENT_ACCOUNT, self.pAccount)
        self.eventEngine.register(EVENT_ERROR, self.pError)


########################################################################
class PositionBuffer(object):
    """用来缓存持仓的数据，处理上期所的数据返回分今昨的问题"""

    #----------------------------------------------------------------------
    def __init__(self, data, gatewayName):
        """Constructor"""
        self.symbol = data['InstrumentID']
        self.direction = posiDirectionMapReverse.get(data['PosiDirection'], '')
        
        self.todayPosition = EMPTY_INT
        self.ydPosition = EMPTY_INT
        self.todayPositionCost = EMPTY_FLOAT
        self.ydPositionCost = EMPTY_FLOAT
        
        # 通过提前创建持仓数据对象并重复使用的方式来降低开销
        pos = VtPositionData()
        pos.symbol = self.symbol
        pos.vtSymbol = self.symbol
        pos.gatewayName = gatewayName
        pos.direction = self.direction
        pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction]) 
        self.pos = pos
        
    #----------------------------------------------------------------------
    def updateShfeBuffer(self, data, size):
        """更新上期所缓存，返回更新后的持仓数据"""
        # 昨仓和今仓的数据更新是分在两条记录里的，因此需要判断检查该条记录对应仓位
        # 因为今仓字段TodayPosition可能变为0（被全部平仓），因此分辨今昨仓需要用YdPosition字段
        if data['YdPosition']:
            self.ydPosition = data['Position']
            self.ydPositionCost = data['PositionCost']   
        else:
            self.todayPosition = data['Position']
            self.todayPositionCost = data['PositionCost']        
            
        # 持仓的昨仓和今仓相加后为总持仓
        self.pos.position = self.todayPosition + self.ydPosition
        self.pos.ydPosition = self.ydPosition
        
        # 如果手头还有持仓，则通过加权平均方式计算持仓均价
        if self.todayPosition or self.ydPosition:
            self.pos.price = ((self.todayPositionCost + self.ydPositionCost)/
                              ((self.todayPosition + self.ydPosition) * size))
        # 否则价格为0
        else:
            self.pos.price = 0
            
        return copy(self.pos)
    
    #----------------------------------------------------------------------
    def updateBuffer(self, data, size):
        """更新其他交易所的缓存，返回更新后的持仓数据"""
        # 其他交易所并不区分今昨，因此只关心总仓位，昨仓设为0
        self.pos.position = data['Position']
        self.pos.ydPosition = 0
        
        if data['Position']:
            self.pos.price = data['PositionCost'] / (data['Position'] * size)
        else:
            self.pos.price = 0
            
        return copy(self.pos)    


#----------------------------------------------------------------------


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