from waves import MainPage, HistoricalDataCrawler, SeabreezeDataCrawler, BureauDataCrawler

import unittest
import mock
from mock.mock import MagicMock
import urllib
import json
import httplib
from datetime import datetime


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

    def return_duplicate_records(self, url, data):
        parameters = json.loads(urllib.unquote(data))
        if 'offset' in parameters:
            filename = "test_response_duplicate_offset" + parameters['offset'] + ".json"
        else:
            filename = "test_response_duplicate.json"
        return MockResponse(200, open(filename))

    @mock.patch('waves.urllib2')
    def testQuery(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = HistoricalDataCrawler()
        response = page.query()
        self.assertTrue(len(response) > 0, "Failed to get waves data")
        
    def testString2Dict(self):
        fd_response_string = open("test_response_string.json");
        response = fd_response_string.read()
        page = HistoricalDataCrawler()
        result = page.string2dict(response)
        self.assertTrue(len(result["records"]) == 100)
        fd_response_string.close();
               
    @mock.patch('waves.urllib2')
    def testGetWavesData(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = HistoricalDataCrawler()
        page.setCacheData(None)
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        for i in range(1, len(records)):
            self.assertGreater(records[i]["Seconds"], records[i-1]["Seconds"], "Records are not sorted by time")

    @mock.patch('waves.urllib2')
    def testGetWavesDataDebug(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = HistoricalDataCrawler()
        query_log = page.getWavesData(debug=True).get('debug')
        self.assertTrue(len(query_log) == 4)
    
    @mock.patch('waves.urllib2')
    def testGetWavesDataCache(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_by_offset_value)
        page = HistoricalDataCrawler()
        page.setCacheData(None)
        # First time urllib2.urlopen() should be called
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        self.assertEqual(4, mock_urllib2.urlopen.call_count)
        # Second time urllib2.urlopen() should NOT be called
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 2873)
        self.assertTrue(len(records) == 334)
        self.assertEqual(4, mock_urllib2.urlopen.call_count)
        
    @mock.patch('waves.urllib2')
    def testHTTPException(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = httplib.HTTPException("Deadline exceeded while waiting for HTTP response from URL: https://data.qld.gov.au/api/action/datastore_search"))
        page = HistoricalDataCrawler()
        historical_data = dict()
        historical_data['time'] = 1463236200
        historical_data['records'] = [{'_id': 3202}]
        page.setCacheData(historical_data)
        records = page.getWavesData().get('records')
        self.assertIsNotNone(records, "results are empty")
        self.assertTrue(records[0]["_id"] == 3202)
       
    @mock.patch('waves.urllib2')
    def testGetWavesDataDuplicate(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(side_effect = self.return_duplicate_records)
        page = HistoricalDataCrawler()
        page.setCacheData(None)
        records = page.getWavesData().get('records')
        self.assertTrue(records[0]["_id"] == 5895)
        self.assertTrue(len(records) == 350)
        for i in range(1, len(records)):
            self.assertGreater(records[i]["Seconds"], records[i-1]["Seconds"], "Records are not sorted by time")

    @mock.patch('waves.urllib2')
    def testGetWavesDataEmpty(self, mock_urllib2):
        mock_urllib2.urlopen = MagicMock(return_value = MockResponse(200, open('test_response_empty.json')))
        page = HistoricalDataCrawler()
        page.setCacheData(None)
        records = page.getWavesData().get('records')
        self.assertIsNone(records)

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
        forecast_data = dict()
        forecast_data['records'] = [{
            "Wind": "22",
            "DateTime": "2016-06-14 23:30:00",
            "Direction": "ESE",
            "Seconds": 1465947000,
            "Waves": "3.01"
        }]
        bureau_data = dict()
        bureau_data['records'] = [{
            'Seconds': 1466401800,
            'Swell': 'Southeasterly around 1 metre outside the reef.',
            'DateTime': '2016-06-20 15:50:00',
            'Seas': 1.0,
            'Weather': 'Cloudy.',
            'Winds': 'Southeasterly 10 to 15 knots, reaching up to 20 knots offshore north of Cairns in the evening.'
        }]

        page = MainPage()
        page.render(historical_data, forecast_data, bureau_data)


    @mock.patch('waves.SeabreezeDataCrawler.now')
    def testString2DictSeabreezeData(self, mock_now):
        mock_now.return_value = datetime(2016, 6, 19, 0, 0, 0)
        fd_response_string = open("test_seabreeze.html")
        response = fd_response_string.read()
        page = SeabreezeDataCrawler()
        result = page.string2dict(response)
        self.assertTrue(len(result) == 119)
        record_Seconds = datetime.fromtimestamp(result[0]['Seconds'])
        record_DateTime = datetime.strptime(result[0]['DateTime'], '%Y-%m-%d %H:%M:%S')
        self.assertTrue(record_Seconds == record_DateTime)
        fd_response_string.close();
               

    @mock.patch('waves.BureauDataParser.now')
    def testString2DictBureauData(self, mock_now):
        mock_now.return_value = datetime(2016, 6, 20, 18, 30, 0)
        fd_response_string = open("test_bom.html")
        response = fd_response_string.read()
        page = BureauDataCrawler()
        result = page.string2dict(response)
        self.assertTrue(len(result) == 13)
        record_Seconds = datetime.fromtimestamp(result[0]['Seconds'])
        record_DateTime = datetime.strptime(result[0]['DateTime'], '%Y-%m-%d %H:%M:%S')
        self.assertTrue(record_Seconds == record_DateTime)
        fd_response_string.close();
        # Seas[0-3]: Below 1 metre.
        # Seas[4-7]: Below 1 metre.
        # Seas[8-11]: Below 1 metre, increasing to 1 to 2 metres during the morning.
        # Seas[12-15]: 1 to 1.5 metres, decreasing to 1 metre during the afternoon.
        fd_response_string = open("test_bom2.html")
        response = fd_response_string.read()
        result = page.string2dict(response)
        
        self.assertTrue(len(result) == 16)

        self.assertTrue(result[0]['Seas'] == 0.8)
        self.assertTrue(result[1]['Seas'] == 0.8)
        self.assertTrue(result[2]['Seas'] == 0.8)
        self.assertTrue(result[3]['Seas'] == 0.8)
        self.assertTrue(result[4]['Seas'] == 0.8)
        self.assertTrue(result[5]['Seas'] == 0.8)
        self.assertTrue(result[6]['Seas'] == 0.8)
        self.assertTrue(result[7]['Seas'] == 0.8)
        self.assertTrue(result[8]['Seas'] == 1.5)
        self.assertTrue(result[9]['Seas'] == 1.5)
        self.assertTrue(result[10]['Seas'] == 1.5)
        self.assertTrue(result[11]['Seas'] == 1.5)
        self.assertTrue(result[12]['Seas'] == 1.25)
        self.assertTrue(result[13]['Seas'] == 1.0)
        self.assertTrue(result[14]['Seas'] == 1.0)
        self.assertTrue(result[15]['Seas'] == 1.0)

        self.assertTrue(result[0]['Winds'] == 12.5)
        self.assertTrue(result[1]['Winds'] == 12.5)
        self.assertTrue(result[2]['Winds'] == 10)
        self.assertTrue(result[3]['Winds'] == 10)
        self.assertTrue(result[4]['Winds'] == 10)
        self.assertTrue(result[5]['Winds'] == 10)
        self.assertTrue(result[6]['Winds'] == 10)
        self.assertTrue(result[7]['Winds'] == 10)
        self.assertTrue(result[8]['Winds'] == 20)
        self.assertTrue(result[9]['Winds'] == 20)
        self.assertTrue(result[10]['Winds'] == 20)
        self.assertTrue(result[11]['Winds'] == 20)
        self.assertTrue(result[12]['Winds'] == 17.5)
        self.assertTrue(result[13]['Winds'] == 17.5)
        self.assertTrue(result[14]['Winds'] == 17.5)
        self.assertTrue(result[15]['Winds'] == 17.5)
        
        fd_response_string.close();

        fd_response_string = open("test_bom3.html")
        response = fd_response_string.read()
        result = page.string2dict(response)
        
        self.assertTrue(len(result) == 16)

        fd_response_string = open("test_bom4.html")
        response = fd_response_string.read()
        result = page.string2dict(response)
        
        self.assertTrue(len(result) == 16)
        
        self.assertTrue(result[8]['Seas'] == 4.0)
        self.assertTrue(result[9]['Seas'] == 4.0)
        self.assertTrue(result[10]['Seas'] == 4.0)
        self.assertTrue(result[11]['Seas'] == 4.0)
        self.assertTrue(result[12]['Seas'] == 8.0)
        self.assertTrue(result[13]['Seas'] == 8.0)
        self.assertTrue(result[14]['Seas'] == 8.0)
        self.assertTrue(result[15]['Seas'] == 8.0)
                                
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
