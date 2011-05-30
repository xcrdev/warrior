'''
Created on May 30, 2011

@author: xavier
'''
import sys
sys.path.append("/Library/Python/2.6/site-packages")
sys.path.append("/Library/Python/2.6/site-packages/python-twitter-0.6")
sys.path.append("/Library/Python/2.6/site-packages/pygooglechart-0.2.1")

import httplib
import socket
from BeautifulSoup import BeautifulSoup
import urllib2
import time
from pygooglechart import SimpleLineChart
import twitter
import re
from decimal import *
import os
import datetime
from datetime import date #, datetime
from collections import deque
import threading
import profile
import numpy
import random
import httplib2
import decimal
import matplotlib.pyplot as plt

httplib.HTTPConnection.debuglevel = 1
api = twitter.Api(username="greenbot01", password="fly83nne")
lastXmt = time.time() # first twitter post won't be until x minutes

#stock_list = ["GOOG", "SPY", "EEM", "GLD", "TLT", "BIDU", "MSFT", "AAPL"]
stock_list = ["GOOG", "SPY", "EEM", "GLD", "TLT", "BIDU", "MSFT", "AAPL"]
stock_data = {}
trend_points = 12
current_stock = ""
current_m = 0
buy = []
sell = []
state = "none held"
workingStock = None
decisionLog = []
clock = 0
shortMA = {}
lastAverageSMA = 0
longMA = {}
lastAverageLMA = 0
flag_counter = {}
derivative = {}
stdDev = []
lastMarketState = None
currentMarketState = None

def init():
    for stock in stock_list:
        stock_data[stock] = []
        shortMA[stock] = [0,0]
        longMA[stock] = [0,0]
        flag_counter[stock] = 0
        derivative[stock]= []

def PostUpdate(msg):
    # ADD CODE to test that msg is a string
    try:
        status = api.PostUpdate(msg)
    except urllib2.HTTPError as e:
        print type(e)
        print e.code
    except urllib2.URLError as e:
        print type(e)
        print e.reason
    except httplib.BadStatusLine, msg:
        print 'BadStatusLine Error !'
        print msg.line

def ratelimit(msg):
    global lastXmt
    if (time.time() - lastXmt) > (4 * 60):
        PostUpdate(msg)
        lastXmt = time.time()

def errorLog(msg):
    print msg
    #if len(msg) <= 140: 
    PostUpdate(msg)
    #else:
    #ADD CODE to strip message down
    #pass

def realtime(stock):
    conn = httplib.HTTPConnection("streamerapi.finance.yahoo.com", timeout=2)
    conn.request("GET","/streamer/1.0?s=" + stock + "&k=c10,c60,l10,l90,p20,p40,t10,t50&j=c10,l10,p20,t10&r=0&marketid=us_market&callback=parent.yfs_u1f&mktmcb=parent.yfs_mktmcb&gencallback=parent.yfs_gencb")
    r1 = conn.getresponse()
    print r1.status, r1.reason
    data = ""
    while 1:
        try:
            data = data + r1.read(1)
        except socket.timeout as e:
            if data != "":
                ##print type(e)
                scriptList = BeautifulSoup(data).findAll('script')
                for script in scriptList:
                    print script
                    ratelimit(script)  
                data = ""
        except httplib.HTTPException as e:
                print type(e)
                conn = httplib.HTTPConnection("streamerapi.finance.yahoo.com", timeout=5)
                conn.request("GET","/streamer/1.0?s=" + stock + "&k=c10,c60,l10,l90,p20,p40,t10,t50&j=c10,l10,p20,t10&r=0&marketid=us_market&callback=parent.yfs_u1f&mktmcb=parent.yfs_mktmcb&gencallback=parent.yfs_gencb")
                r1 = conn.getresponse()
                print r1.status, r1.reason
                data = ""
        except Exception as e:
                print type(e)
def zacks(stock):
    conn = httplib.HTTPConnection("wwww.zacks.com", timeout=5)
    head = {"Accept-Encoding" : "gzip,deflate", "Accept-Charset" : "UTF-8,*"} 
    conn.request("GET", "/research/report.php?type=estimates&t=" + stock, headers = head)
    r1 = conn.getresponse()
    print r1.status, r1.reason
    data = ""
    while 1:
        try:
            data = data + r1.read(1)
        except socket.timeout as e:
            if data != "":
                scriptList = BeautifulSoup(data).findAll('tr')
                for script in scriptList:
                    print script
            data = ""
## market state
## file io

class MarketState:
    def __init__(self):
        self.current_market_state = ""
        self.last_market_state = ""

    def periodic(self):
        self.last_market_state = self.current_market_state
        if self.ismarketopen():
            self.current_market_state = "open"
        else:
            self.current_market_state = "close"

    def market_just_opened(self):
        if self.last_market_state == "close" and self.current_market_state == "open":
            return True
        else:
            return False

    def market_just_closed(self):
        if self.last_market_state == "open" and self.current_market_state == "close":
            return True
        else:
            return False

    def istradingday(self, date):
        holidays = [datetime.date(2010,1,1),
                    datetime.date(2010,1,18),
                    datetime.date(2010,2,15),
                    datetime.date(2010,4,2),
                    datetime.date(2010,5,31),
                    datetime.date(2010,7,5),
                    datetime.date(2010, 9,6),
                    datetime.date(2010,11,25),
    # early market close datetime.date(2010,11,26), 
                    datetime.date(2010,12,24)]
        current_date = date # year month day hour minute second\
        # if the day is a weekday
        if current_date.weekday() < 5: 
            if current_date not in holidays:
                return True
        return False

    def ismarketopen(self):
        if self.istradingday(datetime.datetime.now()):
            current_date = datetime.datetime.now() # year month day hour minute second
            hour = current_date.hour
            minute = current_date.minute
            if (hour == 8 and minute >= 30) or (hour == 15 and minute == 00) or (hour > 8 and hour < 15): # convert this to utc or gmt
                return True
        return False

def file_line_count(file_handle):
    count = 0
    while file_handle.readline():
        count = count + 1
    return count

class MarketDatabase():
    def __init__(self, stock_list =   ['GOOG', #Google
                                       'MSFT', #Microsoft
                                       'AAPL', #Apple
                                       'IBM',  #IBM
                                       'AMZN', #Amazon
                                       'UPS',  #UPS
                                       'TM',   #Toyota
                                       'NFLX', #Netflix
                                       'VRSN', #Verisign
                                       'MSI',  #Motorola
                                       'CSCO', #Cisco
                                       'VZ',   #Verizon
                                       'T',    #AT&T
                                       'TSLA', #Tesla
                                       'BRK.B',#Berkshire Hathaway
                                       'JPM',  #JP Morgan
                                       'BAC',  #Bank of America
                                       'C',    #Citigroup
                                       'WFC',  #Wells Fargo
                                       'MS',   #Morgan Stanley
                                       'PIR',  #Pier 1 Imports
                                       'TLT',  #iShares 20 yr bond
                                       'IEF',  #iShares 7-10 yr bond
                                       'SHY',  #iShares 1-3 yr bond
                                       'VWO',  #Vanguard Emerging Markets
                                       'GLD',  #Gold ETF
                                       'GE',   #General Electric
                                       'AXP',  #American Express
                                       'DOW',  #Dow Chemical
                                       'BIDU', #Baidu
                                       'TROW', #T. Rowe Price Group
                                       'FSLR', #First Solar
                                       'M',    #Macy's
                                       'WHR',  #Whirlpool
                                       'EXPE', #Expedia
                                       'AMD',  #AMD
                                       'ATI',  #ATI
                                       'LYG',  #Lloyds Banking Group
                                       'DB',   #Deutsche Bank
                                       'BP',   #BP
                                       'GS',   #Goldman Sachs
                                       'BCS',  #Barclays
                                       'WLP',  #WellPoint
                                       'SPY',  #S&P500 ETF
                                       'ADM',  #Archer Daniels Midland
                                       'GIS',  #General Mills
                                       'QCOM', #QCOM
                                       'INTC', #Intel
                                       'ARMH', #ARM
                                       'DDS',  #Dillards
                                       'F',    #Ford
                                       'ERJ',  #Embraer
                                       'NVDA', #Nvidia
                                       'GRMN', #Garmin
                                       'RHT',  #Redhat
                                       '.DJI', #Dow Jones Index
                                       '.INX', #S&P 500 Index
                                       'AIG',  #AIG
                                       'MGM',  #MGM
                                       'TSL',  #Trina Solar
                                       'ODP',  #Office Depot
                                       'OMX',  #OfficeMax
                                       'AKS',  #AK Steel Holding Company
                                       'WMG',  #Warner Music Group
                                       'GT',   #Goodyear Tire
                                       'OSK',  #Oshkosh
                                       'HOG',  #Harley Davidson
                                       'ETFC', #E Trade
                                       'DV',   #DeVry
                                       'APOL', #Apollo Group
                                       'COCO', #Corinthian Colleges
                                       'HPQ',  #HPQ
                                    
                                      ]):
        self.path = '/Users/xavier/Documents/db/'
        self.market_state = MarketState()
        self.file_handles = {}
        self.stock_list = stock_list

    def _file_open(self):
        date = datetime.datetime.now()
        for stock in self.stock_list:
            dir_path = self.path + stock + '/'
            file_name = str(date.year) + '_' + "%02d" % (date.month) + '_' + "%02d" % (date.day) + '.txt'
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            self.file_handles[stock]= open(dir_path + file_name, 'a') 

    def _file_close(self):
        if self.file_handles:
            for stock in self.stock_list:
                self.file_handles[stock].close()
            self.file_handles = {}

    def write(self, stock, data):
        line = str(data[stock]["time"]) + "\t" + str(data[stock]["price"])
        #print self.file_handles[self.stock]
        self.file_handles[stock].write(line)
        self.file_handles[stock].write('\n')
        self.file_handles[stock].flush()

    def _get_path_str(self, stock, date):
        dir_path = self.path + stock + '/'
        file_name = str(date.year) + '_' + "%02d" % (date.month) + '_' + "%02d" % (date.day) + '.txt'
        return dir_path+file_name

    def read(self, stock, start_date, end_date):
        results = {}
        results[stock] = {"time" : [], "price" : []}
        
        for day in range(0, (end_date-start_date).days+1):

            date = start_date+datetime.timedelta(days=day)
        
            file_path = self._get_path_str(stock, date)
            if os.path.isfile(file_path):
                file_handle= open(file_path, 'r')
                while 1:
                    line = file_handle.readline()
                    if not line:
                        file_handle.close()
                        break
                    else:
                        data = self._convert(stock, line)
                        results[stock]["time"].append(data[stock]["time"])
                        results[stock]["price"].append(data[stock]["price"])
        return results

    def _convert(self, stock, line):
        # convert between string and stock data struct
        time,price = line.split("\t")
        time = float(time)
        price = float(price)
        data = {stock:{'time':time,'price':price}}
        return data

    def read_all(self, start_date, end_date):
        results = []
        path = {}
        file_handle_dict = {}
        line_dict = {}
        data_dict = {}

        for day in range(0, (end_date-start_date).days+1):

            date = start_date+datetime.timedelta(days=day)
            for stock in self.stock_list:
                file_path = self._get_path_str(stock,date)
                if os.path.isfile(file_path):    
                    file_handle_dict[stock] = open(file_path, 'r')
                    
                    line_dict[stock] = file_handle_dict[stock].readline()
                    if line_dict[stock]:
                        data_dict[stock] = self._convert(stock, line_dict[stock])[stock]
                    else:
                        file_handle_dict[stock].close()
                        del line_dict[stock]

            #print line_dict

            while line_dict:
                min_time = 2000000000
                for stock in line_dict.keys():
                    if data_dict[stock]['time'] < min_time:
                        min_time = data_dict[stock]['time']
                        min_stock = stock
                results.append({min_stock:data_dict[min_stock]})
                #print {min_stock:data_dict[min_stock]}
                line_dict[min_stock] = file_handle_dict[min_stock].readline()
                if line_dict[min_stock]:
                    data_dict[min_stock] = self._convert(min_stock, line_dict[min_stock])[min_stock]
                else:
                    file_handle_dict[min_stock].close()
                    del line_dict[min_stock]
        return results
    
    def periodic(self):
        self.market_state.periodic()
        if self.market_state.market_just_opened():
            self._file_open()     
        elif self.market_state.market_just_closed():
            self._file_close()        
        #open
        #close

    def _get_file_handle(self, stock, date):
        file_path = self._get_path_str(stock,date)
        file_handle = None
        if os.path.isfile(file_path):
            file_handle= open(file_path, 'r')
        return file_handle

    def get_data_points(self, stock, date):
        count = 0
        f = self._get_file_handle(stock, date)
        if f:
            while f.readline():
                count = count + 1
            f.close()
        return count
        
        

    
