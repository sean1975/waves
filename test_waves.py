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
    def testGetWavesData(self, mock_urllib2):
        fd = open("test_response.json")
        mock_urllib2.urlopen.return_value = MockResponse(200, fd)
        page = MainPage()
        response = page.getWavesData()
        self.assertTrue(len(response) > 0, "Failed to get waves data")
        fd.close()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()