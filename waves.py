import webapp2
import urllib2
import urllib
import json
import logging
from operator import itemgetter

class MainPage(webapp2.RequestHandler):
    def getWavesData(self):
        # query all waves statistics for Cairns
        response = self.query()
        
        # load HTTP response into a json dictionary
        result = self.string2dict(response)
        
        return result
        
        
    def query(self):
        # data API: https://data.qld.gov.au/dataset/coastal-data-system-near-real-time-wave-data/resource/2bbef99e-9974-49b9-a316-57402b00609c
        url = 'https://data.qld.gov.au/api/action/datastore_search'
    
        # query string
        data = urllib.quote(json.dumps({'resource_id': '2bbef99e-9974-49b9-a316-57402b00609c', 'q': 'cairns'}))

        # send HTTP request
        response = urllib2.urlopen(url, data)
        assert response.code == 200
        
        return response.read()
        
    
    def render(self, fields, records):
        self.response.headers['Content-Type'] = 'text/plain'
        for field in fields :
            self.response.write(field['id'] + "\t")
        self.response.write("\n")
        
        for record in records :
            for field in fields :
                self.response.write(record[field['id']]);
                self.response.write("\t")
            self.response.write("\n")
                                    

    def string2dict(self, response):
        response_dict = json.loads(response)
        logging.info(json.dumps(response_dict, indent=4, separators={",", ": "}))
        assert response_dict['success'] is True
        records = sorted(response_dict['result']['records'], key=itemgetter("_id"))
        response_dict['result']['records'] = records;
        return response_dict['result']


    def get(self):
        # get waves data from QLD website
        result = self.getWavesData()
        
        # print the result
        # fields = [ _id, Site, SiteNumber, Seconds, DateTime, Latitude, Longitude, Hsig, Hmax, Tp, Tz, SST, Direction, _full_count, rank ]
        fields = result['fields']
        records = result['records'];
        self.render(fields, records)
            
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)