class LRUv2:
    def __init__(self, host, get):
        self.HOST = host
        self.get = get
        self.db = MarketDatabase()
        self.stock_list = self.db.stock_list
        stock_str = ",".join(self.stock_list)
        self.request = ("http://" + self.HOST + self.get) % stock_str
        self.h = httplib2.Http(".cache", timeout = 15.0)
        #print self.request

    def send(self):
        #print 'send'
        try:
            resp, data = self.h.request(self.request,"GET", headers={'Accept-Encoding' : 'gzip,deflate,sdch'})
            #print resp
            return resp, data
        except socket.gaierror as e:
            print type(e)
            return None, ""
        except httplib2.ServerNotFoundError as e:
            print type(e)
            return None, ""
        except socket.timeout as e:
            print type(e)
            return None, ""
        except socket.error as e:
            errno, errstr = sys.exc_info()[:2]
            print type(e), errno, errstr

    def recv(self, n_bytes):
        return self.s.recv(n_bytes)

    def register_recv(self, recv_override):
        self.recv = recv_override       

    def _parse(self, data, time_stamp):
        print data
        return None

    def new_data_callback(self, data):
        print data
        if self.db.file_handles:
            self.db.write(self.stock, data)

    def main(self):
        data = ""
        recvTime = time.time()
        parsed_data = None
        valid_data = {}
        last_valid_data = {}
        for stock in self.stock_list:
            valid_data[stock] = {}
            last_valid_data[stock] = {}
        market_state = MarketState()
        resp, data = self.send()
        while 1:
            
            self.db.periodic()
            if resp and resp.status == 200:
                if data != "":
                    #print 'reply'
                    #print data
                    recvTime = time.time()
                    parsed_list = self._parse(data, recvTime)
                    #print parsed_list
                    if parsed_list:   
                        for stock_dict in parsed_list:
                            stock = stock_dict.keys()[0]
                            valid_data[stock] = stock_dict[stock]
                            if last_valid_data[stock] == {} or \
                               (valid_data[stock]["price"] != \
                                last_valid_data[stock]["price"]):
                                self.new_data_callback({stock : valid_data[stock]})
                                last_valid_data[stock] = valid_data[stock]
                    data = ""
                    resp, data = self.send()
                    #print 'sending request'
                #add an else column for other responses besides 200
                #consider not sending requests during non market hours
            else:
                print 'no reply'
                resp, data = self.send()
            time.sleep(1.0)

    
class LRU:
    def __init__(self, host, get, poll_stock_data):
        self.HOST = host
        self.PORT = 80
        self.s = None
        self.get = get
        self.poll_stock_data = poll_stock_data
        self.stock_list = ['GOOG', 'MSFT', 'AAPL', 'TSLA', 'PIR', 'TLT', 'IEF', 'SHY', 'VWO', 'GLD', 'GE', 'AXP']#, 'DOW', 'BIDU', 'TROW', 'FSLR', 'M', 'WHR', 'EXPE', 'AMD', 'ATI', 'LYG', 'DB']
        self.db = MarketDatabase(self.stock_list)
    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)
        self.s.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
        try:
            self.s.connect((self.HOST,self.PORT))
        except socket.gaierror as e:
            print type(e)
            self.s = None
        except socket.timeout as e:
            print type(e)
            self.s = None
    def send(self):
        stock_str = ",".join(self.stock_list)
        self.s.send(self.get % (stock_str))

    def recv(self, n_bytes):
        return self.s.recv(n_bytes)

    def register_recv(self, recv_override):
        self.recv = recv_override       

    def _parse(self, data, time_stamp):
        print data
        return None

    def new_data_callback(self, data):
        print data
        if self.db.file_handles:
            self.db.write(self.stock, data)

    def main(self):
        data = ""
        recvTime = time.time()
        parsed_data = None
        valid_data = {}
        last_valid_data = {}
        for stock in self.stock_list:
            valid_data[stock] = {}
            last_valid_data[stock] = {}
        market_state = MarketState()
        while 1:
            try:
                if self.s:
                    data = data + self.s.recv(1)  ## eventuall change this to recv()
                else:
                    self.connect()
                    if self.s:
                        self.send()
            except socket.timeout as e:

                self.db.periodic()
                
                if self.poll_stock_data:
                    if data != "":
                        recvTime = time.time()
                        parsed_list = self._parse(data, recvTime)
                        #print parsed_list
                        if parsed_list:   
                            for stock_dict in parsed_list:
                                stock = stock_dict.keys()[0]
                                valid_data[stock] = stock_dict[stock]
                                if last_valid_data[stock] == {} or \
                                   (valid_data[stock]["price"] != \
                                    last_valid_data[stock]["price"]):
                                    self.new_data_callback({stock : valid_data[stock]})
                                    last_valid_data[stock] = valid_data[stock]
                        self.send() # add timeout
                    data = ""
                    
                else:
                    if data != "":
                        recvTime = time.time()
                        parsed_data = self._parse(data, recvTime)
                        if parsed_data:
                            self.new_data_callback(parsed_data)
                        data = ""
                    elif time.time() - recvTime > 6 * 60:
                        errorLog("did not receive data from server in 6 minutes, reconnecting")
                        self.s.close()
                        self.s = None
            except socket.error as e:
                errno, errstr = sys.exc_info()[:2]
                errorLog(str(errno))
                errorLog(str(type(errstr)))
                errorLog(str(errstr))
                errorLog(str(time.time()) + ", reconnecting")
                self.s.close()
                self.s = None

class Yahoo(LRU):
    def __init__(self, poll_stock_data, ident):
        self.id = ident
        host = "streamerapi.finance.yahoo.com"
        get = 'GET /streamer/1.0?s=%s&k=l10&callback=parent.yfs_u1f&mktmcb=parent.yfs_mktmcb&gencallback=parent.yfs_gencb HTTP/1.1\r\nHost: streamerapi.finance.yahoo.com\r\nAccept-Encoding: identity\r\n\r\n'
        LRU.__init__(self, host, get, poll_stock_data)

