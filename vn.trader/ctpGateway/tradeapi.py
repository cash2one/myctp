# encoding: UTF-8
from ctpGateway import *

class tradeAPI(CtpGateway):

    def __init__(self, eventEngine, gatewayName='CTP'):
        super(tradeAPI, self).__init__(eventEngine, gatewayName)

        self.stopLong = False       #不再开多仓
        self.stopShort = False      #不再开空仓

        self.accountInfo = VtAccountData()
        self.recodeAccount = False
        # 注册事件处理函数
        self.registeHandle()

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
        if longPosition in self.tdApi.posBufferDict.keys():
            if tick.lastPrice >= self.tdApi.posBufferDict[longPosition].pos.stopWinPrice:  # 最新价格大于止盈价格
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.onLog(log)
                send_msg(log.logContent.encode('utf-8'))
                #发单
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
                self.tradeDict[tick.symbol].tradeList.append(u'多')      # 多单盈利
        if shortPosition == (tick.symbol + '.3'):  # 空单
            if tick.lastPrice <= self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice:  # 最新价格小于止盈价格
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.onLog(log)
                send_msg(log.logContent.encode('utf-8'))
                #发单
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
                self.tradeDict[tick.symbol].tradeList.append(u'空')  # 空单盈利
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
        if longPosition in self.tdApi.posBufferDict.keys():
            if tick.lastPrice <= self.tdApi.posBufferDict[longPosition].pos.stopLossPrice:  # 最新价格小于止损价格
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[止损单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.onLog(log)
                send_msg(log.logContent.encode('utf-8'))
                #发单
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[longPosition].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].stopCount += 1
                self.tradeDict[tick.symbol].closeing = True
        if shortPosition in self.tdApi.posBufferDict.keys():  # 空单
            if tick.lastPrice >= self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice:  # 最新价格大于止损价格
                log = VtLogData()
                log.gatewayName = self.gatewayName
                log.logContent = u'[止损单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.onLog(log)
                send_msg(log.logContent.encode('utf-8'))
                # 发单
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[shortPosition].pos.position)
                self.sendOrder(orderReq)
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
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]多单卖出，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.bidPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].closeing = True
            elif symbol == (tick.symbol + '.3'):  # 空单
                if self.tdApi.posBufferDict[symbol].pos.position - self.tdApi.posBufferDict[symbol].pos.frozen == 0:
                    continue
                if self.tradeDict[tick.symbol].todayLow <= self.tdApi.posBufferDict[symbol].pos.price / 10 - self.tradeDict[tick.symbol].winTarget:  # 当天价格达到过目标收益
                    if tick.lastPrice >= self.tradeDict[tick.symbol].todayLow + self.tradeDict[tick.symbol].maxDrawDown:     #达到最大回撤
                        log = VtLogData()
                        log.gatewayName = self.gatewayName
                        log.logContent = u'[摸顶止盈单]空单买入，合约代码：%s，价格：%s，数量：%s' % (tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.onLog(log)
                        send_msg(log.logContent.encode('utf-8'))
                        #发单
                        orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1, self.tdApi.posBufferDict[symbol].pos.position)
                        self.sendOrder(orderReq)
                        self.tradeDict[tick.symbol].closeing = True
            else:
                pass

    # ----------------------------------------------------------------------
    def shortPolicy1(self, tick):
        """持仓到收盘"""
        print '============================='
        print 'symbol:',tick.symbol
        print 'lastPrice:',tick.lastPrice
        print 'openPrice:',tick.openPrice
        print 'stopCount:',self.tradeDict[tick.symbol].stopCount
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
        elif tick.lastPrice < lowThreshold:
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = u'空'
        else:
            pass


        # 存在多单,设置止损价位，打开止损开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = lowThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            # 涨停价止盈
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = tick.upperLimit
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif tick.lastPrice > highThreshold:
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = u'多'
        else:
            pass

        #涨停不开多单
        if tick.highPrice >= tick.upperLimit:
            self.stopLong = True
        #跌停不开空单
        if tick.lowPrice <= tick.lowerLimit:
            self.stopShort = True

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (nowTime <= datetime.strptime('15:00:00', '%H:%M:%S').time()):
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys(): #存在空单
                #空单清仓
                # print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
            if tick.symbol + '.2' in self.tdApi.posBufferDict.keys(): #存在多单
                #多单清仓
                # print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
            self.stopLong = True
            self.stopShort = True

    # ----------------------------------------------------------------------
    def shortPolicy2(self, tick):
        """两边10点止盈"""
        print '============================='
        print 'symbol:',tick.symbol
        print 'lastPrice:',tick.lastPrice
        print 'openPrice:',tick.openPrice
        print 'stopCount:',self.tradeDict[tick.symbol].stopCount
        print 'closeing:',self.tradeDict[tick.symbol].closeing
        highThreshold = tick.openPrice + self.tradeDict[tick.symbol].tickPrice * 2
        lowThreshold = tick.openPrice - self.tradeDict[tick.symbol].tickPrice * 2

        longPosition = tick.symbol + '.2'
        shortPosition = tick.symbol + '.3'

        # 存在空单,设置止损止盈价位，打开止损止盈开关
        if shortPosition in self.tdApi.posBufferDict.keys():
            print 'step1'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = highThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = \
                self.tdApi.posBufferDict[tick.symbol].pos.price - self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].winTickPrice
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在空单，且价格达到低阈值，开空单
        elif (tick.lastPrice < lowThreshold) and (u'空' not in self.tradeDict[tick.symbol].tradeList):
            print 'step2'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = u'空'
        else:
            pass

        # 存在多单,设置止损止盈价位，打开止损止盈开关
        if longPosition in self.tdApi.posBufferDict.keys():
            print 'step3'
            self.tdApi.posBufferDict[shortPosition].pos.stopLossPrice = lowThreshold
            self.tradeDict[tick.symbol].stopLoss = True
            self.tdApi.posBufferDict[shortPosition].pos.stopWinPrice = \
                self.tdApi.posBufferDict[tick.symbol].pos.price + self.tradeDict[tick.symbol].tickPrice * self.tradeDict[tick.symbol].winTickPrice
            self.tradeDict[tick.symbol].stopWin = True
        # 不存在多单，且价格达到高阈值，开多单
        elif (tick.lastPrice > highThreshold) and (u'多' not in self.tradeDict[tick.symbol].tradeList):
            print 'step4'
            self.tradeDict[tick.symbol].openFlag = True
            self.tradeDict[tick.symbol].openDirection = u'多'
        else:
            pass

        # 收盘清仓
        nowTime = datetime.strptime(tick.time.split('.')[0], '%H:%M:%S').time()
        if (nowTime > datetime.strptime('14:59:55', '%H:%M:%S').time()) and (nowTime <= datetime.strptime('15:00:00','%H:%M:%S').time()):
            if tick.symbol + '.3' in self.tdApi.posBufferDict.keys():  # 存在空单
                # 空单清仓
                # print 'step9'
                orderReq = self.makeBuyCloseOrder(tick.symbol, tick.askPrice1,self.tdApi.posBufferDict[tick.symbol + '.3'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
            if tick.symbol + '.2' in self.tdApi.posBufferDict.keys():  # 存在多单
                # 多单清仓
                # print 'step10'
                orderReq = self.makeSellCloseOrder(tick.symbol, tick.bidPrice1,self.tdApi.posBufferDict[tick.symbol + '.2'].pos.position)
                self.sendOrder(orderReq)
                self.tradeDict[tick.symbol].closeing = True
            self.stopLong = True
            self.stopShort = True

    # ----------------------------------------------------------------------
    def tradeOpen(self, tick):
        '''开仓函数'''
        
        # 开仓标志位false
        if not self.tradeDict[tick.symbol].openFlag:
            return
        # 停止开多仓
        if self.stopLong and (self.tradeDict[tick.symbol].openDirection == u'多'):
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 停止开空仓
        if self.stopShort and (self.tradeDict[tick.symbol].openDirection == u'空'):
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 未获取到持仓信息
        if not self.getPosition:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 存在未成交的开仓单
        if self.tradeDict[tick.symbol].opening:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 今天止损达到3次
        if self.tradeDict[tick.symbol].stopCount >= 3:
            self.tradeDict[tick.symbol].openFlag = False
            return
        # 存在持仓
        if (tick.symbol + '.2' in self.tdApi.posBufferDict.keys()) or (tick.symbol + '.3' in self.tdApi.posBufferDict.keys()):
            self.tradeDict[tick.symbol].openFlag = False
            return

        #其他情况，执行开仓指令
        if self.tradeDict[tick.symbol].openDirection == u'多':
            orderReq = self.makeBuyOpenOrder(tick.symbol, tick.askPrice1, self.tradeDict[tick.symbol].tradeVolume)
        elif self.tradeDict[tick.symbol].openDirection == u'空':
            orderReq = self.makeSellOpenOrder(tick.symbol, tick.bidPrice1, self.tradeDict[tick.symbol].tradeVolume)
        else:
            self.tradeDict[tick.symbol].openFlag = False
            return
        self.sendOrder(orderReq)
        self.tradeDict[tick.symbol].opening = True
        self.tradeDict[tick.symbol].openFlag = False

        #记录日志
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[开仓单]合约代码：%s，价格：%s，数量：%s，方向：%s' % (
            tick.symbol, tick.bidPrice1, self.tradeDict[tick.symbol].tradeVolume, self.tradeDict[tick.symbol].openDirection)
        self.onLog(log)
        send_msg(log.logContent.encode('utf-8'))

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

        # 策略函数
        self.shortPolicy1(tick)

        # 止损
        self.tradeStopLoss(tick)

        # 止盈
        self.tradeStopWin(tick)

        # 开仓
        self.tradeOpen(tick)

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
        if trade.symbol not in self.tradeDict.keys():
            return
        if trade.offset == u'开仓':
            self.tradeDict[trade.symbol].opening = False
            self.tradeDict[trade.symbol].todayHigh = trade.price
            self.tradeDict[trade.symbol].todayLow = trade.price
        else:
            self.tradeDict[trade.symbol].closeing = False
        # # 记录开仓交易
        # json_dict = {}
        # json_dict['todayMode'] = config.currentMode
        # json_dict['todayTrade'] = self.tradeList
        # f = open(config.TRADE_configPath, 'w')
        # f.write(json.dumps(json_dict))
        # f.close()

    # ----------------------------------------------------------------------
    def pOrder(self, event):
        '''订单事件处理机，当收到订单回报时执行'''
        order = event.dict_['data']
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'[订单回报]合约代码：%s，订单编号：%s，价格：%s，数量：%s，方向：%s，开平仓：%s，订单状态：%s，报单时间：%s' % (
            order.symbol, order.orderID, order.price, order.totalVolume, order.direction, order.offset, order.status, order.orderTime)
        self.onLog(log)

    # ----------------------------------------------------------------------
    def pPosition(self,event):
        '''持仓事件处理机，当收到持仓消息时执行'''
        pos = event.dict_['data']
        self.getPosition = True
        for positionName in self.tdApi.posBufferDict.keys():
            print '###############################'
            print 'position info:'
            print self.tdApi.posBufferDict[positionName].pos.symbol
            print self.tdApi.posBufferDict[positionName].pos.direction
            print self.tdApi.posBufferDict[positionName].pos.position
            print self.tdApi.posBufferDict[positionName].pos.frozen
            print self.tdApi.posBufferDict[positionName].pos.price
            print self.tdApi.posBufferDict[positionName].pos.vtPositionName

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
        if (nowTime > datetime.strptime('15:00:30', '%H:%M:%S').time()) and (not self.recodeAccount):
            fp = file(config.BALANCE_file, 'a+')
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