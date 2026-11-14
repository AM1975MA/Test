import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pytest
from broker_cost import solve_budget

def test_single_buy_cost_is_self_financing():
 eq,cost,n=solve_budget(10000.,np.array([0.,0.]),np.array([1.,0.]),1.,.0015)
 assert n==1 and abs(eq-(9999/1.0015))<1e-8
 assert abs(eq+cost-10000)<1e-8

def test_two_sells_two_buys_four_tickets():
 old=np.array([5000.,5000.,0.,0.]);w=np.array([0.,0.,.5,.5])
 eq,cost,n=solve_budget(10000.,old,w,1.,.0015)
 assert n==4 and abs(cost-(4+.0015*(10000+eq)))<1e-7

def test_no_ticket_on_cash():
 eq,cost,n=solve_budget(10000.,np.array([0.,0.]),np.array([0.,0.]),2.,.003)
 assert eq==10000 and cost==0 and n==0

def test_no_negative_capital():
 with pytest.raises(ValueError):solve_budget(1.,np.array([0.,0.]),np.array([.5,.5]),2.,.003)
