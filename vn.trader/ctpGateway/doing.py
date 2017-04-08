# encoding: UTF-8
from vtConstant import *

class tradeBar(object):
    def __init__(self, symbol, gateway):
        self.symbol = symbol                    # 合约
        self.gateway = gateway
        self.currentMode = EMPTY_INT            # 当前运行模式：1:多，0:空
        self.winTickPrice = EMPTY_INT           # 盈利目标点数(最小价格的倍数)，浮盈达到该点数，止盈
        self.stopTickPrice = EMPTY_INT          # 止损目标点数(最小价格的倍数)，浮亏达到该点数，止损
        self.winTargetPrice = EMPTY_FLOAT       # 止盈目标价位(真实价格)，当前价格达到该价格，止盈
        self.stopTargetPrice = EMPTY_FLOAT      # 止损目标价位(真实价格)，当前价格达到该价格，止损
        self.preSellPrice = EMPTY_FLOAT         # 上次平仓价格
        self.maxDrawDown = EMPTY_INT            # 允许最大回撤点数(最小价格的倍数)，从最高价格回撤达到该点数，止盈
        self.stopLoss = EMPTY_BOOL              # 是否止损
        self.stopCount = EMPTY_INT              # 止损次数
        self.stopWin = EMPTY_BOOL               # 是否止盈
        self.tradeVolume = EMPTY_INT            # 交易手数
        self.openFlag = EMPTY_BOOL              # 开仓标志
        self.openDirection = EMPTY_UNICODE      # 开仓方向，多或者空
        self.closeing = EMPTY_BOOL              # 是否存在未成交平仓单
        self.opening = EMPTY_BOOL               # 是否存在未成交开仓单
        self.tradeList = EMPTY_LIST             # 记录交易历史
        self.todayHigh = EMPTY_FLOAT            # 今天最高价
        self.todayLow = EMPTY_FLOAT             # 今天最低价

if __name__ == '__main__':
    b = {}
    b['1'] = tradeBar('m109')
    b['1'].winTargetPrice = 20
    print b['1'].winTargetPrice
    print b['1'].symbol