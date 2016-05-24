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
    fd = None
    
    def setUp(self):
        self.fd = open("test_response.json")
        
    def tearDown(self):
        self.fd.close
        
    @mock.patch('waves.urllib2')
    def testGetWavesData(self, mock_urllib2):
        mock_urllib2.urlopen.return_value = MockResponse(200, self.fd)
        page = MainPage()
        response = page.getWavesData()
        self.assertTrue(len(response) > 0, "Failed to get waves data")
        
    def testString2Dict(self):
        response = self.fd.read()
        page = MainPage()
        response_dict = page.string2dict(response)
        self.assertTrue(response_dict["result"]["records"][0]["_id"] == 3148)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()