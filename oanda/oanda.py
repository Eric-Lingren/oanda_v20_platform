import requests
import json
import time
from notifier.sms import TwilioSMS
from notifier.system_logger import config_logger


class Oanda:
    def __init__(self, token, account, practice, pair, backfill, text_notifications, twilio_sid, twilio_token, twilio_number, recipient_number):
        self.token = token
        self.account = account
        self.practice = practice
        self.pair = pair
        self.text_notifications = text_notifications
        self.global_logger = config_logger()
        self.base_url = self.set_base_url(practice)
        self.headers = self.set_headers(token)
        self.Account = Account(self.base_url, self.headers, self.account, self.text_notifications, twilio_sid, twilio_token, twilio_number, recipient_number, self.global_logger)
        self.DataFeed = DataFeed(self.headers, self.pair, backfill, self.base_url, practice, account, self.global_logger)

    def set_base_url(self, practice):
        if practice:
            return 'https://api-fxpractice.oanda.com'
        return 'https://stream-fxtrade.oanda.com'

    def set_headers(self, token):
        return {'Authorization': 'Bearer ' + token}

    def print_details(self):
        print(f'Token: {self.token}')
        print(f'Account Number: {self.account}')
        print(f'Base Url: {self.base_url}')
        print(f'Headers: {self.headers}')




class Account(Oanda):
    def __init__(self, base_url, headers, account, text_notifications, twilio_sid, twilio_token, twilio_number, recipient_number, global_logger):
        self.global_logger = global_logger
        self.base_url = base_url
        self.account = account
        self.headers = headers
        self.account_info = self.get_account()
        self.Order = Order(self.base_url, self.headers, self.account, text_notifications, twilio_sid, twilio_token, twilio_number, recipient_number, global_logger)
    
    def get_account(self):
        try:
            url = self.base_url + '/v3/accounts/' + self.account
            r = requests.get(url, headers=self.headers)
            data = r.json()
            if data['errorMessage']:
                self.global_logger.error(f"OANDA API ERROR - {data['errorMessage']}")
            return data
        except:
            pass

    def get_account_balance(self):
        data = self.get_account()
        balance = data['account']['balance']
        return balance

    def get_open_positions(self):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/openPositions'
            r = requests.get(url, headers=self.headers)
            data = r.json()
            if data['errorMessage']:
                self.global_logger.error(f"OANDA API ERROR - {data['errorMessage']}")
            return data
        except:
            pass

    def get_open_trades(self):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/openTrades'
            r = requests.get(url, headers=self.headers)
            data = r.json()
            # if data['errorMessage']:
            #     print('error')
            #     self.global_logger.error(f"OANDA API ERROR - {data['errorMessage']}")
            return data
        except:
            pass

    def find_matching_trades(self, open_trades, pair):
        new_list = []
        for item in open_trades:
            if item['instrument'] == pair:
                new_list.append(item)
        sorted_list = sorted(new_list, key = lambda i: i['id'])
        return sorted_list




