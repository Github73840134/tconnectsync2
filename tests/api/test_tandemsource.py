#!/usr/bin/env python3

import datetime
import unittest
import urllib.parse
from unittest.mock import patch

from tconnectsync.api.tandemsource import TandemSourceApi


# Representative GET api/reports/bff/pumper/{pumperId} response, mirroring the
# structure of a real captured account response: one active pump with settings
# and one never-uploaded pump (null date/settings fields).
BFF_PUMPER = {
    "firstName": "Test",
    "lastName": "User",
    "name": "Test User",
    "dateOfBirth": "1990-01-01",
    "lowGlucoseThreshold": 70,
    "highGlucoseThreshold": 180,
    "country": "US",
    "pumps": [
        {
            "algorithm": "Control-IQ",
            "availableDataRange": {"start": "2021-05-06T12:31:19", "end": "2022-02-16T22:45:58"},
            "assignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "lastUploadDate": "2022-09-20T05:50:12Z",
            "maxDateOfEvents": "2022-02-16T22:45:58",
            "modelNumber": "1000354",
            "modelName": "t:slim X2™ Insulin Pump",
            "partNumber": "1011979",
            "serialNumber": "90556643",
            "softwareVersion": "7.8.0.0",
            "lastUploadClientType": "mobile_tconnect",
            "settings": {
                "id": "b7f931c8-63cd-44c9-86aa-56826f9057e5",
                "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
                "uploadedTimeStamp": "2022-09-10T21:07:43.497",
                "settingsHash": "29EDDA8E7A72C1AD060271268CC7AE81FAD54B9D",
                "uploadId": "5da6a0ca-86c3-440f-9462-fa53168dcb9d",
                "details": {"profiles": {"numberOfProfiles": 1}},
            },
        },
        {
            "algorithm": "Basal-IQ",
            "availableDataRange": {"start": None, "end": None},
            "assignmentId": "f6631fff-f403-4ce4-9362-83eff9e2850e",
            "glucoseUnit": None,
            "lastUploadDate": None,
            "maxDateOfEvents": None,
            "modelNumber": "1000096",
            "modelName": "t:slim X2™ Insulin Pump",
            "partNumber": "1003314",
            "serialNumber": "514387",
            "softwareVersion": "6.0.3.0",
            "lastUploadClientType": None,
            "settings": None,
        },
    ],
}


