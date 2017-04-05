#!/usr/bin/python
# encoding: UTF-8
import matplotlib.pyplot as plt
import pandas as pd
from datetime import *

class analysis():
    def __init__(self):
        pass

    def readData(self, filename):
        return pd.read_csv(filename, index_col=2, parse_dates=[2],na_values=0, na_filter=True, encoding='gbk').dropna(axis=0)

    def readTickData(self, filename):
        return pd.read_csv(filename, parse_dates=[1, 2],na_values=0, na_filter=True).dropna(axis=1)

if __name__ == '__main__':
    a = analysis()
    # d06 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2006.csv')
    # d07 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2007.csv')
    # d08 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2008.csv')
    # d09 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2009.csv')
    # d10 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2010.csv')
    # d11 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2011.csv')
    # d12 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2012.csv')
    # d13 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2013.csv')
    # d15 = a.readData(u'C:\\Users\\Eleven\\PycharmProjects\\myctp\\data\\豆粕2015.csv')
    # m1205 = d12[d12[u'合约'] == 'm1205']
    # m1305 = d13[d13[u'合约'] == 'm1305']
    # m1505 = d15[d15[u'合约'] == 'm1505']
    # fig = plt.figure()
    # ax = fig.add_subplot(3,1,1)
    # plt.plot(m1205[u'收盘价'], color='k')
    # plt.legend(loc='best')
    # ax = fig.add_subplot(3, 1, 2)
    # plt.plot(m1305[u'收盘价'], color='k')
    # plt.legend(loc='best')
    # ax = fig.add_subplot(3, 1, 3)
    # plt.plot(m1505[u'收盘价'], color='k')
    # plt.legend(loc='best')
    # plt.show()
    tick1 = a.readTickData('RM705-2017-03-20.csv')
    tick2 = a.readTickData('m1705-2017-03-20.csv')
    tick = pd.merge(tick1, tick2, on=['time'])
    print tick
    startTime = datetime.strptime('2017-03-20 14:35:00', '%Y-%m-%d %H:%M:%S')
    endTime = datetime.strptime('2017-03-20 14:44:00', '%Y-%m-%d %H:%M:%S')
    new = tick.loc[2000:2500,:]
    new['b-a_x'] = new['bidVolume1_x'] - new['askVolume1_x']
    print new
    fig = plt.figure()
    ax = fig.add_subplot(2,1,1)
    plt.plot(new['lastPrice_x'], color='k')
    # m.loc[:, ['bidVolume1', 'lastPrice']].plot(kind='bar')
    plt.legend(loc='best')
    ax = fig.add_subplot(2, 1, 2)
    plt.plot(new['b-a_x'], color='g')
    plt.legend(loc='best')
    plt.show()