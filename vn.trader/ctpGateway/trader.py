# encoding: UTF-8

class tradeBar(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.currentMode = 1  # 当前运行模式：1:多，0:空
        self.winTarget = 10  # 盈利目标点数，浮盈达到该点数，止盈
        self.stopTarget = 20  # 止损目标点数，浮亏达到该点数，止损
        self.winTargetPrice = 100000      #止盈目标价位，当前价格达到该价格，止盈
        self.stopTargetPrice = 0          #止损目标价位，当前价格达到该价格，止损
        self.preSellPrice = 0             #上次平仓价位
        self.maxDrawDown = 3  # 允许最大回撤点数，从最高价格回撤达到该点数，止盈
        self.stopLoss = False  # 是否止损
        self.stopWin = False  # 是否止盈
        self.threshold = 2
        self.tradeVolume = 1  # 交易数量
        self.openFlag = False  # 开仓标志
        self.openDirection = u'多'
        self.closeing = False  # 是否存在未成交平仓单
        self.opening = False    #存在未成交开仓单
        self.tradeList = []
        self.stopCount = 0  # 止损次数
        self.todayHigh = 0  # 今天最高价
        self.todayLow = 1000000  # 今天最低价
        self.preSellPrice = 0  # 上次卖出价

if __name__ == '__main__':
    b = {}
    b['1'] = tradeBar('m109')
    b['1'].winTargetPrice = 20
    print b['1'].winTargetPrice
    print b['1'].symbol