class Order(Account):
    def __init__(self, base_url, headers, account, text_notifications, twilio_sid, twilio_token, twilio_number, recipient_number, global_logger):
        self.base_url = base_url
        self.account = account
        self.headers = headers
        self.text_notifications = text_notifications
        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token
        self.twilio_number = twilio_number
        self.recipient_number = recipient_number
        self.order = None
        self.global_logger = global_logger

    def get_orders(self):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/orders'
            r = requests.get(url, headers=self.headers)
            data = r.json()
            return data
        except:
            pass

    def get_pending_orders(self):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/pendingOrders'
            r = requests.get(url, headers=self.headers)
            data = r.json()
            return data
        except: 
            pass

    def buy_market(self, units, instrument):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/orders'
            data = {
                "order": {
                    "units": units,
                    "instrument": instrument,
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
            r = requests.post(url, headers=self.headers, json=data)
            self.notify_order(r.json())
        except:
            pass

    def sell_market(self, units, instrument):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/orders'
            data = {
                "order": {
                    "units": -units,
                    "instrument": instrument,
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
            r = requests.post(url, headers=self.headers, json=data)
            self.notify_order(r.json())
        except:
            pass

    def notify_order(self, order):
        self.order = order
        if 'orderCancelTransaction' in order:
            print('Order Transaction Canceled:')
            msg = f"{order['orderCancelTransaction']['type']}, {order['orderCancelTransaction']['reason']}"
            print(msg)
            if self.text_notifications:
                TwilioSMS(self.twilio_sid, self.twilio_token, self.twilio_number, self.recipient_number).send_text(msg)
            self.global_logger.error(f"OANDA ORDER ERROR - {msg}")
        print('\n')
        if 'orderFillTransaction' in order:
            time = order["orderFillTransaction"]["time"]
            orderID = order["orderFillTransaction"]["orderID"]
            instrument = order["orderFillTransaction"]["instrument"]
            units = order["orderFillTransaction"]["units"]
            price = order["orderFillTransaction"]["price"]
            reason = order["orderFillTransaction"]["reason"]
            pl = order["orderFillTransaction"]["pl"]
            msg = f'*** ORDER FUFILLED ***\nTime: {time}\nType: {reason}\nOrder Id: {orderID}\nInstrument: {instrument}\nUnits: {units}\nPrice: {price}\nP/L: ${pl}'
            print(msg)
            if self.text_notifications:
                TwilioSMS(self.twilio_sid, self.twilio_token, self.twilio_number, self.recipient_number).send_text(msg)
            self.global_logger.info(f"OANDA ORDER SUCCESSFUL - {msg}")


    def close_trade(self, order_id):
        try:
            url = self.base_url + '/v3/accounts/' + self.account + '/trades/' + order_id + '/close'
            r = requests.put(url, headers=self.headers)
            self.notify_order(r.json())
        except:
            pass



class DataFeed(Oanda):
    def __init__(self, headers, pair, backfill, base_url, practice, account, global_logger):
        self.headers = headers
        self.pair = pair
        self.base_url = base_url
        self.account = account
        # self.global_logger = global_logger
        self.data0 = self.set_init_data0(backfill)
        self.stream_url = self.set_stream_url(practice)
    
    def set_init_data0(self, backfill):
        try:
            params = { 'granularity': 'M1', 'count': 1, 'price' : 'BA' }
            if backfill:
                params['count'] = 500
            url = self.base_url + '/v3/instruments/' + self.pair + '/candles?'
            r = requests.get(url, headers=self.headers, params=params)
            data = r.json()
            # if data['errorMessage']:
            #     self.global_logger.error(f"OANDA DATA ERROR - {data['errorMessage']}")
            bars = data['candles'][::-1]
            return bars
        except:
            pass

    def rebuild_data(self, latest_bar):
        latest_bar_time = latest_bar['time']
        last_bar_time = self.data0[0]['time']
        if latest_bar_time != last_bar_time:
            self.data0.insert(0, latest_bar)
            if len(self.data0) > 500 :  # Only keeps the last 500 bars in memory
                self.data0.pop()

    def refresh_data(self):
        try:
            url = self.base_url + '/v3/instruments/' + self.pair + '/candles?count=1&price=BA'
            params = { 'granularity': 'M1' }
            r = requests.get(url, headers=self.headers, params=params)
            data = r.json()
            # if data['errorMessage']:
            #         self.global_logger.error(f"OANDA DATA ERROR - {data['errorMessage']}")
            latest_bar = data['candles'][::-1][0]
            self.rebuild_data(latest_bar)
        except:
            pass
    
    def set_stream_url(self, practice): # Does Work, Not currently used.
        if practice:
            return 'https://stream-fxpractice.oanda.com/v3/accounts/' + self.account + "/pricing/stream"
        return 'https://stream-fxtrade.oanda.com/v3/accounts/' + self.account + "/pricing/stream"

    def connect_to_stream(self): # Does Work, Not currently used.
        try:
            s = requests.Session()
            params = {'instruments' : self.pair}
            req = requests.Request('GET', self.stream_url, headers = self.headers, params = params)
            pre = req.prepare()
            resp = s.send(pre, stream = True, verify = True)
            return resp
        except Exception as e:
            s.close()
            print("Caught exception when connecting to stream\n" + str(e)) 

    def stream(self):  # Does Work, Not currently used.
        response = self.connect_to_stream()
        print(response.status_code)
        if response.status_code != 200:
            return
        for line in response.iter_lines(1):
            if line:
                try:
                    line = line.decode('utf-8')
                    msg = json.loads(line)
                except Exception as e:
                    print("Caught exception when converting message into json\n" + str(e))
                    return
                if "instrument" in msg or "tick" in msg:
                    print('\n' + line)