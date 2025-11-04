import unittest

from classify_content_types import CategoryConfig, Classifier, FileRecord, Trigger


class ClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        interview_triggers = [
            Trigger.from_dict({"Type": "Regex", "Pattern": "interview", "Score": 3}),
            Trigger.from_dict({"Type": "Keyword", "Values": ["caleb"], "Score": 1}),
        ]
        system_triggers = [
            Trigger.from_dict({"Type": "Regex", "Pattern": "(readme|license)", "Score": 2}),
            Trigger.from_dict({"Type": "Extension", "Values": [".md"], "Score": 1}),
        ]
        self.categories = [
            CategoryConfig(name="Interview_Transcripts", triggers=interview_triggers),
            CategoryConfig(name="System_Files", triggers=system_triggers),
        ]
        self.classifier = Classifier(self.categories, ["Interview_Transcripts", "System_Files"])

    def test_detects_interview_with_festival(self) -> None:
        record = FileRecord(
            {
                "rank": 55,
                "filename": "Caleb_All_Around_Film_Festival_Interview.txt",
                "full_path": "D:/transcripts/Caleb_All_Around_Film_Festival_Interview.txt",
                "extension": ".txt",
                "keywords": ["Caleb", "festival", "interview"],
                "score": 10,
            }
        )
        buckets, errors = self.classifier.classify([record])
        self.assertEqual(errors, 0)
        self.assertEqual(record.winning_category, "Interview_Transcripts")
        self.assertIn("All_Around_Film_Festival", record.insights.get("Festivals", []))
        self.assertIn(record, buckets["Interview_Transcripts"])

    def test_system_file_detection(self) -> None:
        record = FileRecord(
            {
                "rank": 1,
                "filename": "README.md",
                "full_path": "D:/docs/README.md",
                "extension": ".md",
                "keywords": ["doc"],
                "score": 2,
            }
        )
        buckets, errors = self.classifier.classify([record])
        self.assertEqual(errors, 0)
        self.assertEqual(record.winning_category, "System_Files")
        self.assertIn(record, buckets["System_Files"])

    def test_technical_interview_bonus(self) -> None:
        classifier = Classifier([CategoryConfig(name="Interview_Transcripts", triggers=[])], ["Interview_Transcripts"])
        record = FileRecord(
            {
                "rank": 2,
                "filename": "Kick_mixdown.wav.txt",
                "full_path": "D:/transcripts/Kick_mixdown.wav.txt",
                "extension": ".txt",
                "keywords": ["audio"],
                "score": 4,
            }
        )
        buckets, errors = classifier.classify([record])
        self.assertEqual(errors, 0)
        self.assertEqual(record.winning_category, "Interview_Transcripts")
        self.assertGreaterEqual(record.winning_score, 1)
        self.assertIn(record, buckets["Interview_Transcripts"])


if __name__ == "__main__":
    unittest.main()