##    def send(self,stock_list):
##        stock_str = ",".join(stock_list)
##        self.s.send(self.get % (stock))

    def _parse(self, data, time_stamp):
        yahoo_dict = {}
        my_dict = {}
        l10 = "price"
        pattern = "(?<=\(){.+}(?=\))"
        scriptList = BeautifulSoup(data).findAll('script')
        for script in scriptList:
            match = re.search(pattern, script.string)
            if match: # don't forget to eliminate the document header
                try:
                    yahoo_dict = eval(match.group())
                except Exception as e:
                    print type(e)
                    print match.group()
                    return None 
                if len(yahoo_dict.keys()) == 1:
                    key = yahoo_dict.keys()[0]
                    if not key == "unixtime":
                        stock = key
                        if yahoo_dict[stock].has_key(l10):
                            my_dict[stock] = {"time" : time_stamp, "price" : float(yahoo_dict[stock][l10])}
                            return my_dict
                        else:
                            return None
                    else:
                        return None
                else:
                    return None
        return None


class Google(LRUv2):
    def __init__(self, ident):
        self.id = ident
        host = "finance.google.com"
        #get = 'GET /finance/info?client=ig&q=NASDAQ:%s HTTP/1.1\r\nHost: finance.google.com\r\nAccept-Encoding: gzip,deflate,sdch\r\n\r\n'
        get = '/finance/info?client=ig&q=NASDAQ:%s'
        poll_stock_data = True
        LRUv2.__init__(self, host, get)
        #self.strategy = Strategy(self.stock_list, self.db)

    def _parse(self, data, time_stamp):
        google_list = []
        stock_dict = {}
        my_list = []
        pattern = "\[.+\]"
        prog = re.compile(pattern, re.DOTALL)
        match = prog.search(data)
        if match:
            #print match.group()
            try:
                google_list = eval(match.group())
                #print google_list
            except Exception as e:
                print type(e)
                print match.group() 
                return my_list
            for stock_dict in google_list:
                if stock_dict.has_key("t") and stock_dict.has_key("l"):
                    try:
                        my_list.append({stock_dict["t"] : {"time" : time_stamp, "price" : float(stock_dict["l"].replace(",", ""))}})
                    except ValueError as e:
                        print stock_dict['t']
                        print stock_dict['l']
                else:
                    pass
                    # log failure
        return my_list

    def new_data_callback(self, data):
        print data
        stock = data.keys()[0]
        if self.db.file_handles:
            if self.db.file_handles[stock]:
                self.db.write(stock, data)
        #self.strategy.buy_low_sell_high(data, stock)
        

class MSN(LRU):
    def __init__(self,ident):
        self.id = ident
        host = "moneycentral.msn.com"
        get = 'POST /inc/services/streamingquotes.ashx?symbol=%s HTTP/1.1\r\nHost: moneycentral.msn.com\r\nConnection: keep-alive\r\nUser-Agent: Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_0; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.55 Safari/533.4\r\nReferer: http://moneycentral.msn.com/detail/stock_quote?symbol=goog\r\nContent-Length: 3\r\nOrigin: http://moneycentral.msn.com\r\nX-Mny-SQT: 1\r\nContent-type: application/x-www-form-urlencoded\r\nAccept: */*\r\nAccept-Encoding: gzip,deflate,sdch\r\n\r\nn=0'
        poll_stock_data = True
        LRU.__init__(self, host, get, poll_stock_data)
        

class GoogleThread(threading.Thread):
    def run(self):
        x = Google("google")
        x.main()

class YahooPollThread(threading.Thread):
    def run(self):
        x = Yahoo(True, "yahoo_poll")
        x.main()

class YahooPushThread(threading.Thread):
    def run(self):
        x = Yahoo(False, "yahoo_push")
        x.main()

class StrategyThread(threading.Thread):
    def run(self):
        #stock_list = ['GOOG']
        stock_list = stock_list =   [#'GOOG', #Google
##                                       'MSFT', #Microsoft
##                                       'AAPL', #Apple
##                                       'IBM',  #IBM
                                       'AMZN', #Amazon
##                                       'UPS',  #UPS
##                                       'TM',   #Toyota
                                       'NFLX', #Netflix
##                                       'VRSN', #Verisign
##                                       'MOT',  #Motorola
##                                       'CSCO', #Cisco
##                                       'VZ',   #Verizon
##                                       'T',    #AT&T
                                       'TSLA'#, #Tesla
##                                       'BRK.B',#Berkshire Hathaway
##                                       'JPM',  #JP Morgan
##                                       'BAC',  #Bank of America
##                                       'C',    #Citigroup
##                                       'WFC',  #Wells Fargo
##                                       'MS',   #Morgan Stanley
##                                       'PIR',  #Pier 1 Imports
##                                       'TLT',  #iShares 20 yr bond
##                                       'IEF',  #iShares 7-10 yr bond
##                                       'SHY',  #iShares 1-3 yr bond
##                                       'VWO',  #Vanguard Emerging Markets
##                                       'GLD',  #Gold ETF
##                                       'GE',   #General Electric
##                                       'AXP',  #American Express
##                                       'DOW',  #Dow Chemical
##                                       'BIDU', #Baidu
##                                       'TROW', #T. Rowe Price Group
##                                       'FSLR', #First Solar
##                                       'M',    #Macy's
##                                       'WHR',  #Whirlpool
##                                       'EXPE', #Expedia
##                                       'AMD',  #AMD
##                                       'ATI',  #ATI
##                                       'LYG',  #Lloyds Banking Group
##                                       'DB',   #Deutsche Bank
##                                       'BP',   #BP
##                                       'GS',   #Goldman Sachs
##                                       'BCS',  #Barclays
##                                       'WLP',  #WellPoint
##                                       'SPY',  #S&P500 ETF
##                                       'ADM',  #Archer Daniels Midland
##                                       'GIS',  #General Mills
##                                       'QCOM', #QCOM
##                                       'INTC', #Intel
##                                       'ARMH', #ARM
##                                       'DDS',  #Dillards
##                                       'F',    #Ford
##                                       'ERJ',  #Embraer
##                                       'NVDA', #Nvidia
##                                       'GRMN', #Garmin
##                                       'RHT',  #Redhat
##                                       '.DJI', #Dow Jones Index
##                                       '.INX', #S&P 500 Index
##                                    
                                      ]
        db = MarketDatabase(stock_list = stock_list)
        #stock_list = db.stock_list

##        for x in range(100000):
##            strat.buy_low_sell_high({'GOOG' : {"time":float(x),"price":float(random.randrange(450,500))}}, 'GOOG')
##        strat.load_db(datetime.date(2010,6,24), 'GOOG')
##        strat.load_db(datetime.date(2010,6,25), 'GOOG')
        gain = 0
        max_gain = -1000
        start_date =datetime.date(2010,7,12)
        end_date =datetime.date(2010,8,20)
        sim_data = db.read_all(start_date, end_date)

        #new max found 11.1315112954 4.66050510453 1.0254884932 0.0137193348269 0.113086588052 0.0195327382212 1 week
        #new max found 48.5274565768 10.6150329681 1.53237120954 0.0108413092798 1.27231711381 0.0195020574522 3 weeks
        #new max found 64.3287008232 7.8456215033 2.18399487385 0.0128036644208 0.119820614037 0.0114842379248 3 weeks
        #new max found 86.4206890586 8.12520470729 1.41136594102 0.010101497361 0.239392395487 0.0164724766028 3 weeks
        #new max found 104.663280129 12.6622310013 1.69001063985 0.010472581511 0.22200245199 0.0181101538893  3 weeks
        #new max found 65.5935373522 10.5258358092 1.5401738368 0.0116771367785 0.124419153553 0.00485075994192 3 weeks
        #new max found 45.9062776244 4.19568160109 1.62210306938 0.0105185604479 0.458940600157 0.0103541816628 3 weeks
        #new max found 106.288941112 9.51369571618 1.37799936961 0.0100475536759 1.03788004431 0.0154253500965 18 days
        #new max found 130.265453502 12.6622310013 1.69001063985 0.010472581511 0.22200245199 0.0181101538893 18 days
        #new max found 11.53231431 4.32622063906 1.44670764669 0.015941246609 0.233625633226 0.0082934085183
        std_dev_hours =  6.5*3
        stdDevFactor = 1.44670764669
        std_dev_percent = 0.015941246609
        derivative_moving_average_hours=0.233625633226
        stop_loss = 0.1
        while 1:

            print 'trying', gain, std_dev_hours, stdDevFactor, std_dev_percent, derivative_moving_average_hours,  stop_loss
            strat = Strategy(sim_data,
                             stock_list,
                             db,
                             start_date,
                             end_date = end_date,
                             std_dev_hours =std_dev_hours,
                             stdDevFactor = stdDevFactor,
                             std_dev_percent=std_dev_percent,
                             derivative_moving_average_hours = derivative_moving_average_hours,
                             stop_loss = stop_loss)            
            gain = strat.run_simulation()
            if gain > max_gain:
                max_gain = gain
                print 'new max found', max_gain, std_dev_hours, stdDevFactor, std_dev_percent, derivative_moving_average_hours, stop_loss
                # gain is not the only thing that is important, you want to also maximize the win/loss ratio
            std_dev_hours = random.uniform(3.0,6.5*3)
            #std_dev_hours = 6.5*6
            stdDevFactor = random.uniform(1.0,3.0)
            std_dev_percent = random.uniform(0.01,0.02)
            stop_loss = random.uniform(0.001,0.1)
            #stop_loss = 0.1
            derivative_moving_average_hours=random.uniform(0.1,3.0)
        print "complete"

def LRU_test():
    GoogleThread().start()
    #YahooPushThread().start()

def Strategy_test():
    StrategyThread().start()

