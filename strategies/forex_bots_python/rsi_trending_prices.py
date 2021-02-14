import datetime
from oanda.oanda import Oanda
from indicators.indicators import Indicator
from notifier.system_logger import config_logger


class Rsi1MinTrendingPrices(Oanda):
    def __init__(self, oanda):
        print('-------- RSI 1Min Trending Prices Stratgey Initialized -----------')
        self.data0 = oanda.DataFeed.data0
        self.oanda = oanda
        self.global_logger = config_logger()
        self.pair = oanda.pair
        self.profit_target = 10
        self.loss_target = -10
        self.set_indicators()
        self.global_logger.info('-------- RSI 1Min Trending Prices Stratgey Initialized -----------')

    def set_indicators(self):
        # self.sma = Indicator().sma(self.data0, period=14, ba='bid', ohlc='c')
        self.rsi = Indicator().rsi(ohlc='close', period=14, pair=self.pair, timeframe='minute', )

    
    def log(self, txt, dt=None):
        dt = dt or self.data0[0]['time']
        # print(f'{dt} GMT {txt}')
        self.global_logger.info(f'{dt} {txt}')


    def __next__(self):
        self.set_indicators()
        self.log('\n--------------- NEXT RAN ---------------')
        self.log(f" BID Close Price: {self.data0[0]['bid']['c']}")
        self.log(f" NEW RSI: {self.rsi[0]}")

        bid0 = self.data0[0]['bid']['c']
        bid1 = self.data0[1]['bid']['c']
        bid2 = self.data0[2]['bid']['c']

        open_trades = self.oanda.Account.get_open_trades()['trades']
        matching_trades = self.oanda.Account.find_matching_trades(open_trades, self.pair)

        if len(matching_trades) == 0:  # No Existing Position. Evaluate Entry Criteria
            if self.rsi[0] < 30:
                if (bid2 >= bid1) and (bid1 >= bid0):
                    self.oanda.Account.Order.buy_market(10000, self.pair)
            if self.rsi[0] > 70:
                if (bid2 <= bid1) and (bid1 <= bid0):
                    self.oanda.Account.Order.sell_market(10000, self.pair)
        else:  # Position Exists.  Evaluate Exit Criteria.
            position_value = float(matching_trades[0]['unrealizedPL'])
            self.log(f'Checking profit : {position_value}')
            if (position_value > self.profit_target) or (position_value < self.loss_target):
                order_id = matching_trades[0]['id']
                self.oanda.Account.Order.close_trade(order_id)