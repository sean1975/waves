import webapp2
import urllib2
import urllib
import json
import os
import jinja2
import logging
import time
from datetime import datetime, timedelta
import re
from HTMLParser import HTMLParser
from collections import Counter


class AbstractDataCrawler(webapp2.RequestHandler):
    ''' Base class for crawling data '''
    data_name = None
    ttl = 300

    
    def __init__(self, data_name=None, request=None, response=None):
        super(AbstractDataCrawler, self).__init__(request=request, response=response)
        self.data_name = data_name
        

    def getCacheData(self):
        app = webapp2.get_app()
        return app.registry.get(self.data_name)
        
        
    def setCacheData(self, cache_data):
        app = webapp2.get_app()
        app.registry[self.data_name] = cache_data

        
    def getWavesData(self, debug=False, ttl=300):
        forecast_data = self.getCacheData()
        if forecast_data is None:
            forecast_data = dict()
        elif debug == False:
            timestamp = forecast_data['time']
            if timestamp is not None and time.time() < timestamp + ttl:
                return forecast_data
            
        query_log = []
        # query all waves statistics for Cairns
        try:
            response = self.query()
        except Exception as exception:
            logging.warn(exception)
            return forecast_data
        if debug == True:
            query_log.append(response)

        # load HTTP response into a json dictionary
        records = self.string2dict(response)

        forecast_data['time'] = time.time()
        forecast_data['records'] = records
        forecast_data['debug'] = query_log
        self.setCacheData(forecast_data)
        return forecast_data


    ''' Extract datetime.now in a method so that it can be mocked
        in unit test without affecting other class methods of datetime '''
    def now(self):
        return datetime.now()
    
    
    def render(self, forecast_data):
        if forecast_data is None:
            self.abort(500)
        return json.dumps(forecast_data, indent=4, separators=(',', ': '))
    
    
    def get(self):
        # get waves data from www.seabreeze.com.au
        if self.request and self.request.get('debug') == 'on':
            debug = True
        else:
            debug = False
        forecast_data = self.getWavesData(debug=debug)
                    
        result_page = self.render(forecast_data)
        if self.response:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write(result_page)


