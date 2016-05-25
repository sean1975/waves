from waves import MainPage

import unittest
import mock


class MockResponse():
    code = 500
    data = None
    
    def __init__(self, code, data):
        self.code = code
        self.data = data
        
    def read(self):
        return self.data.read()
    
    
class WavesTest(unittest.TestCase):
        
    @mock.patch('waves.urllib2')
    def testQuery(self, mock_urllib2):
        fd = open("test_response.json") 
        mock_urllib2.urlopen.return_value = MockResponse(200, fd)
        page = MainPage()
        response = page.query()
        self.assertTrue(len(response) > 0, "Failed to get waves data")
        fd.close()
        
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
        fd = open("test_response.json") 
        mock_urllib2.urlopen.return_value = MockResponse(200, fd)
        page = MainPage()
        result = page.getWavesData()
        self.assertTrue(result["records"][0]["_id"] == 3202)
        #self.assertTrue(len(result["records"]) == 356)        
        fd.close()
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()