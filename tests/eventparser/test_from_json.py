#!/usr/bin/env python3

import unittest

from tconnectsync.eventparser.generic import Event_from_json, Events_from_json
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent

# Trimmed real pump-log events (values from a captured account response).
BASAL_279 = {
    "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
    "eventCode": 279,
    "sequenceGroup": 0,
    "sequenceNumber": 393131,
    "pumpDateTime": "2026-04-30T00:03:29",
    "eventProperties": {
        "commandedRateSource": 3, "reservedA2": 0, "spareA3": 0,
        "commandedRate": 0, "profileBasalRate": 1000, "algorithmRate": 0,
        "tempRate": 65535,
    },
    "estimatedDateTime": "2026-04-30T00:03:29Z",
}

ALARM_5 = {
    "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
    "eventCode": 5,
    "sequenceGroup": 0,
    "sequenceNumber": 500001,
    "pumpDateTime": "2026-04-30T01:00:00",
    "eventProperties": {"alarmId": 18, "faultLocatorData": 8311, "param1": 3993668, "param2": 0},
    "estimatedDateTime": "2026-04-30T01:00:00Z",
}


class TestBuildFromJson(unittest.TestCase):
    maxDiff = None

    def test_dispatches_to_correct_class(self):
        self.assertIsInstance(Event_from_json(BASAL_279), eventtypes.LidBasalDelivery)
        self.assertIsInstance(Event_from_json(ALARM_5), eventtypes.LidAlarmActivated)

    def test_plain_fields(self):
        ev = Event_from_json(BASAL_279)
        self.assertEqual(ev.commandedRate, 0)
        self.assertEqual(ev.profileBasalRate, 1000)
        self.assertEqual(ev.tempRate, 65535)

    def test_envelope_fields(self):
        ev = Event_from_json(BASAL_279)
        self.assertEqual(ev.seqNum, 393131)
        self.assertEqual(ev.eventId, 279)

    def test_timestamp_preserves_wall_clock(self):
        # eventTimestamp keeps pumpDateTime's wall-clock (tz forced to the
        # configured TIMEZONE_NAME), so the naive portion round-trips exactly.
        ev = Event_from_json(BASAL_279)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-04-30T00:03:29")

    def test_missing_plain_field_defaults_to_none(self):
        event = dict(BASAL_279)
        event["eventProperties"] = {k: v for k, v in BASAL_279["eventProperties"].items() if k != "tempRate"}
        ev = Event_from_json(event)
        self.assertIsNone(ev.tempRate)
        self.assertEqual(ev.commandedRate, 0)  # others still parse

    def test_extra_keys_are_ignored(self):
        event = dict(BASAL_279)
        event["eventProperties"] = dict(BASAL_279["eventProperties"], someFutureField=42)
        ev = Event_from_json(event)  # must not raise
        self.assertFalse(hasattr(ev, "someFutureField"))

    def test_events_from_json_yields_in_order(self):
        out = list(Events_from_json([BASAL_279, ALARM_5]))
        self.assertEqual([type(e).__name__ for e in out],
                         ["LidBasalDelivery", "LidAlarmActivated"])

    def test_unknown_eventcode_falls_back_to_rawevent(self):
        ev = Event_from_json({
            "eventCode": 99999,
            "sequenceNumber": 7,
            "pumpDateTime": "2026-04-30T00:00:00",
            "eventProperties": {},
        })
        self.assertIs(type(ev), RawEvent)
        self.assertEqual(ev.eventId, 99999)
        self.assertEqual(ev.seqNum, 7)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-04-30T00:00:00")


if __name__ == "__main__":
    unittest.main()
