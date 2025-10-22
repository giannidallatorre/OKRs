import unittest
import os
from pyOKR_VOs_CPUs_Accounting.utils.merged_utils import find_difference, colourise, highlight, get_env_settings

class TestMergedUtils(unittest.TestCase):
    def test_find_difference(self):
        self.assertIn(find_difference("a, b, c", "b, c, d"), ["d, a", "a, d"])
        self.assertEqual(find_difference("a, b, c", "b, c, d", detailed=True), ("d", "a"))
        self.assertEqual(find_difference("a, b", "a, b"), "")
        self.assertEqual(find_difference("a, b", "a, b", detailed=True), ("-", "-"))
    
    # def test_colourise(self):
    #     self.assertIn("\033[1;31mHello\033[0m", colourise("red", "Hello"))
    #     self.assertEqual(colourise("unknown", "Test"), "Test")
    
    def test_highlight(self):
        self.assertEqual("\033[1;41mHello\033[0m", highlight("red", "Hello"))
        # self.assertEqual(highlight("unknown", "Test"), "Test")
    
    def test_get_env_settings(self):
        os.environ["SERVICE_ACCOUNT_PATH"] = "TEST_VALUE"
        settings = get_env_settings()
        self.assertIn("SERVICE_ACCOUNT_PATH", settings)
        self.assertEqual(settings["SERVICE_ACCOUNT_PATH"], "TEST_VALUE")
        del os.environ["SERVICE_ACCOUNT_PATH"]

if __name__ == "__main__":
    unittest.main()
