import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/jukebox')))

from components.rfid.reader import append_scan_history_event  # noqa: E402


def test_append_scan_history_event(tmp_path):
    out_file = tmp_path / 'rfid_scan_history.jsonl'

    append_scan_history_event(str(out_file), 'read_00', '12345', True)
    append_scan_history_event(str(out_file), 'read_01', 'abcde', False)

    with open(out_file, encoding='utf-8') as stream:
        lines = [line.strip() for line in stream if line.strip()]

    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])

    assert first['reader'] == 'read_00'
    assert first['card_id'] == '12345'
    assert first['is_registered'] is True
    assert isinstance(first['timestamp_utc'], str)

    assert second['reader'] == 'read_01'
    assert second['card_id'] == 'abcde'
    assert second['is_registered'] is False
    assert isinstance(second['timestamp_utc'], str)
