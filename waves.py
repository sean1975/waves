import webapp2
import urllib2
import urllib
import json
from operator import itemgetter
import os
import jinja2
import logging
import time


class HistoricalDataCrawler(webapp2.RequestHandler):
    
    def getWavesData(self, debug=False):
        app = webapp2.get_app()
        historical_data = app.registry.get('historical_data')
        if historical_data is None:
            historical_data = dict()
        elif debug == False:
            timestamp = historical_data['time']
            if timestamp is not None and time.time() < timestamp + 5 * 60:
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
        app = webapp2.get_app();
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
        
    def render(self, historical_data):
        records = historical_data.get('records')
        debug = historical_data.get('debug')
        if records is None:
            self.abort(500)
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = { 'records': records, 'debug': debug }
        return template.render(template_values)
                                    

    def get(self):
        # call HistoricalDataCrawler to get waves data from QLD website
        crawler = HistoricalDataCrawler(self.request, self.response)

        debug = self.request.get('debug')
        if debug is not None and debug == 'on':
            historical_data = crawler.getWavesData(debug=True)
        else:
            historical_data = crawler.getWavesData(debug=False)
        
        # print the result
        # fields = [ _id, Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hsig, Hmax, Tp, Tz, SST, Direction, _full_count, rank ]
        result_page = self.render(historical_data)
        self.response.write(result_page)
            
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/data/historical', HistoricalDataCrawler)
], debug=True)