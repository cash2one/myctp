# encoding: UTF-8

class config:

    tradeSymbol = ['ru1709', 'RM709', 'i1709', 'FG709', 'jd1709', 'SR709']       #交易合约，菜粕
    recodeTickFlag = True        #是否记录实时行情
    tableName = 'tradeseting'
    basePath = '/home/'

    # 风控
    riskControl = False     # 是否执行风控
    rc_win = 20000          # 风控止盈金额
    rc_loss = -20000        # 风控止损金额
