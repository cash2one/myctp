# encoding: UTF-8

class config:
    currentMode = u'多'          #当前运行模式：多或者空
    winTarget = 30               #盈利目标点数，浮盈达到该点数，止盈
    stopTarget = 20              #止损目标点数，浮亏达到该点数，止损
    winTargetPrice = 100000      #平仓目标价位，当前价格达到该价格，止盈
    stopTargetPrice = 0          #平仓目标价位，当前价格达到该价格，止损
    preSellPrice = 0             #上次平仓价位
    maxDrawDown = 10             #允许最大回撤点数，从最高价格回撤达到该点数，止盈
    stopLoss = False             #是否止损
    stopWin = False              #是否止盈