class TestPumpMetadataAdapter(unittest.TestCase):
    maxDiff = None

    def _api(self):
        # Bypass __init__ (which performs a network login) to test the adapter.
        return TandemSourceApi.__new__(TandemSourceApi)

    def test_bff_pump_to_metadata_active_pump(self):
        meta = TandemSourceApi._bff_pump_to_metadata(BFF_PUMPER["pumps"][0])
        self.assertEqual(meta["deviceId"], "1b493210-9336-4901-a329-a352775738c5")
        self.assertEqual(meta["serialNumber"], "90556643")
        self.assertEqual(meta["modelNumber"], "1000354")
        self.assertEqual(meta["softwareVersion"], "7.8.0.0")
        self.assertEqual(meta["algorithm"], "Control-IQ")
        # maxDateOfEvents -> maxDateWithEvents
        self.assertEqual(meta["maxDateWithEvents"], "2022-02-16T22:45:58")
        # availableDataRange.start -> minDateWithEvents
        self.assertEqual(meta["minDateWithEvents"], "2021-05-06T12:31:19")
        # settings.details -> settings
        self.assertEqual(meta["settings"], {"profiles": {"numberOfProfiles": 1}})

    def test_bff_pump_to_metadata_never_uploaded_pump(self):
        meta = TandemSourceApi._bff_pump_to_metadata(BFF_PUMPER["pumps"][1])
        self.assertEqual(meta["deviceId"], "f6631fff-f403-4ce4-9362-83eff9e2850e")
        self.assertEqual(meta["serialNumber"], "514387")
        # null date/settings fields map to None, not KeyError
        self.assertIsNone(meta["maxDateWithEvents"])
        self.assertIsNone(meta["minDateWithEvents"])
        self.assertIsNone(meta["settings"])

    def test_pump_metadata_maps_all_pumps(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get_pumper", return_value=BFF_PUMPER):
            metas = api.pump_metadata()
        self.assertEqual(len(metas), 2)
        self.assertEqual(
            [m["deviceId"] for m in metas],
            [
                "1b493210-9336-4901-a329-a352775738c5",
                "f6631fff-f403-4ce4-9362-83eff9e2850e",
            ],
        )

    def test_pump_metadata_empty_when_no_pumps(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get_pumper", return_value={}):
            self.assertEqual(api.pump_metadata(), [])

    def test_available_data_range_key_absent(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["availableDataRange"]
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertIsNone(meta["minDateWithEvents"])

    def test_settings_key_absent(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["settings"]
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertIsNone(meta["settings"])

    def test_missing_required_key_raises(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["serialNumber"]
        with self.assertRaises(KeyError):
            TandemSourceApi._bff_pump_to_metadata(pump)

    def test_mobi_controliq_plus_passthrough(self):
        pump = {
            "algorithm": "Control-IQ+",
            "availableDataRange": {"start": "2024-01-01T00:00:00", "end": "2026-05-27T23:03:06"},
            "assignmentId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "maxDateOfEvents": "2026-05-27T23:03:06",
            "modelNumber": "1004000",
            "modelName": "Tandem Mobi™ System",
            "partNumber": "1005000",
            "serialNumber": "1518994",
            "softwareVersion": "1.0.0.0",
            "lastUploadClientType": "mobile_mobi",
            "settings": None,
        }
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertEqual(meta["algorithm"], "Control-IQ+")
        self.assertEqual(meta["modelName"], "Tandem Mobi™ System")
        self.assertEqual(meta["deviceId"], "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


class TestDefaultEventIds(unittest.TestCase):
    def test_default_event_ids(self):
        ids = TandemSourceApi.DEFAULT_EVENT_IDS
        self.assertEqual(len(ids), 55)
        self.assertEqual(len(set(ids)), 55, "DEFAULT_EVENT_IDS contains duplicates")
        # FSL3 ids added for the BFF pump-logs endpoint
        self.assertTrue({477, 480, 486}.issubset(set(ids)))


# Trimmed real-shape pump-logs response (1 event + 1 clockChange).
PUMP_LOGS = {
    "events": [
        {
            "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "eventCode": 16,
            "sequenceGroup": 1,
            "sequenceNumber": 100123,
            "pumpDateTime": "2024-01-10T08:15:30",
            "eventProperties": {"iob": 1.25, "bg": 112},
            "estimatedDateTime": "2024-01-10T08:15:30Z",
        }
    ],
    "clockChanges": [
        {
            "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "eventCode": 13,
            "sequenceGroup": 0,
            "sequenceNumber": 5,
            "pumpDateTime": "2024-01-01T00:00:00",
            "eventProperties": {"timePrior": 1, "timeAfter": 2, "rawRtcTime": 3},
            "estimatedDateTime": "2024-01-01T00:00:00Z",
        }
    ],
}


class TestGetPumpLogs(unittest.TestCase):
    maxDiff = None

    def _api(self):
        api = TandemSourceApi.__new__(TandemSourceApi)
        api.pumperId = "PUMPER123"
        return api

    def _endpoint(self, mock_get):
        mock_get.assert_called_once()
        # (endpoint, query_dict) positional args
        self.assertEqual(mock_get.call_args.args[1], {})
        return mock_get.call_args.args[0]

    def _qs(self, endpoint, keep_blank=False):
        parsed = urllib.parse.urlparse(endpoint)
        return parsed.path, urllib.parse.parse_qs(parsed.query, keep_blank_values=keep_blank)

    def test_endpoint_path_and_params(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev-uuid", min_date="2024-01-01", max_date="2024-01-15")
        endpoint = self._endpoint(mock_get)
        path, qs = self._qs(endpoint)
        self.assertEqual(path, "api/reports/bff/pump-logs/dev-uuid")
        self.assertEqual(qs["pumperId"], ["PUMPER123"])
        self.assertEqual(qs["startDate"], ["2024-01-01T00:00:00Z"])
        self.assertEqual(qs["endDate"], ["2024-01-15T23:59:59Z"])

    def test_default_event_ids_comma_joined(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", min_date="2024-01-01", max_date="2024-01-02")
        _, qs = self._qs(self._endpoint(mock_get))
        self.assertEqual(qs["eventIds"][0].split(","),
                         [str(i) for i in TandemSourceApi.DEFAULT_EVENT_IDS])

    def test_custom_event_ids_comma_joined(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", "2024-01-01", "2024-01-02", event_ids_filter=[16, 5, 28])
        _, qs = self._qs(self._endpoint(mock_get))
        self.assertEqual(qs["eventIds"], ["16,5,28"])

    def test_none_event_ids_empty(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", "2024-01-01", "2024-01-02", event_ids_filter=None)
        _, qs = self._qs(self._endpoint(mock_get), keep_blank=True)
        self.assertEqual(qs["eventIds"], [""])

    def test_return_value_passthrough(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS):
            result = api.get_pump_logs("dev", "2024-01-01", "2024-01-15")
        self.assertIs(result, PUMP_LOGS)

    def test_none_dates_default_to_today(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev")
        _, qs = self._qs(self._endpoint(mock_get))
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.assertEqual(qs["startDate"], ["%sT00:00:00Z" % today])
        self.assertEqual(qs["endDate"], ["%sT23:59:59Z" % today])


if __name__ == "__main__":
    unittest.main()
