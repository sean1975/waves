from waves import MainPage

import unittest
import mock
from mock.mock import MagicMock
import webapp2
import urllib
import json
import httplib


class MockResponse():
    code = 500
    data = None
    
    def __init__(self, code, data):
        self.code = code
        self.data = data
        
    def read(self):
        return self.data.read()
    
    
class WavesTest(unittest.TestCase):
        
    def return_by_offset_value(self, url, data):
        parameters = json.loads(urllib.unquote(data))
        if 'offset' in parameters:
            filename = "test_response_offset" + parameters['offset'] + ".json"
        else:
            filename = "test_response.json"
        return MockResponse(200, open(filename))

    @mock.patch('waves.urllib2')
    def testQuery(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = MainPage()
        response = page.query()
        self.assertTrue(len(response) > 0, "Failed to get waves data")
        
    def testString2Dict(self):
        fd_response_string = open("test_response_string.json");
        response = fd_response_string.read()
        page = MainPage()
        result = page.string2dict(response)
        self.assertTrue(len(result["records"]) == 100)
        fd_response_string.close();
               
    @mock.patch('waves.urllib2')
    def testGetWavesData(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = MainPage()
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        for i in range(1, len(records)):
            self.assertGreater(records[i]["_id"], records[i-1]["_id"], "Records are not sorted by id")

    @mock.patch('waves.urllib2')
    def testGetWavesDataDebug(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = MainPage()
        query_log = page.getWavesData(debug=True).get('debug')
        self.assertTrue(len(query_log) == 4)
    
    @mock.patch('waves.urllib2')
    def testGetWavesDataCache(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = MainPage()
        app = webapp2.get_app()
        app.registry['historical_data'] = None
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        self.assertEqual(4, mock_urllib2.urlopen.call_count)
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        self.assertEqual(4, mock_urllib2.urlopen.call_count)

    @mock.patch('waves.urllib2')
    def testHTTPException(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = httplib.HTTPException("Deadline exceeded while waiting for HTTP response from URL: https://data.qld.gov.au/api/action/datastore_search"))
        page = MainPage()
        app = webapp2.get_app()
        historical_data = dict()
        historical_data['time'] = 1463236200
        historical_data['records'] = [{'_id': 3202}]
        app.registry['historical_data'] = historical_data
        records = page.getWavesData().get('records')
        self.assertIsNotNone(records, "results are empty")
        self.assertTrue(records[0]["_id"] == 3202)

    def testRender(self):
        historical_data = dict()
        historical_data['records'] = [{
            "Hmax": "1.4500000000000000",
            "SiteNumber": "9",
            "Hsig": "0.7131000000000000",
            "Latitude": "-16.7335700000",
            "_full_count": "350",
            "Seconds": "1463236200",
            "DateTime": "2016-05-15T00:30:00",
            "Longitude": "145.7089900000",
            "_id": 3149,
            "SST": "26.53",
            "Site": "Cairns",
            "rank": 0.0573088,
            "Tz": "3.2260000000000000",
            "Tp": "3.5700000000000000",
            "Direction": "109.473037217659"
        }]
        historical_data['debug'] = []

        page = MainPage()
        page.render(historical_data)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
