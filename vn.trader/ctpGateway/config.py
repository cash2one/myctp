# encoding: UTF-8

class config:
    currentMode = 1             #当前运行模式：1:多，0:空
    winTarget = 10                #盈利目标点数，浮盈达到该点数，止盈
    stopTarget = 20              #止损目标点数，浮亏达到该点数，止损
    # winTargetPrice = 100000      #止盈目标价位，当前价格达到该价格，止盈
    # stopTargetPrice = 0          #止损目标价位，当前价格达到该价格，止损
    # preSellPrice = 0             #上次平仓价位
    maxDrawDown = 3              #允许最大回撤点数，从最高价格回撤达到该点数，止盈
    stopLoss = False             #是否止损
    stopWin = False              #是否止盈

    # analysisSymbol = 'm1705'     #分析合约，美豆
    tradeSymbol = ['RM709']       #交易合约，菜粕
    tradeVolume = 1              #交易数量
    recodeTickFlag = True        #是否记录实时行情
    CTP_configPath = '/home/myctp/vn.trader/ctpGateway/CTP_connect.json'
    TRADE_configPath = '/home/myctp/vn.trader/ctpGateway/tradeConfig.json'