import tempfile
import unittest
from pathlib import Path

from design_naming_conventions import process_classification


class NamingConventionTests(unittest.TestCase):
    def test_rule_matching_and_placeholders(self) -> None:
        classification_data = {
            "Classifications": {
                "Data_Reports": [
                    {
                        "FileName": "stats_report_20240101.csv",
                        "FullPath": "C:/reports/stats_report_20240101.csv",
                        "Extension": ".csv",
                        "Modified": "2024-01-05T00:00:00",
                        "Keywords": ["stats"],
                        "Rank": 4,
                        "Score": 88,
                    },
                    {
                        "FileName": "mystery.txt",
                        "FullPath": "C:/reports/mystery.txt",
                        "Extension": ".txt",
                        "Modified": "2024-05-06",
                        "Keywords": [],
                        "Rank": 12,
                        "Score": 12,
                    },
                ]
            }
        }
        config = {
            "NamingRules": {
                "Data_Reports": {
                    "Pattern": "GW_Report_{Type}_{Date}.{ext}",
                    "Rules": [
                        {
                            "Condition": {"FileName": "(?i)stats"},
                            "Mapping": {"Type": "Statistics"},
                        }
                    ],
                    "DefaultMapping": {"Type": "Analysis"},
                }
            },
            "GlobalSettings": {"PreservePaths": False, "DateFormat": "yyyy-MM-dd"},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary, mappings = process_classification(classification_data, config, Path(tmp_dir), True)
        self.assertEqual(summary["TotalFiles"], 2)
        self.assertEqual(summary["FilesRenamed"], 2)
        generated_names = {item["OldFileName"]: item["NewFileName"] for item in mappings}
        self.assertEqual(generated_names["stats_report_20240101.csv"], "GW_Report_Statistics_2024-01-01.csv")
        self.assertEqual(generated_names["mystery.txt"], "GW_Report_Analysis_2024-05-06.txt")
        mapping_lookup = {item["OldFileName"]: item["Mapping"] for item in mappings}
        self.assertEqual(mapping_lookup["stats_report_20240101.csv"]["Date"], "2024-01-01")
        self.assertEqual(mapping_lookup["mystery.txt"]["ext"], "txt")

    def test_duplicate_resolution_add_version(self) -> None:
        classification_data = {
            "Classifications": {
                "Web_Content": [
                    {
                        "FileName": "page_a.html",
                        "FullPath": "C:/site/page_a.html",
                        "Extension": ".html",
                        "Keywords": ["web"],
                        "Rank": 1,
                        "Score": 90,
                    },
                    {
                        "FileName": "page_b.html",
                        "FullPath": "C:/site/page_b.html",
                        "Extension": ".html",
                        "Keywords": ["web"],
                        "Rank": 2,
                        "Score": 70,
                    },
                ]
            }
        }
        config = {
            "NamingRules": {
                "Web_Content": {
                    "Pattern": "GW_Web_Page.html",
                    "Rules": [],
                    "DefaultMapping": {},
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary, mappings = process_classification(classification_data, config, Path(tmp_dir), True)
        new_names = [item["NewFileName"] for item in mappings]
        self.assertIn("GW_Web_Page.html", new_names)
        self.assertIn("GW_Web_Page_v2.html", new_names)
        self.assertEqual(summary["Conflicts"], 1)

    def test_duplicate_resolution_append_rank(self) -> None:
        classification_data = {
            "Classifications": {
                "Unknown": [
                    {
                        "FileName": "alpha.bin",
                        "FullPath": "C:/data/alpha.bin",
                        "Extension": ".bin",
                        "Rank": 11,
                        "Score": 50,
                    },
                    {
                        "FileName": "beta.bin",
                        "FullPath": "C:/data/beta.bin",
                        "Extension": ".bin",
                        "Rank": 99,
                        "Score": 41,
                    },
                ]
            }
        }
        config = {
            "NamingRules": {
                "Unknown": {
                    "Pattern": "GW_Unknown_File.{ext}",
                    "Rules": [],
                    "DefaultMapping": {},
                }
            },
            "GlobalSettings": {"HandleDuplicates": "AppendRank"},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary, mappings = process_classification(classification_data, config, Path(tmp_dir), True)
        new_names = sorted(item["NewFileName"] for item in mappings)
        self.assertIn("GW_Unknown_File.bin", new_names)
        self.assertIn("GW_Unknown_File_rank99.bin", new_names)
        self.assertEqual(summary["Conflicts"], 1)


if __name__ == "__main__":
    unittest.main()
