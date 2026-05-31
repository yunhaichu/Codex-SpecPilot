"""Run tests for the minimal supervised project."""
import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=2)
    raise SystemExit(0 if runner.run(suite).wasSuccessful() else 1)
