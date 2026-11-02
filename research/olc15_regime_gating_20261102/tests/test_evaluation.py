import pandas as pd
from evaluate import periods_for

def test_adaptive_period_excludes_fallback_and_unmatured_end():
 assert 'ADAPTIVE2023_2024' not in periods_for(pd.Timestamp('2022-12-30'),pd.Timestamp('2023-04-01'))
 assert 'ADAPTIVE2023_2024' in periods_for(pd.Timestamp('2024-01-31'),pd.Timestamp('2024-05-01'))
 assert 'ADAPTIVE2023_2024' not in periods_for(pd.Timestamp('2024-12-31'),pd.Timestamp('2025-04-01'))
 assert 'ADAPTIVE2023_2024_ALL_SIGNALS' in periods_for(pd.Timestamp('2024-12-31'),pd.Timestamp('2025-04-01'))

def test_future_unavailable_endpoints_not_evaluated():
 assert periods_for(pd.Timestamp('2026-06-30'),pd.NaT)==[]
 assert 'ADAPTIVE_FULL' not in periods_for(pd.Timestamp('2026-06-30'),pd.Timestamp('2026-10-01'))