def yahoo_socket_connect(s):
    HOST = "streamerapi.finance.yahoo.com"
    PORT = 80
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.setsockopt( socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        s.connect((HOST,PORT))
    except socket.gaierror as e:
        print type(e)
        return None
    except socket.timeout as e:
        print type(e)
        return None
    stock_str = ",".join(stock_list)
    s.send('GET /streamer/1.0?s=' + stock_str + '&k=l10&callback=parent.yfs_u1f&mktmcb=parent.yfs_mktmcb&gencallback=parent.yfs_gencb HTTP/1.1\r\nHost: streamerapi.finance.yahoo.com\r\nAccept-Encoding: identity\r\n\r\n')
    return s    

def google_socket_connect(s):
    HOST = "finance.google.com"
    PORT = 80
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.setsockopt( socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        s.connect((HOST,PORT))
    except socket.gaierror as e:
        print type(e)
        return None
    except socket.timeout as e:
        print type(e)
        return None
    stock_str = ",".join(stock_list)
    s.send('GET /finance/info?client=ig&q=NASDAQ:GOOG HTTP/1.1\r\nHost: finance.google.com\r\nAccept-Encoding: gzip,deflate,sdch\r\n\r\n')
    return s

class Point:
    def __init__(self):
        self.x = 0
        self.y = 0

def Write_To_File(f, line, time_stamp):
    l10 = "last trade"
    v00 = "volume"
    t10 = "last trade time"
    p = Point()
    try:
        d = eval(line)
    except NameError as e:
        print type(e)
        return
    stock = d.keys()[0] # should not have more than one stock in dictionary item received from Yahoo
    if stock in stock_list:
        for key in d[stock].keys():
            f[stock].write(str(time_stamp) + "\t" + d[stock][key])
            p.x = float(d[stock][key])
            p.y = time_stamp
            stock_data[stock].append(p)
        f[stock].write('\n')
        f[stock].flush()



##def trade():
##    trade_data = {}
##    max_m = 0
##    max_stock = ""
##    for stock in stock_list:
##        items = min(len(stock_data[stock]), 20)
##        #for i in range(0, items):
##        #    p = stock_data[stock][-1 * (item - i)]
##        trade_data[stock] = least_squares_method(stock_data[stock][items:])
##    for stock in stock_list:
##        m,b = trade_data[stock]
##        if m > max_m:
##            max_m = m
##            max_stock = stock
##    return max_stock, m
##
##def periodic():
##    state = "idle"
##
##    if state == "idle":
##        for stock in stock_list:
##            if len(stock_data[stock]) < 20:
##                fail = False
##                break
##        if not fail:
##            state = "buy"
##    elif state == "buy":
##        stock, m = max_slope()
##        if m > 0:
##            buy.append((stock,stock_data[stock][-1:]))
##        state = "sell"
##    elif state == "sell":
##        if (stock_data[current_stock][-1:] - buy[-1:][1] ) / start_price < -0.5:
##            sell.append((stock,stock_data[stock][-1:]))
##        elif 


## stock data feed
## microblogging
## 
                
def test():
    global lastMarketState
    global currentMarketState
    init()
    file_handles = {}
    pattern = "(?<=\(){.+}(?=\))"
    s = None
    s = yahoo_socket_connect(s)
    data = ""
    recvTime = time.time()
    while 1:
        try:
            if s:
                data = data + s.recv(1)
            else:
                s = yahoo_socket_connect(s)
        except socket.timeout as e:
            ## PERIODIC PROCESSING
            if currentMarketState.ismarketopen():
                currentMarketState = "open"
            else:
                currentMarketState = "close"
            
            if lastMarketState == "close" and currentMarketState == "open":
                PostUpdate("market open")
                date = datetime.datetime.now()
                for stock in stock_list:
                    path = '/Users/xavier/Documents/db/' + stock + '/'
                    file_name = str(date.year) + '_' + "%02d" % (date.month) + '_' + "%02d" % (date.day) + '.txt'
                    if not os.path.exists(path):
                        os.makedirs(path)
                    file_handles[stock]= open(path + file_name, 'w')      
            elif lastMarketState == "open" and currentMarketState == "close":
                PostUpdate("market close")
                for stock in stock_list:
                    file_handles[stock].close()
                file_handles = {}

            lastMarketState = currentMarketState
            
            if data != "":
                recvTime = time.time()
                #print "rx:", data
                scriptList = BeautifulSoup(data).findAll('script')
                for script in scriptList:
                    print script
                    match = re.search(pattern, script.string)
                    if match: # don't forget to eliminate the document header
                        print match.group()
                        ratelimit(match.group())
                        if file_handles:
                            Write_To_File(file_handles, match.group(), recvTime)
                data = ""
                
            elif time.time() - recvTime > 6 * 60:
                errorLog("did not receive data from server in 6 minutes, reconnecting")
                s.close()
                s = None
        except socket.error as e:
            errno, errstr = sys.exc_info()[:2]
            errorLog(str(errno))
            errorLog(str(type(errstr)))
            errorLog(str(errstr))
            errorLog(str(time.time()) + ", reconnecting")
            s.close()
            s = None
              
def chart():
    f = open('/Users/Xavier/Documents/db/420.txt','r')
    data = []
    for line in f:
        data.append(Decimal(line))
        if len(data) == 1000:
            break
    chart = SimpleLineChart(400, 250, y_range=[470, 500])
    chart.add_data(data)
    # Set the line colour to blue
    chart.set_colours(['0000FF'])
    chart.download('test.png')



def least_squares_method(data):
    n = len(data)
    b = 0
    m = 0
    sum_x = 0
    sum_y = 0
    sum_xx = 0
    sum_yy = 0
    sum_xy = 0
    for point in data:
        sum_x = sum_x + point.x
        sum_y = sum_y + point.y
        xx = pow(point.x,2)
        sum_xx = sum_xx + xx
        xy = point.x * point.y
        sum_xy = sum_xy + xy

    b=(-sum_x*sum_xy+sum_xx*sum_y)/(n*sum_xx-sum_x*sum_x)
    m=(-sum_x*sum_y+n*sum_xy)/(n*sum_xx-sum_x*sum_x)
    print "Y = %sX + %s"%(m,b)
    print "100 * m/b = %s" % (100 * m/b)
    return (m,b)

def least_squares_test():
    n = 500
    f = open('/Users/xavier/Documents/db/420.txt','r')
    data = []
    sum_x = 0
    y_list = []
    best_fit_list = []
    m = 0
    b = 0
    for line in f:
        point = Point()
        point.y = float(line)
        y_list.append(point.y)
        sum_x = sum_x + 1
        point.x = sum_x
        data.append(point)
        if len(data) == n:
            break
    m,b = least_squares_method(data)
    chart = SimpleLineChart(400, 250, y_range=[470, 500])
    chart.add_data(y_list)
    for x in range(1, n + 1):
        best_fit_list.append(m*x + b)
    chart.add_data(best_fit_list)
    # Set the line colour to blue
    chart.set_colours(['0000FF'])
    chart.download('best_fit_test.png')

def average(mylist):
    return sum(mylist)/len(mylist)

def standardDeviation(mylist):
    deviationSquared = []
    avg = average(mylist)
    for item in mylist:
        deviationSquared.append((avg - item) ** 2)
    return ((sum(deviationSquared)/(len(deviationSquared)-1)) ** 0.5)

##def movingAverage(mylist, averageNElements):
##    result = []
##    listToAverage = []
##    avgOfMyList = average(mylist)
##    for i in range(len(mylist)):
##        if (i > averageNElements - 1):
##            listToAverage.pop(0)
##            listToAverage.append(mylist[i])
##            result.append(average(listToAverage))
##        elif (i < averageNElements - 1):
##            listToAverage.append(mylist[i])
##            result.append(avgOfMyList)
##        else:
##            listToAverage.append(mylist[i])
##            result.append(average(listToAverage))
##    #print result
##    return result

def movingAverage(mylist, averageNElements, average):
    if len(mylist) >= averageNElements:
        slicedlist = mylist[-averageNElements:]
        return sum(slicedlist) / len(slicedlist)
    else:
        return average

def slope(x1,y1,x2,y2):
    return (y2 - y1) / (x2 - x1)

def findEquationOfALine(x1,y1,x2,y2):
    ## Finds the slope and y-intercept
    ## y = m*x + b return (m,b)
    #print x1,y1,x2,y2
    
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    return m,b
        

def determinant(a,b,c,d):
    ## matrix in the form of [a b]
    ##                       [c d]
    return (a*d - b*c)

def cramersRule(m1,b1,m2,b2):
    ## ax + by = e
    ## cx + dy = f
    a = float(-m1)
    b = 1.0
    e = float(b1)
    c = float(-m2)
    d = 1.0
    f = float(b2)
    x = 0.0
    y = 0.0
    d0 = determinant(a,b,c,d)
    dx = determinant(e,b,f,d)
    dy = determinant(a,e,c,f)
    #print d0, dx, dy, e, b, f, d
    if d0 == 0 and dx == 0 and dy == 0:
        return "same lines", x, y
    elif d0 == 0 and (dx != 0 or dy != 0):
        return "parallel lines", x, y
    else: # solution
        x = dx / d0
        y = dy / d0
        return "intersecting lines", x, y
    
def intersect(segment1, segment2, ix1, ix2):
    # detects intersection over interval (x1,x2]
#    print 'int', s1x1, s1y1, s1x2, s1y2
    #try:
    m1, b1 = findEquationOfALine(segment1.start_point.x, segment1.start_point.y, segment1.end_point.x, segment1.end_point.y)
##    except:
##        print s1x1, s1y1, s1x2, s1y2
    m2, b2 = findEquationOfALine(segment2.start_point.x, segment2.start_point.y, segment2.end_point.x, segment2.end_point.y)
    status, x, y = cramersRule(m1,b1,m2,b2)
    #print x, y
    if status == "intersecting lines":
        if (x > min(ix1,ix2) and x <= max(ix1,ix2)):
            return True
    return False

def buy(stock, price):
    #print "buy"
    global state
    global workingStock
    global decisionLog
    global clock
    state = "bought"
    workingStock = stock
    #print "test"
    #print clock, stock, price
    decisionLog.append([clock, "bought", stock, price, 0])
    print [clock, "bought", stock, price, 0]

def sell( stock, price):
    #print "sell"
    global state
    global workingStock
    global decisionLog
    global clock
    state = "none held"
    workingStock = None
    percent = 0.0
    percent = (price - decisionLog[-1][3]) * 100.0 / decisionLog[-1][3]
    decisionLog.append([clock, "sold", stock, price, percent])
    print [clock, "sold", stock, price, percent]

def load():
    file_handles = {}
    for stock in stock_list:
        file_handles[stock]= open('/Users/xavier/Documents/db/' + stock + '.txt', 'r')
        while 1:
            line = file_handles[stock].readline()
            if not line:
                break
            try:
                stock_data[stock].append(float(line))
            except ValueError:
                pass

def crash(dbdict):
    global clock
    global shortMA
    global longMA
    clock = clock + 1
    #print clock
    longMAElements = 4160
    shortMAElements = 720

    if clock <= (len(dbdict[stock_list[0]])):

        if state == "none held":
            #print "b1"
            for stock in dbdict:
                if clock > longMAElements:
                    shortMA.pop(0)
                    shortMA.append(movingAverage(dbdict[stock][:clock], shortMAElements))
                    longMA.pop(0)
                    longMA.append(movingAverage(dbdict[stock][:clock], longMAElements))
                    if intersect(clock-1, shortMA[-2], clock, shortMA[-1], clock-1, longMA[-2], clock, longMA[-1], clock-1, clock):
                        m1, b1 = findEquationOfALine(clock-1, shortMA[-2], clock, shortMA[-1])
                        m2, b2 = findEquationOfALine(clock-1, longMA[-2], clock, longMA[-1])
                        if m1 > m2:
                            ## short MA is crossing over long MA
                            ## buy signal
                            buy(stock, dbdict[stock][:clock][-1])

        elif state == "bought":
            #print "b2"
            shortMA.pop(0)
            shortMA.append(movingAverage(dbdict[workingStock][:clock], shortMAElements))
            longMA.pop(0)
            longMA.append(movingAverage(dbdict[workingStock][:clock], longMAElements))
            #print shortMA[-1], longMA[-1], dbdict[workingStock][:clock][-1]
            if intersect(clock-1, shortMA[-2], clock, shortMA[-1], clock-1, longMA[-2], clock, longMA[-1], clock-1, clock):
                m1, b1 = findEquationOfALine(clock-1, shortMA[-2], clock, shortMA[-1])
                m2, b2 = findEquationOfALine(clock-1, longMA[-2], clock, longMA[-1])
                if m1 < m2:
                    ## sell signal if holding this stock
                    sell(workingStock, dbdict[workingStock][:clock][-1])
        return "continue"
    else:
        return "complete"

def max_stock_len(mylist):
    msl = 0
    for stock in mylist:
        msl = max(msl, len(mylist[stock]))
    #print msl
    return msl

#class Point:
#    def __init__(self, x, y):
#        self.x = x
#        self.y = y

class Segment:
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point



import pylab 
def plot_stock(stock, date):
    db = MarketDatabase()
    results = db.read(stock, date, date)
    data_points_per_hour = db.get_data_points(stock, date) / 6.5
    ma_price_duration = int(0.01 * data_points_per_hour)
    short_ma_price_duration = int(1.0 * data_points_per_hour)
    ma_speed_duration = int(0.01 * data_points_per_hour)
    ma_accel_duration = int(0.01 * data_points_per_hour)
    t = results[stock]['time']
    price = results[stock]['price']
    #print t
    #print price,
    speed = [slope(t[i], price[i], t[i+1], price[i+1]) for i in range(len(t)-1)]
    speed.insert(0,0)
##    for i in range(len(speed)):
##        print speed[i]
    #print speed
    accel = [slope(t[i], speed[i], t[i+1], speed[i+1]) for i in range(1, len(t)-1)]
    accel.insert(0,0)
    accel.insert(0,0)
    #print accel
    ma_price = [movingAverage(price[:i], ma_price_duration, average(price)) for i in range(len(t))]
##    ma_speed = [movingAverage(speed[:i], ma_speed_duration, 0) for i in range(len(t))]
##    ma_accel = [movingAverage(accel[:i], ma_accel_duration, 0) for i in range(len(t))]


    ma_speed = [slope(t[i], ma_price[i], t[i+1], ma_price[i+1]) for i in range(len(t)-1)]
    ma_speed.insert(0,0)
    ma_speed = [movingAverage(ma_speed[:i], ma_speed_duration, 0) for i in range(len(t))]
##    for i in range(len(speed)):
##        print speed[i]
    #print speed
    ma_accel = [slope(t[i], ma_speed[i], t[i+1], ma_speed[i+1]) for i in range(1, len(t)-1)]
    ma_accel.insert(0,0)
    ma_accel.insert(0,0)
    ma_accel = [movingAverage(ma_accel[:i], ma_accel_duration, 0) for i in range(len(t))]

    
    short_price = [movingAverage(price[:i], short_ma_price_duration, average(price)) for i in range(len(t))]
    plt.figure(1)
    plt.subplot(611)
    plt.plot(t, price, 'b')
    plt.subplot(612)
    plt.plot(t, short_price, 'g', t, ma_price, 'b')
    plt.subplot(613)
    plt.plot(t,speed, 'r')

    plt.subplot(614)
    plt.plot(t, accel, 'b')
    plt.subplot(615)
    plt.plot(t, ma_speed)
    empty = [0] * (len(t))
    t =numpy.array(t)
    ma_speed=numpy.array(ma_speed)
    ma_accel=numpy.array(ma_accel)
    plt.fill_between(t, ma_speed, 0,  where=ma_speed>0, facecolor='green')
    plt.fill_between(t, ma_speed, 0,  where=ma_speed<0, facecolor='red')
    pylab.ylim((-0.07,0.07))
    plt.subplot(616)
    plt.plot(t,ma_accel)
    plt.fill_between(t, 0, ma_accel,  where=ma_accel>0, facecolor='green')
    plt.fill_between(t, 0, ma_accel,  where=ma_accel<0, facecolor='red')
    pylab.ylim((-0.007,0.007))
    plt.show()
    
    

class Strategy:
    def __init__(self, sim_data, stock_list, db, start_date, end_date = datetime.date.today(),std_dev_hours=4.0, stdDevFactor = 1.0, std_dev_percent=1.0, derivative_moving_average_hours=0.25, stop_loss = 0.008):
        self.derivative = {}
        self.shortMA = {}
        self.longMA = {}
        self.flag_counter = {}
        #self.workingStock = None
        self.state = {}
        self.decisionLog = []
        self.dbdict = {}
        self.db = db
        self.data_points_per_hour_dict = {}
        self.sum_of_points = {}
        self.std_dev_hours = std_dev_hours
        self.derivative_moving_average_hours = derivative_moving_average_hours
        self.start_date = start_date
        self.end_date = end_date
        self.std_dev_percent = std_dev_percent
        self.longMAElements = {}
        self.shortMAElements = {}
        self.long_moving_average_partial_sum = {}
        self.short_moving_average_partial_sum = {}
        self.stdDevFactor = stdDevFactor
        self.stop_loss = stop_loss
        self.running_total = 0
        self.sim_data = sim_data
        self.elements_received = {}
        self.start_time = {}
        self.hack_adjust = (6.5 * ((self.end_date-self.start_date).days+1-6)) / (6.5 * ((self.end_date-self.start_date).days+1)) * .55992086
        self.price_duration_timedelta = datetime.timedelta(hours=std_dev_hours)  #remove hack
        self.derivative_duration_timedelta = datetime.timedelta(hours=derivative_moving_average_hours)  #remove hack

        for stock in stock_list:
            self.derivative[stock] = {"price" : None, "time" : None}
            self.flag_counter[stock] = 0
            self.dbdict[stock] = {"price" : None, "time" : None}
            self.data_points_per_hour_dict[stock] = 0
            self.sum_of_points[stock] = 0
            ## True = Entry Strategy, False = Exit Strategy
            self.state[stock] = True
            self.long_moving_average_partial_sum[stock] = 0
            self.short_moving_average_partial_sum[stock] = 0
            self.elements_received[stock] = 0
            self.start_time[stock] = None

        for day in range(0, (self.end_date-self.start_date).days+1):   
            for stock in stock_list:
                self.sum_of_points[stock] = self.sum_of_points[stock] + db.get_data_points(stock, self.start_date+datetime.timedelta(days=day))

        for stock in stock_list:
            self.data_points_per_hour_dict[stock] = self.sum_of_points[stock] / (6.5 * ((self.end_date-self.start_date).days+1))
            self.longMAElements[stock] = int(round(self.data_points_per_hour_dict[stock] * self.std_dev_hours))
            self.shortMAElements[stock] = int(round(self.data_points_per_hour_dict[stock] * self.derivative_moving_average_hours))
            #TODO: why dont these deques have max lengths?
            self.dbdict[stock]["price"] = deque() #deque(maxlen=self.longMAElements[stock]) #deque()
            self.dbdict[stock]["time"] = deque() #deque(maxlen=self.longMAElements[stock]) #deque()
            self.derivative[stock]["price"] = deque() #deque(maxlen=self.shortMAElements[stock]) #deque()
            self.derivative[stock]["time"] = deque() #deque(maxlen=self.shortMAElements[stock]) #deque()
            self.shortMA[stock] = deque() #deque( maxlen=self.longMAElements[stock])
            self.longMA[stock] = deque() #deque( maxlen=self.longMAElements[stock])
        #print self.sum_of_points
        #print self.data_points_per_hour_dict

##    def calculate_constants(self, stock):
##        longMAElements = int(round(self.data_points_per_hour_dict[stock] * self.std_dev_hours)) #4320 2880
##        shortMAElements = int(round(self.data_points_per_hour_dict[stock] * self.derivative_moving_average_hours)) #1040 720 360 180
##        stdDevMAElements = longMAElements
##        stdDevMultiplier = 1
##        return longMAElements, shortMAElements, stdDevMAElements, stdDevMultiplier

    def moving_average(self, stock, mylist):
        length = len(mylist)
        if length == self.longMAElements[stock]:
            partial_sum = self.long_moving_average_partial_sum 

        else:
            partial_sum = self.short_moving_average_partial_sum

        if not partial_sum[stock] == 0:
            partial_sum[stock] = partial_sum[stock] + mylist[-1]
            s = partial_sum[stock]
        else:
            s = sum(mylist)

        partial_sum[stock] = s - mylist[0]

        return s / length

##    def load_file(self, date, stock):
##        results = self.db.read(stock, date)
##        for i in range (len(results[stock]["price"])):
##            data = {stock : {"time" : results[stock]["time"][i], "price" : results[stock]["price"][i]}}
##            self.buy_low_sell_high(data)
##
##    def load_all_files(self):
##        results = self.db.read_all(self.start_date, self.end_date)
##        self.sim_data = results


    def run_simulation(self):
        for i in xrange(len(self.sim_data)):
            #print 'simulating', self.sim_data[i]
            self.buy_low_sell_high(self.sim_data[i])
        return self.running_total        

    def _buy(self, stock, price, time):
        #print "buy"
        self.state[stock] = False
        #self.workingStock = stock
        #print "test"
        #print clock, stock, price
        self.decisionLog.append([time, "bought", stock, price, 0])
        #print [time, "bought", stock, price, 0]
        #self.plot(stock,time,price)

    def _purchase_price(self,stock):
        bought_index = 0
        for i in range(0,len(self.decisionLog)):
            if self.decisionLog[len(self.decisionLog)-1-i][2] == stock:
                bought_index = len(self.decisionLog)-1-i
                break
        return self.decisionLog[bought_index][3]

    def _sell(self, stock, current_price, time):
        #print "sell"
        self.state[stock] = True
        #self.workingStock = None
        percent = 0.0
        purchase_price = self._purchase_price(stock)
 
        percent = (current_price - purchase_price) * 100.0 / purchase_price
        self.decisionLog.append([time, "sold", stock, current_price, percent])
        self.running_total = self.running_total + percent
        #print [time, "sold", stock, current_price, percent, self.running_total ]
        #self.plot(stock,time,current_price)

    def calculate_moving_averages(self, clock, stock):
        if len(self.dbdict[stock]["time"]) > 1:
            m1 = slope(self.dbdict[stock]["time"][-2], \
                       self.dbdict[stock]["price"][-2], \
                       self.dbdict[stock]["time"][-1], \
                       self.dbdict[stock]["price"][-1])

##            if len(self.derivative[stock]) >= self.shortMAElements[stock]:
##                self.derivative[stock].pop(0)
##                self.derivative[stock].append(m1)
##            else:
            #self.derivative[stock]["price"].append(m1)
            #self.derivative[stock]["time"].append(self.dbdict[stock]["time"][-1])
            unix_time_at_start = minus(datetime.datetime.fromtimestamp(float(self.dbdict[stock]["time"][-1])) \
                                 , self.derivative_duration_timedelta)
            time_based_moving_average_append(self.derivative[stock], \
                                             m1, \
                                             self.dbdict[stock]["time"][-1], \
                                             datetime_to_unixtime(unix_time_at_start))
            #print self.derivative
        
        # if timestamp - duration >= stock start time in database
        # in other words if we have enough data in the database to perform a 
        # moving average
        if minus(datetime.datetime.fromtimestamp(float(self.dbdict[stock]["time"][-1])), self.price_duration_timedelta) \
           >= self.start_time[stock]:
            #self.shortMA[stock].pop(0)
            self.shortMA[stock].append(average(self.derivative[stock]["price"]))
            #self.longMA[stock].pop(0)
            self.longMA[stock].append(average(self.dbdict[stock]["price"]))
            #print self.shortMA[stock]
            #

    def entry_strategy(self, clock, stock ):
        if len(self.shortMA[stock]) > 1 and len(self.dbdict[stock]["time"]) > 1:

            if self.flag_counter[stock] == 4:
                self._buy(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])
                self.flag_counter[stock] = 0
            
            if self.flag_counter[stock] > 0:
                self.flag_counter[stock] = self.flag_counter[stock] + 1


            stdDevMA = npstd(list(self.dbdict[stock]["price"])[::5])

            derivative_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], \
                self.shortMA[stock][-2]], \
                [self.dbdict[stock]["time"][-1], \
                self.shortMA[stock][-1]]]
            price_equals_zero_line_segment = \
                [[self.dbdict[stock]["time"][-2], 0], \
                [self.dbdict[stock]["time"][-1],0]]
            if intersection(derivative_moving_average_line_segment, \
                         price_equals_zero_line_segment):

