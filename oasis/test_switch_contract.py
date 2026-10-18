"""Unit properties of hysteresis/urgent protection. All examples are synthetic."""
import unittest
from oasis.switch_contract import Candidate,MarketState,decide

class OASISSwitchTests(unittest.TestCase):
    def s(self,**extra):
        vals=dict(incumbent="ETF_A",incumbent_expected_shortfall_loss=.07,
                  posterior_systemic_stress=.1,maximum_allowed_expected_shortfall_loss=.16,
                  verified_defensive_available=True)
        vals.update(extra);return MarketState(**vals)
    def test_near_tie_holds(self):
        c=Candidate("ETF_B",.004,.008,.002,.08,.8)
        self.assertEqual(decide(self.s(),[c],simultaneous_candidates=60).action,"HOLD")
    def test_big_credible_crisis_opportunity_rotates(self):
        c=Candidate("ETF_B",.04,.009,.003,.10,.9)
        x=decide(self.s(posterior_systemic_stress=.70),[c],simultaneous_candidates=10)
        self.assertEqual(x.action,"ROTATE")
        self.assertGreater(x.lower_bound_net_log_gain,0)
    def test_unconfirmed_rebound_not_chased(self):
        c=Candidate("ETF_C",.03,.009,.002,.08,.35)
        self.assertEqual(decide(self.s(),[c],simultaneous_candidates=10).action,"HOLD")
    def test_protective_override_and_missing_defensive(self):
        s=self.s(incumbent_expected_shortfall_loss=.27,posterior_systemic_stress=.88)
        self.assertEqual(decide(s,[],simultaneous_candidates=1).action,"DEFEND")
        x=self.s(incumbent_expected_shortfall_loss=.27,
                 posterior_systemic_stress=.88,verified_defensive_available=False)
        self.assertEqual(decide(x,[],simultaneous_candidates=1).action,"RISK_ALERT")
    def test_many_looked_at_names_raise_evidence_bar(self):
        c=Candidate("ETF_B",.024,.008,.003,.11,.9)
        self.assertEqual(decide(self.s(),[c],simultaneous_candidates=1).action,"ROTATE")
        self.assertEqual(decide(self.s(),[c],simultaneous_candidates=60).action,"HOLD")
    def test_tail_budget_prevents_spurious_high_return_trade(self):
        c=Candidate("ETF_B",.20,.01,.003,.32,.9)
        self.assertEqual(decide(self.s(),[c],simultaneous_candidates=10).action,"HOLD")
    def test_invalid_count_fails_closed(self):
        with self.assertRaises(ValueError):
            decide(self.s(),[Candidate("ETF_B",.04,.01,.001,.08,.9)],simultaneous_candidates=0)

if __name__=="__main__":unittest.main()
