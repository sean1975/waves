import webapp2
import urllib2
import urllib
import json
from operator import itemgetter
import os
import jinja2
import logging
import time
from datetime import datetime, timedelta
import re


class ForecastDataCrawler(webapp2.RequestHandler):

    def getWavesData(self, debug=False, ttl=300):
        app = webapp2.get_app()
        forecast_data = app.registry.get('forecast_data')
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
        app.registry['forecast_data'] = forecast_data
        return forecast_data


    def query(self):
        url = 'http://www.seabreeze.com.au/graphs/qld2.asp'

        # send HTTP request
        response = urllib2.urlopen(url)
        assert response.code == 200
        
        return response.read()
    
    
    ''' Extract datetime.now in a method so that it can be mocked
        in unit test without affecting other class methods of datetime '''
    def now(self):
        return datetime.now()
    
    
    def string2dict(self, response):
        # extract waves data from var jsonGraphsData in javascript embedded in html
        match = re.search("^var jsonGraphsData = (.*);\s*$", response, re.MULTILINE)
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
        for i in xrange(58, len(response_array), 4):
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


    def render(self, forecast_data):
        if forecast_data is None:
            self.abort(500)
        return json.dumps(forecast_data, indent=4, separators=(',', ': '))
    
    
    def get(self):
        # get waves data from www.seabreeze.com.au
        debug = self.request.get('debug')
        if debug is not None and debug == 'on':
            forecast_data = self.getWavesData(debug=True)
        else:
            forecast_data = self.getWavesData(debug=False)
        
        self.response.headers['Content-Type'] = 'text/plain'
        result_page = self.render(forecast_data)
        self.response.write(result_page)


class HistoricalDataCrawler(webapp2.RequestHandler):
    
    def getWavesData(self, debug=False, ttl=300):
        app = webapp2.get_app()
        historical_data = app.registry.get('historical_data')
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
                
        historical_data['time'] = time.time()
        historical_data['records'] = sorted(records, key=itemgetter("_id"))
        historical_data['debug'] = query_log
        app.registry['historical_data'] = historical_data
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


    def render(self, historical_data):
        if historical_data is None:
            self.abort(500)
        return json.dumps(historical_data, indent=4, separators=(',', ': '))
     
     
    def get(self):
        # get waves data from QLD website
        debug = self.request.get('debug')
        if debug is not None and debug == 'on':
            historical_data = self.getWavesData(debug=True)
        else:
            historical_data = self.getWavesData(debug=False)
        
        self.response.headers['Content-Type'] = 'text/plain'
        result_page = self.render(historical_data)
        self.response.write(result_page)
 
    
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(webapp2.RequestHandler):
        
    def render(self, historical_data, forecast_data):
        forecast = forecast_data.get('records')
        records = historical_data.get('records')
        debug = historical_data.get('debug')
        if records is None:
            self.abort(500)
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = { 'forecast': forecast, 'records': records, 'debug': debug }
        return template.render(template_values)
                                    

    def get(self):
        # call HistoricalDataCrawler to get waves data from QLD website
        historical_crawler = HistoricalDataCrawler(self.request, self.response)
        forecast_crawler = ForecastDataCrawler(self.request, self.response)

        debug = self.request.get('debug')
        if debug is not None and debug == 'on':
            historical_data = historical_crawler.getWavesData(debug=True)
            forecast_data = forecast_crawler.getWavesData(debug=True)
        else:
            historical_data = historical_crawler.getWavesData(debug=False, ttl=30*60)
            forecast_data = forecast_crawler.getWavesData(debug=False, ttl=30*60)
        
        # print the result
        # fields = [ _id, Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hsig, Hmax, Tp, Tz, SST, Direction, _full_count, rank ]
        result_page = self.render(historical_data, forecast_data)
        self.response.write(result_page)
            
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/data/historical', HistoricalDataCrawler),
    ('/data/forecast', ForecastDataCrawler)
], debug=True)