##                print 'intersection', self.dbdict[stock]["time"][-1], ":", self.dbdict[stock]["price"][-1], "<", \
##                      self.longMA[stock][-1] - stdDevMA * self.stdDevFactor, ",", \
##                      stdDevMA * self.stdDevFactor / self.longMA[stock][-1], ">=", self.std_dev_percent, ",", len(self.dbdict[stock]["time"])
##                
                if (self.dbdict[stock]["price"][-1] < self.longMA[stock][-1] - stdDevMA * self.stdDevFactor) \
                   and (stdDevMA * self.stdDevFactor / self.longMA[stock][-1] >= self.std_dev_percent):

                    if self.shortMA[stock][-1] > 0:
                        ## short MA is crossing over long MA
                        ## buy signal
                        self.flag_counter[stock] = 1
                        #print "buy pending"
                if self.shortMA[stock][-1] <= 0:
                    self.flag_counter[stock] = 0
                    #print "cancel buy"

    def exit_strategy(self, stock):

        #print (self.dbdict[stock]["price"][-1] - self._purchase_price(stock)) / self._purchase_price(stock) 
        
        if ((self.dbdict[stock]["price"][-1] - self._purchase_price(stock)) / self._purchase_price(stock)) <= -self.stop_loss:
            # stop loss
            #print 'stop loss'
            self._sell(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])
        else:
            stdDevMA = npstd(list(self.dbdict[stock]["price"])[::5])

            derivative_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], \
                self.shortMA[stock][-2]],
                [self.dbdict[stock]["time"][-1], \
                self.shortMA[stock][-1]]]
            price_equals_zero_line_segment = \
                [[self.dbdict[stock]["time"][-2], 0], \
                [self.dbdict[stock]["time"][-1], 0]]
            if intersection(derivative_moving_average_line_segment, \
                         price_equals_zero_line_segment) \
                and self.dbdict[stock]["price"][-1] > \
                    self.longMA[stock][-1]:
                if self.shortMA[stock][-1] <= 0:
                    #print self.dbdict[stock]["price"][-1], self.longMA[stock][-1]
                    ## sell signal if holding this stock
                    self._sell(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])

    def calculate_moving_averages2(self, clock, stock):
        if clock > 1:
            self.derivative[stock].append(self.dbdict[stock]["price"][-1])
        if clock >= self.longMAElements[stock]:
            self.shortMA[stock].append(average(self.derivative[stock]))
            self.longMA[stock].append(average(self.dbdict[stock]["price"]))



    def entry_strategy2(self, clock, stock ):
        #print 'entry strat', clock, self.longMAElements[stock]
        if clock > self.longMAElements[stock]:
            
            short_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], \
                self.shortMA[stock][-2]], \
                [self.dbdict[stock]["time"][-1], \
                self.shortMA[stock][-1]]]
            long_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], self.longMA[stock][-2]], \
                [self.dbdict[stock]["time"][-1],self.longMA[stock][-1]]]
            if intersection(short_moving_average_line_segment, \
                         long_moving_average_line_segment):

                if self.shortMA[stock][-1] > self.longMA[stock][-1]:
                    self._buy(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])

    def exit_strategy2(self, stock):
        short_moving_average_line_segment = \
            [[self.dbdict[stock]["time"][-2], \
            self.shortMA[stock][-2]],
            [self.dbdict[stock]["time"][-1], \
            self.shortMA[stock][-1]]]
        long_moving_average_line_segment = \
            [[self.dbdict[stock]["time"][-2], self.longMA[stock][-2]], \
            [self.dbdict[stock]["time"][-1], self.longMA[stock][-1]]]
        if intersection(short_moving_average_line_segment, \
                     long_moving_average_line_segment):
            #print 'sold state intersection'
            if self.shortMA[stock][-1] < self.longMA[stock][-1]:
                self._sell(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])


    def calculate_moving_averages3(self, clock, stock):
        if clock > 1:
            m1 = slope(self.dbdict[stock]["time"][-2], \
                       self.dbdict[stock]["price"][-2], \
                       self.dbdict[stock]["time"][-1], \
                       self.dbdict[stock]["price"][-1])

