from waves import MainPage

import unittest
import mock
from mock.mock import MagicMock
import urllib
import json


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
        self.assertTrue(result["records"][0]["_id"] == 3148)
        self.assertTrue(len(result["records"]) == 100)
        fd_response_string.close();
               
    @mock.patch('waves.urllib2')
    def testGetWavesData(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = MainPage()
        records = page.getWavesData()
        self.assertTrue(records[0]["_id"] == 3202)
        self.assertTrue(len(records) == 356)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
