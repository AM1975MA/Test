from pathlib import Path
import subprocess
exp={
  "vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py":"045e57996b02d481bd23f6e4dfe53738d43008e5",
  "vendor/etf_trader_v2/src/etf_trader/source_only/features.py":"b7f6520b2b5bc54fdc26178dea839bad8a8fecaf",
  "vendor/etf_trader_v2/src/etf_trader/source_only/models.py":"fc642cce171facfcb92440a7708ee2428f120efe",
  "vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py":"2b2ebd4d35ff32e88be62edc61a464656f6f7d4b",
  "vendor/etf_trader_v2/src/etf_trader/ma3/ensemble.py":"4b23fd297df6bfcf71557af9a7aaf7ca96c9a223",
  "vendor/etf_trader_v2/src/etf_trader/ma3/hybrid_producer.py":"acf83f2cee6876c89dfd9948cfbf30889af4c08e",
  "vendor/etf_trader_v2/src/etf_trader/ma3/producer.py":"e691376e3a8e0ec1bd38cc5b85a8ebbfa35d0592",
  "vendor/etf_trader_v2/src/etf_trader/ma3/ddfirst.py":"3794564fdfe8501c2c19e618bc7d1550884aeb53",
  "vendor/etf_trader_v2/src/etf_trader/ma3/v6.py":"6c5d3fd6f54fb5ef5162f4b26d3ef9af2af34701",
  "vendor/p45/v2_stage19_kernel.py":"364c16f61d1866946827626e0d8f26dab276aca4"
}
lf={"vendor/etf_trader_v2/src/etf_trader/source_only/models.py","vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py"}
for p,w in exp.items():
    g=subprocess.check_output(["git","hash-object",p],text=True).strip()
    if g!=w and p in lf:
        q=Path(p);b=q.read_bytes()
        if not b.endswith(b"\n"):
            q.write_bytes(b+b"\n");g=subprocess.check_output(["git","hash-object",p],text=True).strip()
    assert g==w,(p,g,w)
print("SOURCE_GATE_PASS")