##            if len(self.derivative[stock]) >= self.shortMAElements[stock]:
##                self.derivative[stock].pop(0)
##                self.derivative[stock].append(m1)
##            else:
            self.derivative[stock].append(m1)
            #print self.derivative
        if clock >= self.longMAElements[stock]:
            #self.shortMA[stock].pop(0)
            self.shortMA[stock].append(average(self.derivative[stock]))
            #self.longMA[stock].pop(0)
            self.longMA[stock].append(average(self.dbdict[stock]["price"]))
            #print self.shortMA[stock]

    def entry_strategy3(self, clock, stock ):
        if clock > self.longMAElements[stock]:

            if self.flag_counter[stock] == 4:
                self._buy(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])
                self.flag_counter[stock] = 0
            
            if self.flag_counter[stock] > 0:
                self.flag_counter[stock] = self.flag_counter[stock] + 1


            stdDevMA = npstd(list(self.dbdict[stock]["price"])[::5])

            derivative_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], \
                self.shortMA[stock][-2]], \
                [self.dbdict[stock]["time"][-1], \
                self.shortMA[stock][-1]]]
            price_equals_zero_line_segment = \
                [[self.dbdict[stock]["time"][-2], 0], \
                [self.dbdict[stock]["time"][-1],0]]
            if intersection(derivative_moving_average_line_segment, \
                         price_equals_zero_line_segment):
                
                if (self.dbdict[stock]["price"][-1] < self.longMA[stock][-1] - stdDevMA * self.stdDevFactor) \
                   and (stdDevMA * self.stdDevFactor / self.longMA[stock][-1] >= self.std_dev_percent):

                    if self.shortMA[stock][-1] > 0:
                        ## short MA is crossing over long MA
                        ## buy signal
                        self.flag_counter[stock] = 1
                        #print "buy pending"
                if self.shortMA[stock][-1] <= 0:
                    self.flag_counter[stock] = 0
                    #print "cancel buy"

    def exit_strategy3(self, stock):

        #print (self.dbdict[stock]["price"][-1] - self._purchase_price(stock)) / self._purchase_price(stock) 
        
        if ((self.dbdict[stock]["price"][-1] - self._purchase_price(stock)) / self._purchase_price(stock)) <= -self.stop_loss:
            # stop loss
            #print 'stop loss'
            self._sell(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])
        else:
            stdDevMA = npstd(list(self.dbdict[stock]["price"])[::5])

            derivative_moving_average_line_segment = \
                [[self.dbdict[stock]["time"][-2], \
                self.shortMA[stock][-2]],
                [self.dbdict[stock]["time"][-1], \
                self.shortMA[stock][-1]]]
            price_equals_zero_line_segment = \
                [[self.dbdict[stock]["time"][-2], 0], \
                [self.dbdict[stock]["time"][-1], 0]]
            if intersection(derivative_moving_average_line_segment, \
                         price_equals_zero_line_segment) \
                and self.dbdict[stock]["price"][-1] > \
                    self.longMA[stock][-1]:
                if self.shortMA[stock][-1] <= 0:
                    #print self.dbdict[stock]["price"][-1], self.longMA[stock][-1]
                    ## sell signal if holding this stock
                    self._sell(stock, self.dbdict[stock]["price"][-1], self.dbdict[stock]["time"][-1])



    def append_data_element(self, stock_values_length, stock, data):
        if ((stock_values_length >= 1) and \
           not self.dbdict[stock]["time"][-1] == data[stock]["time"] and \
           not self.dbdict[stock]["price"][-1] == data[stock]["price"]) \
           or (stock_values_length == 0):

            #self.dbdict[stock]["time"].append(data[stock]["time"])
            #self.dbdict[stock]["price"].append(data[stock]["price"])
            unix_time_at_start = minus(datetime.datetime.fromtimestamp(float(data[stock]["time"])) , self.price_duration_timedelta)
            time_based_moving_average_append(self.dbdict[stock], \
                                             data[stock]["price"], \
                                             data[stock]["time"], \
                                             datetime_to_unixtime(unix_time_at_start))
            self.elements_received[stock] = self.elements_received[stock] + 1

            if not self.start_time[stock]:
                self.start_time[stock] = datetime.datetime.fromtimestamp(float(data[stock]["time"]))
            #print 'running sim data'
            return True
        else:
            #log an error
            #print 'tossing sim data'
            return False 
    
    def buy_low_sell_high(self, data):
        # The entry strategy looks for the derivative line to rise above the y = 0 line and the current price to be one std dev lower than the moving average.
        # The exit strategy looks for the derivative line to fall below the y = 0 line and the current price to be above the moving average.
        stock = data.keys()[0]
        clock = self.elements_received[stock]
        success = self.append_data_element(clock, stock, data)
        if not success:
            return

        clock = self.elements_received[stock]
        self.calculate_moving_averages(clock, stock)

        if self.state[stock]:
            self.entry_strategy(clock, stock)
        else:
            self.exit_strategy(stock)


