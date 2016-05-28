import webapp2
import urllib2
import urllib
import json
import logging
from operator import itemgetter
import os
import jinja2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(webapp2.RequestHandler):
    def getWavesData(self):
        # query all waves statistics for Cairns
        response = self.query()
        
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
            result = self.string2dict(response)
            count += len(result['records'])
            records += result['records']
        
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
        response = urllib2.urlopen(url, data)
        assert response.code == 200
        
        return response.read()
        
    
    def render(self, records):
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = { 'records': records }
        self.response.write(template.render(template_values))
                                    

    def string2dict(self, response):
        response_dict = json.loads(response)
        logging.info(json.dumps(response_dict, indent=4, separators={",", ": "}))
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