class SeabreezeDataCrawler(AbstractDataCrawler):
    ''' Data crawler to get forecast data from www.seabreeze.com.au '''
    
    def __init__(self, request=None, response=None):
        super(SeabreezeDataCrawler, self).__init__(data_name='seabreeze_data', request=request, response=response)
        
    
    def query(self):
        url = 'http://www.seabreeze.com.au/graphs/qld2.asp'

        # send HTTP request
        response = urllib2.urlopen(url)
        assert response.code == 200
        
        return response.read()
    
    
    def string2dict(self, response):
        # extract waves data from var jsonGraphsData in javascript embedded in html
        match = re.search("^var json\s*=\s*(.*);\s*$", response, re.MULTILINE)
        if not match:
            return None
        
        records = []
        response_dict = json.loads(match.group(1))
        response_array = response_dict['data'][0].split(',')
        # start_date in Cairns timezone (AEST)
        start_date = datetime.strptime(response_array[12], '%Y%m%d%H%M')
        # Cairns timezone +10
        tzdiff = timedelta(hours=10)
        # now in Cairns timezone (AEST)
        now = self.now()+tzdiff
        index_start = int(response_array[11])
        index_step = int(response_array[10])
        for i in xrange(index_start, len(response_array), index_step):
            hours = float(response_array[i]) / 100
            timediff = timedelta(hours=hours)
            dt = start_date + timediff
            # out-of-dated forecast
            if dt < now:
                continue
            record = dict()
            # record['DateTime'] is in Cairns timezone (AEST)
            record['DateTime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            # record['Seconds'] is Epoch time in UTC
            record['Seconds'] = int((dt - tzdiff - datetime(1970,1,1)).total_seconds())
            record['Wind'] = response_array[i+1]
            record['Direction'] = response_array[i+2]
            record['Waves'] = response_array[i+3]
            records.append(record)
        return records


# create a subclass and override the handler methods
class BureauDataParser(HTMLParser):
    content = False
    path = []
    issued_time = None
    tzdiff = timedelta(hours=10)
    records = []
    current_record = None
    field_name = None
    
    
    def get_records(self):
        return self.records
    
    
    ''' Extract datetime.now in a method so that it can be mocked
        in unit test without affecting other class methods of datetime '''
    def now(self):
        return datetime.now()

    
    def handle_starttag(self, tag, attrs):
        if self.content == True:
            self.path.append((tag, attrs))
            return
        if tag != 'div':
            return
        for attr in attrs:
            (name, value) = attr
            if name != 'id':
                continue
            if value != 'content':
                continue
            # Found entity <div id='content'>
            self.content = True
            self.path = []
            self.issued_time = None
            self.records = []
            self.current_record = None
            self.field_name = None
            return
        

    def handle_endtag(self, tag):
        if self.content != True:
            return
        if len(self.path) > 0:
            self.path.pop()
        else:
            self.content = False


    def handle_data(self, data):
        if self.content != True:
            return
        if len(data.strip()) == 0:
            return
        if len(self.path) < 2:
            return
        #<div class='marine'>
        if self.path[0][0] != 'div' or self.path[0][1][0][0] != 'class' or self.path[0][1][0][1] != 'marine':
            return
        #<div class='marine'><p class='date'>
        if self.path[1][0] == 'p' and self.path[1][1][0][0] == 'class' and self.path[1][1][0][1] == 'date':
            if len(self.path) > 2:
                #<div class='marine'><p class='date'><strong>
                return
            # Forecast issued/updated at 3:50 pm EST on Monday 20 June 2016.
            match = re.search("(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) (?:\d)+ (?:\w)+ (?:\d)+", data)
            if match:
                self.issued_time = datetime.strptime(match.group(0), '%A %d %B %Y')
            else:
                logging.error('Failed to parse issued date from "' + data + '"')
            return
        #<div class='marine'><div class='day'>
        if self.path[1][0] != 'div' or self.path[1][1][0][0] != 'class' or self.path[1][1][0][1] != 'day':
            return
        if len(self.path) < 3:
            return
        #<div class='marine'><div class='day'><h2>
        if self.path[2][0] == 'h2':
            self.current_record = []
            for i in xrange(0,4):
                self.current_record.append(dict())
            dt = None
            if len(self.records) == 0:
                dt = self.issued_time.replace(hour=0, minute=0, second=0)
            else:
                dt = datetime.strptime(data, '%A %d %B').replace(year=self.issued_time.year, hour=0, minute=0, second=0)
            for i in xrange(0, 4):
                dt += timedelta(hours=6)
                self.current_record[i]['DateTime'] = dt.__str__()
                self.current_record[i]['Seconds'] = int((dt - self.tzdiff - datetime(1970,1,1)).total_seconds())
            return
        if len(self.path) < 4:
            return
        #<div class='marine'><div class='day'><dl class='marine'>
        if self.path[2][0] != 'dl' or self.path[2][1][0][0] != 'class' or self.path[2][1][0][1] != 'marine':
            return
        #<div class='marine'><div class='day'><dl class='marine'><dt>
        #<div class='marine'><div class='day'><dl class='marine'><dd>
        if self.path[3][0] == 'dt':
            self.field_name = data
            return
        if self.path[3][0] == 'dd':
            if self.field_name == 'Seas':
                match = re.search("^(?P<modifier>Around|Below)?\s?(?P<from>\d(?:\.\d)?)(?: to (?P<to>\d+(?:\.\d)?))? metre(?:s)?(?:, (?:increasing|decreasing) to (?P<from2>\d(?:\.\d)?)(?: to (?P<to2>\d+(?:\.\d)?))? metre(?:s)? during the (?P<during>morning|afternoon|evening))?.*?", data)
                if match:
                    seas_dict = match.groupdict()
                    seas = 0.0
                    if seas_dict['from'] == None:
                        logging.error('Failed to parse wave height from "' + data + '"')
                    elif seas_dict['to'] != None:
                        seas = (float(seas_dict['from']) + float(seas_dict['to'])) / 2.0
                    else:
                        seas = float(seas_dict['from'])
                    if seas_dict['modifier'] == 'Below':
                        seas *= 0.8;
                    for i in xrange(0,4):
                        self.current_record[i][self.field_name] = seas
                        
                    # increase/decrease seas
                    if seas_dict['from2'] != None:
                        if seas_dict['to2'] != None:
                            seas = (float(seas_dict['from2']) + float(seas_dict['to2'])) / 2.0
                        else:
                            seas = float(seas_dict['from2'])
                        if seas_dict['during'] == 'morning':
                            index = 0
                        elif seas_dict['during'] == 'afternoon':
                            index = 1
                        elif seas_dict['during'] == 'evening':
                            index = 2
                        for i in xrange(index, 4):
                            self.current_record[i][self.field_name] = seas
                else:
                    logging.error('Failed to parse wave height from "' + data + '"')
                    for i in xrange[0:4]:
                        self.current_record[i][self.field_name] = data
            elif self.field_name == 'Waves':
                match = re.search("^Seas (:?and swell )?exceeding (?P<waves>\d+)m\.?.*?", data)
                if match:
                    seas_dict = match.groupdict()
                    seas = float(seas_dict['waves'])
                    for i in xrange(0,4):
                        self.current_record[i]["Seas"] = seas
                else:
                    logging.error('Failed to parse wave height from "' + data + '"')
                    for i in xrange[0:4]:
                        self.current_record[i]["Seas"] = data   
            elif self.field_name == 'Winds':
                match = re.search("^\D*(?P<from>\d+)(?: to (?P<to>\d+))? knots(?: (?:increasing|decreasing) to (?:about )?(?P<from2>\d+)(?: to (?P<to2>\d+))? knots (?:during|before|in) (?:the )?(?P<during>morning|dawn|afternoon|evening|late evening))?.*?", data)
                if match:
                    winds_dict = match.groupdict()
                    winds = 0.0
                    if winds_dict['from'] == None:
                        logging.error('Failed to parse wind speed from "' + data + '"')
                    elif winds_dict['to'] != None:
                        winds = (float(winds_dict['from']) + float(winds_dict['to'])) / 2.0
                    else:
                        winds = float(winds_dict['from'])
                    for i in xrange(0,4):
                        self.current_record[i][self.field_name] = winds
                        
                    # increase/decrease winds
                    if winds_dict['from2'] != None:
                        if winds_dict['to2'] != None:
                            winds = (float(winds_dict['from2']) + float(winds_dict['to2'])) / 2.0
                        else:
                            winds = float(winds_dict['from2'])
                        if winds_dict['during'] == 'morning' or winds_dict['during'] == 'dawn':
                            index = 0
                        elif winds_dict['during'] == 'afternoon':
                            index = 1
                        elif winds_dict['during'] == 'evening' or winds_dict['during'] == 'late evening':
                            index = 2
                        for i in xrange(index, 4):
                            self.current_record[i][self.field_name] = winds
                else:
                    logging.error('Failed to parse wind speed from "' + data + '"')               
                    self.current_record[self.field_name] = data
            else:
                for i in xrange(0,4):
                    self.current_record[i][self.field_name] = data
            if len(self.path[3]) > 1 and len(self.path[3][1]) > 0 and self.path[3][1][0][0] == 'class' and self.path[3][1][0][1] == 'last':
                now = self.now()
                for record in self.current_record:
                    dt = datetime.fromtimestamp(record['Seconds'])
                    if dt < now:
                        continue
                    self.records.append(record)
                self.current_record = None
            self.field_name = None
            return       
        
        
class BureauDataCrawler(AbstractDataCrawler):
    ''' Data crawler to get forecast data from bureau of meteorology www.bom.gov.au '''
    
    def __init__(self, request=None, response=None):
        super(BureauDataCrawler, self).__init__(data_name='bureau_data', request=request, response=response)
        
    
    def query(self):
        url = 'http://www.bom.gov.au/qld/forecasts/cairns-coast.shtml'

        # send HTTP request as a browser. Otherwise www.bom.gov.au would reject the request
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        response = opener.open(url)
        assert response.code == 200
        
        return response.read()
    
    
    def string2dict(self, response):
        parser = BureauDataParser()
        parser.feed(response)
        return parser.get_records()


class HistoricalDataCrawler(AbstractDataCrawler):
    ''' Data crawler to get historical data from data.qld.gov.au '''
    
    def __init__(self, request=None, response=None):
        super(HistoricalDataCrawler, self).__init__(data_name='historical_data', request=request, response=response)

    
    def getWavesData(self, debug=False, ttl=300):
        historical_data = self.getCacheData()
        if historical_data is None:
            historical_data = dict()
        elif debug == False:
            historical_data['debug'] = []
            timestamp = historical_data['time']
            if timestamp is not None and time.time() < timestamp + ttl:
                return historical_data
            
        query_log = []
        # query all waves statistics for Cairns
        try:
            response = self.query()
        except Exception as exception:
            logging.warn(exception)
            return historical_data
        if debug == True:
            query_log.append(response)
        
        # load HTTP response into a json dictionary
        result = self.string2dict(response)
        
        # query may be successiful but no records are returned
        if 'records' not in result or 'total' not in result:
            return historical_data
        
        records = result['records']
        total = result['total']        
        count = len(records)
        offset = 0
        
        # continue query with offset until all waves statistics are returned
        while count < total:
            offset += 100
            try:
                response = self.query(str(offset))
            except Exception as exception:
                logging.warn(exception)
                return historical_data
            if debug == True:
                query_log.append(response)
                
            result = self.string2dict(response)
            count += len(result['records'])
            records += result['records']
        
        # waves statistics from data.qld.gov.au could be duplicated
        deduped_records = []
        dedupe_counter = Counter()
        for i in range(0, len(records)):
            seconds = records[i]['Seconds']
            dedupe_counter[seconds] += 1
            if dedupe_counter[seconds] == 1:
                deduped_records.append(records[i])
        
        historical_data['time'] = time.time()
        # records['_id'] is not reliable, use records['Seconds'] for sorting instead
        historical_data['records'] = sorted(deduped_records, cmp=lambda x,y: cmp(int(x['Seconds']), int(y['Seconds'])))
        historical_data['debug'] = query_log
        self.setCacheData(historical_data)
        return historical_data
        
        
    def query(self, offset=None):
        # data API: https://data.qld.gov.au/dataset/coastal-data-system-near-real-time-wave-data/resource/2bbef99e-9974-49b9-a316-57402b00609c
        url = 'https://data.qld.gov.au/api/action/datastore_search'
    
        # query string
        parameters = {'resource_id': '2bbef99e-9974-49b9-a316-57402b00609c', 'q': 'cairns'}
        if offset is not None:
            parameters['offset'] = offset
        data = urllib.quote(json.dumps(parameters))

        # send HTTP request
        response = urllib2.urlopen(url, data)
        assert response.code == 200
        
        return response.read()
    

    def string2dict(self, response):
        response_dict = json.loads(response)
        assert response_dict['success'] is True
        return response_dict['result']
 
    
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(webapp2.RequestHandler):
        
    def render(self, historical_data, forecast_data, bureau_data):
        bureau = bureau_data.get('records')
        forecast = forecast_data.get('records')
        records = historical_data.get('records')
        debug = historical_data.get('debug')
        if records is None:
            self.abort(500)
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = { 'forecast2': bureau, 'forecast': forecast, 'records': records, 'debug': debug }
        return template.render(template_values)
                                    

    def get(self):
        # call HistoricalDataCrawler to get waves data from QLD website
        historical_crawler = HistoricalDataCrawler(self.request, self.response)
        forecast_crawler = SeabreezeDataCrawler(self.request, self.response)
        bureau_crawler = BureauDataCrawler(self.request, self.response)

        debug = self.request.get('debug')
        if debug is not None and debug == 'on':
            historical_data = historical_crawler.getWavesData(debug=True)
            forecast_data = forecast_crawler.getWavesData(debug=True)
            bureau_data = bureau_crawler.getWavesData(debug=True)
        else:
            historical_data = historical_crawler.getWavesData(debug=False, ttl=30*60)
            forecast_data = forecast_crawler.getWavesData(debug=False, ttl=30*60)
            bureau_data = bureau_crawler.getWavesData(debug=False, ttl=30*60)
        
        # print the result
        # fields = [ _id, Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hsig, Hmax, Tp, Tz, SST, Direction, _full_count, rank ]
        result_page = self.render(historical_data, forecast_data, bureau_data)
        self.response.write(result_page)
            
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/data/historical', HistoricalDataCrawler),
    ('/data/seabreeze', SeabreezeDataCrawler),
    ('/data/bureau', BureauDataCrawler)
], debug=True)