##        if clock % 1000 == 0:
##            self.plot(stock)

        return

    def plot(self,stock, time=0, price=0):
        print 'plot'
        plt.figure(1)
        print 'figure'
        plt.subplot(211)
        print 'test'
        print len(self.longMA[stock])
        print len(self.shortMA[stock])
        print len(self.dbdict[stock]['time'])
        if time != 0:
            truncate = min(len(self.dbdict[stock]['time']),len(self.longMA[stock]))
            plt.plot(self.dbdict[stock]['time'], self.dbdict[stock]['price'], 'k', \
                     [time], [price], 'rp', \
                    list(self.dbdict[stock]['time'])[-truncate:], list(self.longMA[stock])[-truncate:], 'b')
            plt.subplot(212)
            truncate = min(len(self.dbdict[stock]['time']),len(self.shortMA[stock]))
            plt.plot(list(self.dbdict[stock]['time'])[-truncate:], list(self.shortMA[stock])[-truncate:], 'g')
        elif len(self.shortMA[stock]) > 0 and len(self.longMA[stock]) > 0:
            truncate = min(len(self.dbdict[stock]['time']),len(self.longMA[stock]))
            plt.plot(self.dbdict[stock]['time'], self.dbdict[stock]['price'], 'k', \
                     list(self.dbdict[stock]['time'])[-truncate:], list(self.longMA[stock])[-truncate:], 'b')
            plt.subplot(212)
            truncate = min(len(self.dbdict[stock]['time']),len(self.shortMA[stock]))
            plt.plot(list(self.dbdict[stock]['time'])[-truncate:], list(self.shortMA[stock])[-truncate:], 'g')
        #plt.subplot(212)
        #duration = self.data_points_per_hour_dict[stock] * 0.01
        #ma_price = [movingAverage(self.dbdict[stock]['price'],[:i], duration, 0) for i in range(len(self.dbdict[stock]['price']))]
        #plt.plot(self.dbdict[stock]['time'][-self.shortMAElements:], self.shortMA[stock]['price'], 'g', self.dbdict[stock]['time'][-self.longMAElements], self.longMA[stock], 'b', [time],[price], 'rp')
        print 'test1'
        plt.show()
        print 'test2'

##def find_avg_freq(data, peak_amplitude, MAElements):
##    stock = data.has_keys()[0]
##    price = data[stock]["price"]
##    for i range(len(data[stock]["price"]):
##        if i >= MAElements:
##            if i = MAElements:
##                start_timer = data[stock]["time"][i]
##            moving_avg = movingAverage(data[stock]["price"], MAElements)
##            if data[stock]["price"][i] <= moving_avg - peak_amplitude and searching_bottom:
##                searching_bottom = False
##                counter = counter + 1
##            elif data[stock]["price"][i] >= moving_avg:
##                searching bottom = True
##    end_timer = data[stock]["time"][-1]
##    return counter / (end_timer - start_timer)
##    
##def find_avg_freq_test():
##    db = MarketDatabase('GOOG')
##        for x in range(100000):
##            strat.buy_low_sell_high({'GOOG' : {"time":float(x),"price":float(random.randrange(450,500))}}, 'GOOG')
    #print find_avg_freq(db.read(datetime.date(2010,6,24), 'GOOG'), 5, 
    #db.read(datetime.date(2010,6,25), 'GOOG')
    
## write database function which reads files from multiple days
    

class HealthMonitor():
    def __init__(self):
        self.db_path = '/Users/xavier/Documents/db/'
    

