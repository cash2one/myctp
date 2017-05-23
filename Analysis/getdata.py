#!/usr/bin/python
# encoding: UTF-8
import urllib,json
import pandas as pd
import numpy as np


class hist():
    def __init__(self):
        self.data = None

    def get_K_data(self, symbol, period='1d'):
        if period == '1d':
            url = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=%s' % symbol
            fp = urllib.urlopen(url)
            jsonData = json.loads(fp.read())
            self.data = pd.DataFrame(jsonData, columns=['date', 'open', 'high', 'low', 'close', 'volume'], dtype=float)
        elif period == '5m' or period == '15m' or period == '30m' or period == '60m':
            url = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine%s?symbol=%s' % (period, symbol)
            fp = urllib.urlopen(url)
            jsonData = json.loads(fp.read())
            jsonData.reverse()
            self.data = pd.DataFrame(jsonData, columns=['date', 'open', 'high', 'low', 'close', 'volume'], dtype=float)
        else:
            pass

    def get_ma(self, maList):
        for ma in maList:
            self.data['ma' + str(ma)] = self.data['close'].rolling(window=ma,center=False).mean()

    def get_ema(self, maList):
        for ma in maList:
            self.data['ema' + str(ma)] = self.data['close'].ewm(ignore_na=False,span=ma,min_periods=0,adjust=True).mean()

    def get_adx(self, n=14, m=6):

        df = self.data.copy()

        # 计算HD和LD值
        df['hd'] = df['high'] - df['high'].shift(1)
        df['ld'] = df['low'].shift(1) - df['low']

        # 计算TR值
        df['t1'] = df['high'] - df['low']
        df['t2'] = abs(df['high'] - df['close'].shift(1))
        df.ix[df['t1'] >= df['t2'], 'temp1'] = df['t1']
        df.ix[df['t1'] < df['t2'], 'temp1'] = df['t2']

        df['temp2'] = abs(df['low'] - df['close'].shift(1))

        df.ix[df['temp1'] >= df['temp2'], 'temp'] = df['temp1']
        df.ix[df['temp1'] < df['temp2'], 'temp'] = df['temp2']

        df.dropna(inplace=True)

        df['tr'] = df['temp'].rolling(window=n,center=False).sum()

        df.ix[(df['hd'] > 0) & (df['hd'] > df['ld']), 'hd1'] = df['hd']
        df['hd1'].fillna(0, inplace=True)

        df.ix[(df['ld'] > 0) & (df['ld'] > df['hd']), 'ld1'] = df['ld']
        df['ld1'].fillna(0, inplace=True)

        df['dmp'] = df['hd1'].rolling(window=n,center=False).sum()
        df['dmm'] = df['ld1'].rolling(window=n,center=False).sum()

        df['pdi'] = df['dmp'] / df['tr'] * 100
        df['mdi'] = df['dmm'] / df['tr'] * 100
        df['adx'] = (abs(df['mdi'] - df['pdi']) / (df['mdi'] + df['pdi']) *  100).rolling(window=m,center=False).mean()

        self.data['pdi'] = df['pdi'].copy()
        self.data['mdi'] = df['mdi'].copy()
        self.data['adx'] = df['adx'].copy()

    def get_macd(self, s=12, l=26, m=9):
        ema12 = self.data['close'].ewm(ignore_na=False, span=s, min_periods=0, adjust=True).mean()
        ema26 = self.data['close'].ewm(ignore_na=False, span=l, min_periods=0, adjust=True).mean()
        self.data['diff'] = ema12 - ema26
        self.data['dea'] = self.data['diff'].ewm(ignore_na=False, span=m, min_periods=0, adjust=True).mean()
        self.data['macd'] = (self.data['diff'] - self.data['dea']) * 2

    def getMode(self, symbol):
        self.get_K_data(symbol)
        self.get_macd()
        print self.data
        self.data.ix[self.data['macd'] >= self.data['macd'].shift(1), 'mode'] = 1
        self.data.ix[self.data['macd'] < self.data['macd'].shift(1), 'mode'] = 0
        print self.data
        return list(self.data['mode'])[-1]



def p1():
    a = hist()
    a.get_K_data('RM0', period='1d')
    a.get_macd()
    a.data.ix[a.data['macd'].shift(1) > a.data['macd'].shift(2), 'mode'] = 1
    a.data.ix[a.data['macd'].shift(1) < a.data['macd'].shift(2), 'mode'] = 0

    a.data.ix[(a.data['mode'] == 1) & ((a.data['open'] - a.data['low']) > 25), 'good'] = 1
    a.data.ix[(a.data['mode'] == 0) & ((a.data['high'] - a.data['open']) > 25), 'good'] = 1

    a.data.ix[(a.data['mode'] == 1) & ((a.data['high'] - a.data['open']) > 20), 'good'] = 1
    a.data.ix[(a.data['mode'] == 0) & ((a.data['open'] - a.data['low']) > 20), 'good'] = 1
    a.data['good'].fillna(0, inplace=True)
    print a.data
    print a.data['good'].sum()

def p2(symbol):
    """计算平均涨跌幅度"""
    a = hist()
    a.get_K_data(symbol, period='1d')
    a.data.ix[a.data['open'] == 0, 'open'] = np.nan
    a.data.dropna(inplace=True)
    a.data['h-l'] = abs(a.data['open'] - a.data['close']) / a.data['open']
    # print a.data
    return a.data['h-l'].mean(),a.data['volume'].mean()



if __name__ == '__main__':
    symbol = ['A0', 'B0', 'M0', 'Y0', 'C0', 'P0', 'V0', 'L0', 'PP0', 'J0', 'JM0', 'I0', 'JD0', 'BB0','FB0',
              'WH0', 'PM0', 'RI0', 'JR0', 'CF0', 'SR0', 'OI0', 'RS0', 'RM0', 'PTA0', 'ME0', 'FG0', 'TC0', 'LR0',
              'SM0', 'SF0', 'CU0', 'AL0', 'ZN0', 'PB0', 'AU0', 'AG0', 'RB0', 'WR0', 'HC0', 'RU0', 'FU0', 'BU0']
    a = hist()
    a.get_K_data('RM1705', period='1d')
    print a.data.loc[200:210,:]
    a.get_macd()
    a.data.ix[(a.data['open'] > a.data['close']), 'fan'] = a.data['high'] - a.data['open']
    a.data.ix[(a.data['open'] < a.data['close']), 'fan'] = a.data['open'] - a.data['low']
    a.data.ix[(a.data['fan'] >= 5), 'win'] = 1

    # a.data.ix[a.data['direction'] == u'多', 'win'] = a.data['close'] - a.data['open']
    # a.data.ix[a.data['direction'] == u'空', 'win'] = a.data['open'] - a.data['close']
    # a.data['win'] = abs(a.data['open'] - a.data['close']) - 200
    # a.data.ix[a.data['win'] < -150 , 'win'] = -150

    # a.data.ix[a.data['mode'] == 1, 'bad'] = (a.data['open'] - a.data['low'])/5
    # a.data.ix[a.data['mode'] == 0, 'bad'] = (a.data['high'] - a.data['open'])/5
    a.data['win'].fillna(0, inplace=True)
    print a.data
    print a.data['win'].sum()
    print a.data['win'].sum()/a.data['win'].count()
