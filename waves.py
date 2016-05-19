import webapp2
import urllib2
import urllib
import json

class MainPage(webapp2.RequestHandler):
    def get(self):
        # query all waves statistics for Cairns
        data_string = urllib.quote(json.dumps({'resource_id': '2bbef99e-9974-49b9-a316-57402b00609c', 'q': 'cairns'}))
        # data API: https://data.qld.gov.au/dataset/coastal-data-system-near-real-time-wave-data/resource/2bbef99e-9974-49b9-a316-57402b00609c
        url = 'https://data.qld.gov.au/api/action/datastore_search'
        # send HTTP request
        response = urllib2.urlopen(url, data_string)
        assert response.code == 200
        # load HTTP response into a json dictionary
        response_dict = json.loads(response.read());
        assert response_dict['success'] is True
        # print the result
        result = response_dict['result']
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(result)
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)