def crash2(dbdict):
    global clock
    global shortMA
    global longMA
    global flag_counter
    global derivative
    clock = clock + 1
    #print clock
    longMAElements = 4320 #2880
    shortMAElements = 360 #1040 720 360 180
    stdDevMAElements = 4320
    stdDevMultiplier = 1

    if clock <= (max_stock_len(dbdict)):

        for stock in dbdict:
            if clock > 1 and clock <= len(dbdict[stock]):
                m1, b1 = findEquationOfALine(clock-1, dbdict[stock][:clock][-2], clock, dbdict[stock][:clock][-1])
                derivative[stock].append(m1)
            if clock >= longMAElements and clock <= len(dbdict[stock]):
                shortMA[stock].pop(0)
                shortMA[stock].append(movingAverage(derivative[stock][:clock], shortMAElements))
                longMA[stock].pop(0)
                longMA[stock].append(movingAverage(dbdict[stock][:clock], longMAElements))

        if state == "none held":

         
            
            #print "b1"
            for stock in dbdict:

                if clock <= len(dbdict[stock]) and clock >= longMAElements:
                    

                    if flag_counter[stock] == 4:
                        buy(stock, dbdict[stock][:clock][-1])
                        flag_counter[stock] = 0
                        break
                    
                    if flag_counter[stock] > 0:
                        flag_counter[stock] = flag_counter[stock] + 1
                        #print "increment flag"


                    stdDevMA = npstd(dbdict[stock][:clock][-stdDevMAElements:])
                    
                    if intersect(clock-1, shortMA[stock][-2], clock, shortMA[stock][-1], clock-1, 0, clock, 0, clock-1, clock):

                        if (dbdict[stock][:clock][-1] < longMA[stock][-1] - stdDevMultiplier * stdDevMA) and (stdDevMA / longMA[stock][-1] >= 0.01):
                            print longMA[stock][-1], stdDevMA
    
                            if shortMA[stock][-1] > 0:
                                ## short MA is crossing over long MA
                                ## buy signal
                                flag_counter[stock] = 1
                                #print "buy pending"
                        if shortMA[stock][-1] <= 0:
                            flag_counter[stock] = 0
                            #print "cancel buy"
                    
                        
                    


        elif state == "bought":

            stdDevMA = npstd(dbdict[workingStock][:clock][-stdDevMAElements:])
            #print shortMA[-1], longMA[-1], dbdict[workingStock][:clock][-1]
            if intersect(clock-1, shortMA[workingStock][-2], clock, shortMA[workingStock][-1], clock-1, 0, clock, 0, clock-1, clock) and dbdict[workingStock][:clock][-1] > longMA[workingStock][-1]:
                if shortMA[workingStock][-1] <= 0:
                    print dbdict[workingStock][:clock][-1], longMA[workingStock][-1]
                    ## sell signal if holding this stock
                    sell(workingStock, dbdict[workingStock][:clock][-1])
        return "continue"
    else:
        return "complete"

def intersectionTest():
    t1 = [-1, 1, 0, 2] # intersecting
    t2 = [-1, 1, 0, 0] # intersecting
    t3 = [-1, 1, 0, -1] # intersecting
    t4 = [1.0, 0.0, -1.0, 1.0] # intersecting
    t5 = [1, 1, 1, 1] # same
    t6 = [1, 0, 1, 1] # parallel
    tests = [t1, t2, t3, t4, t5, t6]
    for test in tests:
        status = cramersRule(test[0], test[1], test[2], test[3])
        print status



class ThreadClass(threading.Thread):
    def run(self):
        while 1:
            global stock_data
            crash(stock_data)
            time.sleep(1)

def main():
    global stock_data
    init()
    load()
##    t = ThreadClass()
##    t.start()
    print "loaded"

    print average(stock_data[stock_list[0]]), standardDeviation(stock_data[stock_list[0]])
    while 1:
        status = crash2(stock_data)
        if status == "complete":
            break
##    for i in range(len(shortMA)):
##        print longMA[i], shortMA[i]

def pow_test1():
    x = 5 ** 0.5

def pow_test2():
    x = 5 * 5

def pow_test3():
    x = pow(5, 0.5)

def pow_test():
    for i in range(1000):
        pow_test1()
        pow_test2()
        pow_test3()

def datatype_test1(a, i):
    a.append(i)
    a.pop(0)
    
def datatype_test2(b, i):
    b.append(i)
    b.pop()


def datatype_test():
    a = []
    b = deque(maxlen=10000)
    for i in range(10000):
        datatype_test1(a,i)
        datatype_test2(b,i)

def deviationSquaredF(avg, item):
    return (avg - item) ** 2

def standardDeviationMapReduceStyle(mylist):
    deviationSquared = []
    avg = average(mylist)
    deviationSquared = map((lambda item: (avg - item) ** 2), mylist)
    return ((sum(deviationSquared)/(len(deviationSquared)-1)) ** 0.5)


def npstd(mylist):
    return numpy.std(numpy.array(mylist))

def stddev_test():
    x = standardDeviation(range(50000))
    y = standardDeviationMapReduceStyle(range(50000))
    z = npstd(range(50000))
    #print x,y, z

def npavg(mylist):
    return numpy.average(mylist)

def average_test():
    for i in range(5000):
        y = npavg(numpy.array(range(10000)))
        x = average(range(10000))
    print x,y

def npsum(mylist):
    return numpy.sum(numpy.array(mylist))

def sum_test():
    for i in range(50):
        y = npsum(range(500000))
        x = sum(range(500000))
    print x,y

def profile():
    profile.run('main()')

import Lines

def numint(p1,p2,p3,p4):
    return Lines.seg_intersect(numpy.array(p1),numpy.array(p2),numpy.array(p3),numpy.array(p4))

def intx(p1,p2,p3,p4):
    return intersect(Segment(Point(p1[0],p1[1]),Point(p2[0],p2[1])),Segment(Point(p3[0],p3[1]),Point(p4[0],p4[1])), -10,10)

def intersection(vector1,vector2):
    m1 = (vector1[1][1] - vector1[0][1]) / (vector1[1][0] - vector1[0][0])
    b1 = vector1[0][1] - m1 * vector1[0][0]
    m2 = (vector2[1][1] - vector2[0][1]) / (vector2[1][0] - vector2[0][0])
    b2 = vector2[0][1] - m2 * vector2[0][0]

        ##Where the lines crossing: x1 = x2 and y1 = y2 so
        ##
        ##y = m1*x + b1;
        ##y = m2*x + b2;
        ##
        ##m1*x + b1 = m2*x + b2;
        ##x*( m1 - m2 ) = b2 - b1;
        ##
        ##so
        ##
        ##x = ( b2 - b1 ) / ( m1 - m2 );
        ##y = m1 * x + b1;
    try:
            cx = (b2-b1) / (m1-m2)
            #cy = m1 * cx + b1 
    except ZeroDivisionError:
            # these are either parallel lines or the same line
            # find out which and return proper value
            return False
    if not(vector1[0][0] < cx <= vector1[1][0]):
            return False
    else:
            return True
    

def int_test():
    p1 = [0.0, 0.0]
    p2 = [1.0, 1.0]
    p3 = [0.0,1.0]
    p4 = [1.0, 0.0]

    for i in range(10000):
        numint(p1,p2,p3,p4)
        intx(p1,p2,p3,p4)
        intersection([p1,p2],[p3,p4])
import itertools
def moving_average(iterable, n=3):
    # moving_average([40, 30, 50, 46, 39, 44]) --> 40.0 42.0 45.0 43.0
    # http://en.wikipedia.org/wiki/Moving_average
    it = iter(iterable)
    d = deque(itertools.islice(it, n-1))
    d.appendleft(0)
    s = sum(d)
    for elem in it:
        s += elem - d.popleft()
        d.append(elem)
    return s / float(n)

def moving_avg_test():
    for i in range(5000):
        moving_average(range(1000), len(range(1000)))
        movingAverage(range(1000), len(range(1000)))
        average(range(1000))
import std
def std_dev_test2():
    a = []
    for i in range(1000):
        a.append(float(i))
    for i in range(1000):
        numpy.std(a)
        std.func(a)

def __main__():
    LRU_test()

if __name__ == "__main__":
    LRU_test()

def minus(timestamp,duration):
    """
    timestamp is of type datetime.datetime
    duration is of type datetime.timedelta
    timestamp-duration will result in a type of datetime.datetime
    
    Calculates timestamp - duration in trading day hours.
    """
    startTime = timestamp-duration
    ms = MarketState()
    sameDayMarketOpen = datetime.datetime(timestamp.year, \
                                                   timestamp.month, \
                                                   timestamp.day, \
                                                   8, 30, 0, 0)
    
    if not ms.istradingday(timestamp):
        raise Exception
    if (startTime >= sameDayMarketOpen) :
        return startTime
    else:
        startTime = timestamp - datetime.timedelta(days=1)
        sameDayStartToTimeStamp = datetime.timedelta(\
            hours = timestamp.hour, \
            minutes = timestamp.minute, \
            seconds=timestamp.second, \
            microseconds=timestamp.microsecond) \
            - datetime.timedelta(hours=8,minutes=30)
        left_to_subtract = duration - sameDayStartToTimeStamp
        stockMarketDayDuration = datetime.timedelta(hours=6,minutes=30,seconds = 0, microseconds=0)
        while True:
            if ms.istradingday(startTime):
                if left_to_subtract <=stockMarketDayDuration:
                    startTime = datetime.datetime(startTime.year, startTime.month, startTime.day, 15, 0, 0, 0)
                    startTime = startTime - left_to_subtract
                    break
                sameDayStartToTimeStamp = sameDayStartToTimeStamp + stockMarketDayDuration
                left_to_subtract = duration - sameDayStartToTimeStamp
            startTime = startTime - datetime.timedelta(days=1)
        return startTime

def datetime_to_unixtime(a):
    return time.mktime(a.timetuple()) + a.microsecond/1000000.0

def time_based_moving_average_append(seq, value, time, unix_time):
    while True:
        if len(seq["time"]) == 0 or seq["time"][0] >= unix_time:
            break
        if seq["time"][0] < unix_time:
            seq["time"].popleft()
            seq["price"].popleft()

    seq["time"].append(time)
    seq["price"].append(value)
