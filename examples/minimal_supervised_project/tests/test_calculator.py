"""Tests for calculator module."""

import unittest

from src.calculator import add, subtract


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)

    def test_subtract(self):
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(1, 4), -3)
        self.assertEqual(subtract(0, 5), -5)
