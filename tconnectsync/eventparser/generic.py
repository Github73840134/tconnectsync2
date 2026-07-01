import struct
import base64
import logging

from dataclasses import dataclass

from .raw_event import RawEvent, EVENT_LEN
from .events import EVENT_IDS
from .utils import batched

logger = logging.getLogger(__name__)

def Event(x):
    raw_event = RawEvent.build(x)
    if not raw_event.id in EVENT_IDS:
        # Log unknown events with full hex dump for reverse-engineering
        hex_dump = ' '.join(f'{b:02x}' for b in x[:EVENT_LEN])
        # Also log seqNum and timestamp for correlation
        logger.debug(f"UNKNOWN_EVENT | id={raw_event.id} | seqNum={raw_event.seqNum} | timestamp={raw_event.timestamp.isoformat()} | bytes={hex_dump}")
        return raw_event


    return EVENT_IDS[raw_event.id].build(x)

Events = lambda x: (Event(bytearray(e)) for e in batched(x, EVENT_LEN))

def decode_raw_events(raw):
    return base64.b64decode(raw)


def Event_from_json(event):
    raw_event = RawEvent.build_from_json(event)
    if not raw_event.id in EVENT_IDS:
        # Log unknown events with their property keys for reverse-engineering
        props = ' '.join(event['eventProperties'].keys())
        # Also log seqNum and timestamp for correlation
        logger.debug(f"UNKNOWN_JSON_EVENT | id={raw_event.id} | seqNum={raw_event.seqNum} | timestamp={raw_event.timestamp.isoformat()} | props={props}")
        return raw_event


    return EVENT_IDS[raw_event.id].build_from_json(event)

Events_from_json = lambda events: (Event_from_json(e) for e in events)