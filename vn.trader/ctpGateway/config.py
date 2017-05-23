# encoding: UTF-8

class config:

    tradeSymbol = ['ru1709', 'RM709', 'i1709', 'FG709', 'jd1709', 'SR709']       #交易合约，菜粕
    recodeTickFlag = True        #是否记录实时行情
    tableName = 'tradeseting_doing'
    basePath = '/work/'

    # 风控
    riskControl = True      # 是否执行风控
    rc_win = 6000          # 风控止盈金额
    rc_loss = -8000        # 风控止损金额
