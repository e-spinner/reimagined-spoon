from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "reimagined-spoon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_final_project.roster import read_student_names


class TestExampleNameSheetODS(unittest.TestCase):
    def test_example_name_sheet_ods_parses(self) -> None:
        sheet_path = (
            Path(__file__).resolve().parents[1]
            / "Unit Tests"
            / "fixtures"
            / "Example Name sheet.ods"
        )

        names = read_student_names(sheet_path)

        self.assertEqual(
            names,
            ["George Alan", "Michael Smith"],
        )

    def test_student_names_header_is_skipped(self) -> None:
        names = ["Student Names", "George Alan", "Michael Smith"]
        # Exercise public API behavior through read_student_names-style cleanup.
        from ai_final_project.roster import _strip_header_if_present

        self.assertEqual(
            _strip_header_if_present(names),
            ["George Alan", "Michael Smith"],
        )


if __name__ == "__main__":
    unittest.main()
