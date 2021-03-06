# encoding: UTF-8
from vtConstant import *
from config import *
from weixin import *
import json
from pHist import *
from mysqlApi import *


def reconfig():
    '''初始化交易参数，读取json文件，转换成DataFrame并存入数据库中'''
    fileName = config.basePath + 'myctp/vn.trader/ctpGateway/TRADE_setting.json'
    # fileName = 'TRADE_setting.json'
    try:
        f = file(fileName)
    except IOError:
        logContent = u'读取交易配置出错，请检查'
        send_msg(logContent.encode('utf-8'))
        return

    # 解析json文件
    setting = json.load(f)
    df = pd.DataFrame(setting).T
    df['symbol'] = df.index
    df.index = range(df.shape[0])
    sql = SqlApi()
    sql.saveToSql(df, config.tableName)

def saveConfig(data):
    '''将交易时段的临时数据保存到数据库中，传入CtpGateway中的tradeDict'''
    dataList = []
    for key in data.keys():
        dataList.append(data[key].__dict__)
    df = pd.DataFrame(dataList)
    sql = SqlApi()
    sql.saveToSql(df, config.tableName)

class tradeBar(object):
    def __init__(self, symbol):
        self.symbol = symbol                    # 合约代码
        self.loadConfig()
        # self.tickPrice = EMPTY_FLOAT            # 合约价格最小变动单位
        # self.size = EMPTY_INT                   # 每手合约数量
        # self.currentMode = EMPTY_UNICODE        # 当前运行模式：多，空
        # self.winTickPrice = EMPTY_INT           # 盈利目标点数(最小价格的倍数)，浮盈达到该点数，止盈
        # self.stopTickPrice = EMPTY_INT          # 止损目标点数(最小价格的倍数)，浮亏达到该点数，止损
        # self.winTargetPrice = EMPTY_FLOAT       # 止盈目标价位(真实价格)，当前价格达到该价格，止盈
        # self.stopTargetPrice = EMPTY_FLOAT      # 止损目标价位(真实价格)，当前价格达到该价格，止损
        # self.preSellPrice = EMPTY_FLOAT         # 上次平仓价格
        # self.maxDrawDown = EMPTY_INT            # 允许最大回撤点数(最小价格的倍数)，从最高价格回撤达到该点数，止盈
        # self.stopLoss = EMPTY_BOOL              # 是否止损
        # self.stopCount = EMPTY_INT              # 止损次数
        # self.winCount = EMPTY_INT               # 止盈次数
        # self.stopWin = EMPTY_BOOL               # 是否止盈
        # self.tradeVolume = EMPTY_INT            # 交易手数
        # self.stopLong = EMPTY_BOOL              # 不再开多仓
        # self.stopShort = EMPTY_BOOL             # 不再开空仓
        # self.status = EMPTY_INT                 # 当前状态
        # self.perHigh = EMPTY_FLOAT              # 前一天最高价
        # self.perLow = EMPTY_FLOAT               # 前一天最低价
        self.closeCount = EMPTY_INT             # 平仓次数
        self.openFlag = EMPTY_BOOL              # 开仓标志
        self.openDirection = EMPTY_STRING       # 开仓方向，多或者空
        self.closeing = EMPTY_BOOL              # 是否存在未成交平仓单
        self.opening = EMPTY_BOOL               # 是否存在未成交开仓单
        self.doWin = EMPTY_BOOL                 # 正在止盈
        self.doLoss = EMPTY_BOOL                # 正在止损
        # self.tradeList = EMPTY_LIST             # 记录交易历史
        self.todayHigh = EMPTY_FLOAT            # 今天最高价
        self.todayLow = EMPTY_FLOAT             # 今天最低价
        self.tickCount = EMPTY_INT
        self.update()

    def loadConfig(self):
        '''从数据库中读取交易参数，用来初始化类成员'''
        sql = SqlApi()
        newdf = sql.readFromSql(config.tableName)
        newdf = newdf.drop(['index'], axis=1)
        newdf.index = newdf['symbol']
        newdf['tickPrice'] = newdf['tickPrice'].astype(float)
        newdf['size'] = newdf['size'].astype(int)
        newdf['currentMode'] = newdf['currentMode'].astype(str)
        newdf['winTickPrice'] = newdf['winTickPrice'].astype(int)
        newdf['stopTickPrice'] = newdf['stopTickPrice'].astype(int)
        newdf['winTargetPrice'] = newdf['winTargetPrice'].astype(float)
        newdf['stopTargetPrice'] = newdf['stopTargetPrice'].astype(float)
        newdf['preSellPrice'] = newdf['preSellPrice'].astype(float)
        newdf['maxDrawDown'] = newdf['maxDrawDown'].astype(int)
        newdf['stopLoss'] = newdf['stopLoss'].astype(bool)
        newdf['stopCount'] = newdf['stopCount'].astype(int)
        newdf['winCount'] = newdf['winCount'].astype(int)
        newdf['stopWin'] = newdf['stopWin'].astype(bool)
        newdf['tradeVolume'] = newdf['tradeVolume'].astype(int)
        newdf['stopLong'] = newdf['stopLong'].astype(bool)
        newdf['stopShort'] = newdf['stopShort'].astype(bool)
        newdf['status'] = newdf['status'].astype(int)
        newdf['clearPos'] = newdf['clearPos'].astype(bool)
        # print newdf
        if self.symbol not in newdf.index:
            logContent = u'没有合约%s的交易配置' % self.symbol
            send_msg(logContent.encode('utf-8'))
            return
        else:
            self.__dict__ = dict(newdf.loc[self.symbol, :])
            # h = hist()
            # if h.getMode(self.symbol2hist()) == 1:
            #     self.currentMode = 'long'
            # else:
            #     self.currentMode = 'short'

    def update(self):
        a = hist()
        a.get_K_data(self.symbol2hist(), period='1d')
        self.perHigh = list(a.data['high'])[-1]
        self.perLow = list(a.data['low'])[-1]


    def symbol2hist(self):
        if self.symbol == 'RM709':
            return 'RM1709'
        elif self.symbol == 'i1709':
            return 'i1709'
        elif self.symbol == 'jm1709':
            return 'jm1709'
        elif self.symbol == 'hc1710':
            return 'hc1710'
        elif self.symbol == 'ru1709':
            return 'ru1709'
        elif self.symbol == 'zn1706':
            return 'zn1706'
        elif self.symbol == 'pp1709':
            return 'pp1709'
        elif self.symbol == 'j1709':
            return 'j1709'
        elif self.symbol == 'bu1706':
            return 'bu1706'
        elif self.symbol == 'FG709':
            return 'fg1709'
        elif self.symbol == 'jd1709':
            return 'jd1709'
        elif self.symbol == 'SR709':
            return 'SR1709'
        elif self.symbol == 'cu1707':
            return 'cu1707'
        elif self.symbol == 'rb1710':
            return 'rb1710'

if __name__ == '__main__':
    # reconfig()
    # a = tradeBar('FG709')
    # b = tradeBar('i1709')
    # c = {}
    # c[a.symbol] = a
    # c[b.symbol] = b
    # saveConfig(c)
    # a = tradeBar('FG709')
    # print a.__dict__
    a = hist()
    a.get_K_data('jd1709', period='1d')
    print a.data
    perHigh = list(a.data['high'])[-1]
    perLow = list(a.data['low'])[-1]
    print perHigh
    print perLow