import unittest

import calc


class MeanTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(calc.mean([1, 2, 3]), 2)


if __name__ == "__main__":
    unittest.main()
