import webapp2
import urllib2
import urllib
import json
from operator import itemgetter
import os
import jinja2
import logging
from httplib import HTTPException


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(webapp2.RequestHandler):
    debug = None
    http_cache = None
    
    def getWavesData(self):
        self.debug = []
        # query all waves statistics for Cairns
        response = self.query()
        if response is None:
            return self.http_cache
        
        # load HTTP response into a json dictionary
        result = self.string2dict(response)
        
        records = result['records']
        total = result['total']        
        count = len(records)
        offset = 0
        
        # continue query with offset until all waves statistics are returned
        while count < total:
            offset += 100
            response = self.query(str(offset))
            if response is None:
                return self.http_cache
            result = self.string2dict(response)
            count += len(result['records'])
            records += result['records']
        
        self.http_cache = records
        return records
        
        
    def query(self, offset=None):
        # data API: https://data.qld.gov.au/dataset/coastal-data-system-near-real-time-wave-data/resource/2bbef99e-9974-49b9-a316-57402b00609c
        url = 'https://data.qld.gov.au/api/action/datastore_search'
    
        # query string
        parameters = {'resource_id': '2bbef99e-9974-49b9-a316-57402b00609c', 'q': 'cairns'}
        if offset is not None:
            parameters['offset'] = offset
        data = urllib.quote(json.dumps(parameters))

        # send HTTP request
        content = None
        try:
            response = urllib2.urlopen(url, data)
            assert response.code == 200
        
            content = response.read()
            if self.request and self.request.get('debug') == 'on':
                self.debug.append(content)
            
        except HTTPException as httpexception:
            logging.warn(httpexception)
            if self.request and self.request.get('debug') == 'on':
                self.debug.append(httpexception)

        return content
        
    
    def render(self, records):
        if records is None:
            self.abort(500)
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = { 'records': records, 'debug': self.debug }
        self.response.write(template.render(template_values))
                                    

    def string2dict(self, response):
        response_dict = json.loads(response)
        assert response_dict['success'] is True
        records = sorted(response_dict['result']['records'], key=itemgetter("_id"))
        response_dict['result']['records'] = records;
        return response_dict['result']


    def get(self):
        # get waves data from QLD website
        records = self.getWavesData()
        
        # print the result
        # fields = [ _id, Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hsig, Hmax, Tp, Tz, SST, Direction, _full_count, rank ]
        self.render(records)
            
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)