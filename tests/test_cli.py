import subprocess
import sys
import unittest


class CliExecutionTest(unittest.TestCase):
    def test_stats_command_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "main.py", "stats"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Business Analytics", result.stdout)


if __name__ == "__main__":
    unittest.main()
