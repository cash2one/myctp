# encoding: UTF-8

class config:

    tradeSymbol = ['ru1801', 'i1801']       #交易合约，菜粕
    recodeTickFlag = False        #是否记录实时行情
    tableName = 'tradeseting'
    basePath = '/home/'

    # 风控
    riskControl = False      # 是否执行风控
    rc_win = 1500           # 风控止盈金额
    rc_loss = -3000         # 风控止损金额
