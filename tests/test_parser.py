"""Tests for the dependency-free FT0360 parser."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "ft0360" / "parser.py"
)
SPEC = importlib.util.spec_from_file_location("ft0360_parser", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
parser = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = parser
SPEC.loader.exec_module(parser)


SAMPLE = json.loads(
    r'''{
      "Sensor": [
        {"title": "Indoor", "list": [["Temperature", "25.2", "Â°C"], ["Humidity", "52", "%"]]},
        {"title": "Outdoor", "list": [["Temperature", "24,1 °C", "Â°C"], ["Humidity", "46", "%"]]},
        {"title": "Pressure", "list": [
          ["Absolute", "973.1", "hpa"], ["Relative", "1012.2", "hpa"]
        ]},
        {"title": "Wind Speed", "list": [
          ["Max Daily Gust", "6.9", "m/s"], ["Wind", "0.5", "m/s"],
          ["Gust", "0.7", "m/s"], ["Direction", "504", "Â°"],
          ["Wind Average 2 Minute", "0.4", "m/s"], ["Direction Average 2 Minute", "147", "Â°"],
          ["Wind Average 10 Minute", "0.2", "m/s"], ["Direction Average 10 Minute", "127", "Â°"]
        ]},
        {"title": "Rainfall", "list": [
          ["Rate", "0.0", "mm/hr"], ["Hour", "0.0", "mm", "43"],
          ["Day", "0.9", "mm", "44"], ["Week", "0.9", "mm", "45"],
          ["Month", "0.9", "mm", "46"], ["Year", "0.9", "mm", "47"],
          ["Total", "0.9", "mm", "48"]
        ]},
        {"title": "Solar", "list": [["Light", "12.68", "w/mÂ²"], ["UVI", "0.0", ""]]}
      ],
      "battery": {"title": "Battery", "list": ["All battery are ok"]}
    }'''
)


class ParseRecordTests(unittest.TestCase):
    """Exercise real and malformed console payloads."""

    def test_parse_real_shape_and_mojibake_units(self):
        record = parser.parse_record(SAMPLE)

        self.assertEqual(len(record.values), 23)
        self.assertEqual(record.values["outdoor_temperature"], 24.1)
        self.assertEqual(record.values["solar_radiation"], 12.68)
        self.assertEqual(record.values["wind_direction"], 144.0)
        self.assertFalse(record.battery_low)

    def test_semantic_labels_survive_reordering(self):
        payload = {
            "Sensor": [
                {
                    "title": "Pressure",
                    "list": [["Relative", "1012.2", "hPa"], ["Absolute", "973.1", "hPa"]],
                }
            ]
        }
        record = parser.parse_record(payload)

        self.assertEqual(record.values["pressure_absolute"], 973.1)
        self.assertEqual(record.values["pressure_relative"], 1012.2)

    def test_position_fallback_works_for_unknown_labels(self):
        payload = {
            "Sensor": [
                {"title": "?", "list": [["?", "21.5", "Â°C"], ["?", "40", "%"]]}
            ]
        }
        record = parser.parse_record(payload)

        self.assertEqual(record.values["indoor_temperature"], 21.5)
        self.assertEqual(record.values["indoor_humidity"], 40.0)

    def test_missing_and_non_numeric_values_stay_absent(self):
        payload = {
            "Sensor": [
                {
                    "title": "Outdoor",
                    "list": [["Temperature", "--", "Â°C"], ["Humidity", None, "%"]],
                }
            ]
        }
        record = parser.parse_record(payload)

        self.assertNotIn("outdoor_temperature", record.values)
        self.assertNotIn("outdoor_humidity", record.values)

    def test_battery_problem_and_unknown(self):
        problem = dict(SAMPLE)
        problem["battery"] = {"list": ["Outdoor sensor battery low"]}
        self.assertTrue(parser.parse_record(problem).battery_low)

        unknown = dict(SAMPLE)
        unknown["battery"] = {"list": ["Status unavailable"]}
        self.assertIsNone(parser.parse_record(unknown).battery_low)

    def test_invalid_payload_raises(self):
        with self.assertRaises(parser.FT0360ParseError):
            parser.parse_record({"status": "ok"})


class HelperTests(unittest.TestCase):
    """Test identity and compass helpers."""

    def test_station_info_and_mac_normalization(self):
        info = parser.parse_station_info(
            {"Model": "", "Version": "Version 2.0.0", "MAC": "D4-8A-FC-3A-E1-AC"}
        )
        self.assertIsNone(info.model)
        self.assertEqual(info.firmware, "Version 2.0.0")
        self.assertEqual(info.mac, "d4:8a:fc:3a:e1:ac")

    def test_cardinal_directions(self):
        self.assertEqual(parser.degrees_to_cardinal(0), "n")
        self.assertEqual(parser.degrees_to_cardinal(44), "ne")
        self.assertEqual(parser.degrees_to_cardinal(144), "se")
        self.assertEqual(parser.degrees_to_cardinal(359), "n")
        self.assertIsNone(parser.degrees_to_cardinal(None))

    def test_firmware_info_preserves_zero_padded_build(self):
        info = parser.parse_firmware_info(
            {"Firmware": {"Version": "2.0.0", "build": "00026", "bin": "user1.bin"}}
        )

        self.assertEqual(info.version, "2.0.0")
        self.assertEqual(info.build, "00026")

    def test_connection_info_and_status_mapping(self):
        info = parser.parse_connection_info(
            {
                "IPConfig": {
                    "status": 5,
                    "reason": 204,
                    "rssi": 3,
                    "ip": "192.168.1.236",
                    "gw": "192.168.1.1",
                    "mac": "D4:8A:FC:3A:E1:AC",
                }
            }
        )

        self.assertEqual(info.status, "connected")
        self.assertEqual(info.status_code, 5)
        self.assertEqual(info.wifi_signal_level, 3)
        self.assertEqual(info.ip_address, "192.168.1.236")
        self.assertEqual(info.gateway, "192.168.1.1")
        self.assertEqual(info.mac, "d4:8a:fc:3a:e1:ac")

    def test_unknown_connection_status_is_forward_compatible(self):
        info = parser.parse_connection_info({"IPConfig": {"status": 99, "rssi": "--"}})

        self.assertEqual(info.status, "unknown")
        self.assertIsNone(info.wifi_signal_level)

    def test_debug_info_is_kept_diagnostic_and_nulls_are_normalized(self):
        info = parser.parse_debug_info(
            {
                "Model": "esp8266 router",
                "Version": "2.0.0 build-00026 ",
                "UploadStatus": [
                    {
                        "Serial": 1,
                        "Code": 1,
                        "Message": "",
                        "Website": "wunderground.com",
                        "Time": "2026-09-02 20:29:42",
                    },
                    {
                        "Serial": 3,
                        "Code": 1,
                        "Message": "",
                        "Website": "weathercloud.net",
                        "Time": "2026-09-02 20:29:42",
                    },
                ],
                "Net": 0,
                "ostime": "2026-09-02 20:30:39",
                "synctime": "0.17.56",
                "time_info": "Year: 2026, Bias: -60",
                "Feature": True,
                "Option": {
                    "Nation": "NULL",
                    "Transmitter": "NULL",
                    "Position": "NULL",
                    "Pairing": "AP mode",
                },
            }
        )

        self.assertEqual(info.model, "esp8266 router")
        self.assertEqual(info.version, "2.0.0 build-00026")
        self.assertEqual(info.upload_status[0]["website"], "wunderground.com")
        self.assertEqual(info.upload_status[1]["serial"], 3)
        self.assertEqual(info.network_state, 0)
        self.assertEqual(info.device_time, "2026-09-02 20:30:39")
        self.assertEqual(info.sync_time, "0.17.56")
        self.assertTrue(info.feature_enabled)
        self.assertIsNone(info.options["nation"])
        self.assertEqual(info.options["pairing"], "AP mode")

    def test_invalid_diagnostic_payloads_raise(self):
        with self.assertRaises(parser.FT0360ParseError):
            parser.parse_firmware_info({"Firmware": {}})
        with self.assertRaises(parser.FT0360ParseError):
            parser.parse_connection_info({"status": 5})
        with self.assertRaises(parser.FT0360ParseError):
            parser.parse_debug_info({"unrelated": True})


if __name__ == "__main__":
    unittest.main()
