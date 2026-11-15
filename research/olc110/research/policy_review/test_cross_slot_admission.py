"""Read-only, literal account-state regressions for OLC110 review.

These call the policy with hand-specified holdings. They do not run a financial
backtest and do not load market data or financial result files.
"""
from pathlib import Path
import importlib.util
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "olc110_policy_review_fixtures", ROOT / "tests/test_protection.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
fixtures.ProtectionTests.setUpClass()


class CrossSlotPolicyReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProtectionTests()
        self.fixture.setUp()

    def crossed_fresh_slots(self):
        """Reach primary A/asset C and primary B/asset A by valid transitions."""
        t = self.fixture
        policy = t.initialized("EXIT21_STAGED_FRESHW")
        t.bad(253, 0)
        t.call(policy, 253, [.5, .5, 0, 0])
        t.bad(254, 0)
        t.emerging(254, 2)
        t.call(policy, 254, [0, .5, 0, 0])
        t.bad(255, 1)
        t.call(policy, 255, [0, .5, .25, 0], buys={2: 255})
        t.bad(259, 1)
        t.emerging(259, 0)
        t.call(policy, 259, [0, 0, .25, 0], buys={2: 255})
        self.assertEqual([(s["primary"], s["asset"]) for s in policy.slots],
                         [(0, 2), (1, 0)])
        return policy

    def test_primary_held_elsewhere_does_not_suppress_fresh_fallback(self):
        t = self.fixture
        policy = self.crossed_fresh_slots()
        t.bad(260, 2)
        t.f["m21"][260, 0] = 0.
        t.call(policy, 260, [.25, 0, .5, 0], buys={0: 260, 2: 255})
        t.emerging(264, 3)
        t.f["m21"][264, 0] = 0.
        current = np.array([.25, 0, 0, 0])
        self.assertEqual(policy.fresh_candidate(264, 0, current), 3)
        action = t.call(policy, 264, current, buys={0: 260, 2: 255})
        self.assertIsNotNone(action, "An eligible D should fill vacant slot 0")
        self.assertEqual(action["weights"][3], .25)

    def test_old_fresh_asset_does_not_claim_other_slots_later_holding(self):
        t = self.fixture
        policy = self.crossed_fresh_slots()
        # A fails as a fresh probe in slot 1 and is actually sold.
        t.bad(260, 0)
        t.f["sma10"][260, 0] = 101.
        t.call(policy, 260, [.25, 0, .5, 0], buys={0: 260, 2: 255})
        # C then exits from slot 0 and is actually sold.
        t.bad(262, 2)
        t.bad(262, 1)
        t.call(policy, 262, [0, 0, .5, 0], buys={0: 260, 2: 255})
        # A is admitted back into its original slot while B is still blocked.
        t.bad(264, 1)
        action = t.call(policy, 264, [0, 0, 0, 0])
        self.assertEqual(action["weights"][0], .5)
        self.assertEqual(policy.slots[0]["state"], "NORMAL")
        self.assertEqual(policy.slots[1]["state"], "CASH")
        # B now satisfies SLOW. A's new holding belongs to slot 0; it is not
        # residual unsold inventory of slot 1's already liquidated old probe.
        action = t.call(policy, 266, [.5, 0, 0, 0], buys={0: 265})
        self.assertIsNotNone(action, "B must not be blocked by slot 0's new A")
        self.assertEqual(action["weights"][1], .5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
