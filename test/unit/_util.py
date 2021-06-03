# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
# type: ignore
import unittest

from pdkmaster import _util

class UtilTest(unittest.TestCase):
    def test_i2f(self):
        self.assertAlmostEqual(_util.i2f(2.0), 2.0, 12)
        self.assertAlmostEqual(_util.i2f(1), 1.0, 12)
        self.assertEqual(_util.i2f(None), None)
        with self.assertRaisesRegex(
            ValueError, "Use of bool as float not allowed",
        ):
            self.assertEqual(_util.i2f(True), True)
        with self.assertRaisesRegex(
            ValueError, "could not convert string to float: 'Yoh'",
        ):
            self.assertEqual(_util.i2f("Yoh"), "Yoh")

    def test_i2f_recursive(self):
        f = _util.i2f_recursive(2)
        self.assertIsInstance(f, float)
        self.assertAlmostEqual(f, 2.0, 12)

        t = _util.i2f_recursive((range(3), 3, 4.0))
        self.assertIsInstance(t, tuple)
        self.assertAlmostEqual(t[0][0], 0.0, 12)
        self.assertAlmostEqual(t[0][2], 2.0, 12)
        self.assertAlmostEqual(t[1], 3.0, 12)
        self.assertAlmostEqual(t[2], 4.0, 12)

    def test_v2t(self):
        self.assertEqual(_util.v2t(None), (None,))
        self.assertEqual(_util.v2t(False), (False,))
        self.assertEqual(_util.v2t(2.0), (2.0,))
        self.assertEqual(_util.v2t(range(3)), (0, 1, 2))
        self.assertEqual(_util.v2t("Yoh"), ("Yoh",))
        self.assertEqual(_util.v2t(2, n=2), (2, 2))

        with self.assertRaises(AssertionError):
            _util.v2t(range(3), n=2)

    def test_is_iterable(self):
        self.assertEqual(_util.is_iterable(None), False)
        self.assertEqual(_util.is_iterable(1), False)
        self.assertEqual(_util.is_iterable(1.0), False)
        self.assertEqual(_util.is_iterable(range(2)), True)
        self.assertEqual(_util.is_iterable((1, "a")), True)
        self.assertEqual(_util.is_iterable({0}), True)
        self.assertEqual(_util.is_iterable("a"), True)

    def test_nth(self):
        self.assertEqual(_util.nth(range(5), 2), 2)
        with self.assertRaises(StopIteration):
            _util.nth(range(2), 3)

    def test_first(self):
        self.assertEqual(_util.first(range(5)), 0)
        with self.assertRaises(StopIteration):
            _util.first(tuple())

    def test_last(self):
        self.assertEqual(_util.last(range(2)), 1)
        with self.assertRaises(StopIteration):
            _util.last({})

    def test_strip_literal(self):
        self.assertEqual(_util.strip_literal('"Yoh"'), 'Yoh')
        self.assertEqual(_util.strip_literal("'Yoh'"), "'Yoh'")
        self.assertEqual(_util.strip_literal('"Yoh"'), 'Yoh')
        self.assertEqual(_util.strip_literal('"Yoh'), '"Yoh')
        self.assertEqual(_util.strip_literal('Yoh"'), 'Yoh"')
