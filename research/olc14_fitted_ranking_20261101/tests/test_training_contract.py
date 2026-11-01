import json
import pytest
from train_heads import parameters
from common import P11,SEEDS

def test_original_hyperparameters_except_seed():
 p=json.loads((P11/'inputs/PARENT_PARAMETERS.json').read_text())
 for family in ['ET','XGB']:
  for seed in SEEDS:
   expected=dict(p[family],random_state=seed)
   assert parameters(family,seed)==expected

def test_undeclared_family_or_seed_rejected():
 with pytest.raises(ValueError):parameters('OTHER',101)
 with pytest.raises(ValueError):parameters('ET',999)
