# encoding: UTF-8

class config:

    tradeSymbol = ['ru1709', 'RM709', 'i1709', 'FG709', 'jd1709', 'SR709', 'p1709', 'c1709', 'pp1709',
                   'cu1707', 'zn1707', 'rb1710', 'bu1709', 'SM709']       #交易合约，菜粕
    recodeTickFlag = True        #是否记录实时行情
    tableName = 'tradesetingGap'
    CTP_configPath = '/work/myctp/vn.trader/ctpGateway/CTP_connect.json'
    TRADE_configPath = '/work/myctp/vn.trader/ctpGateway/TRADE_setting.json'
    BALANCE_file = '/work/myctp/vn.trader/ctpGateway/balance.csv'
