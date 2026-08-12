import unittest
from pathlib import Path


class SkillSmokeTests(unittest.TestCase):
    def test_skill_exists(self) -> None:
        self.assertTrue(Path("candidate-skill/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
