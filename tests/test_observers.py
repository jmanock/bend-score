import unittest

from bend_score.observers.registry import ObserverRegistry


class ObserverRegistryTest(unittest.TestCase):
    def test_enabled_observer_generates_standard_signals(self) -> None:
        observers = ObserverRegistry.enabled()

        self.assertTrue(any(observer.name == "fake_opportunity" for observer in observers))
        result = next(observer.run() for observer in observers if observer.name == "fake_opportunity")
        self.assertEqual(result.raw_count, 15)
        self.assertGreaterEqual(len(result.signals), 15)
        self.assertTrue(all(signal.observer == "fake_opportunity" for signal in result.signals))


if __name__ == "__main__":
    unittest.main()

