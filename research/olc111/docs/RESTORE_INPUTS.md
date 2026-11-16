# Exact input restoration

The source panels are large and were already archived with OLC109. The downloaded raw Cboe files are retained separately from the public research repository. Derived model banks, source fingerprints, fitted coefficients and result ledgers are included in the research subtree.

## ETF panel and liquidity

Archive: `OLC109_RICERCA_ETF_20261115.zip`,238,685,250 bytes.

Archive SHA256: `fc89eadb3ee94f6ade1dceafbd43707f5bac518bb889e4dc350f55de32e2281e`.

Persistent reference: `libfile_78a392f2bcac81919669f3fd5cbee900`.

Extract the following originals, preserving their bytes, into the indicated paths relative to `olc111`:

| Archive source | Required destination | SHA256 |
|---|---|---|
| `olc109/source/data/XETRA_EUR_ETF.npz` | `../olc110/source/data/XETRA_EUR_ETF.npz` | `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96` |
| `olc109/data/LIQUIDITY.npz` | `../olc110/data/LIQUIDITY.npz` | `b95fa3d67837fa06c5705aa4aea09807d396464ab44ec1671031d797b57f4485` |

The immutable parent research commit is `5752452e565037b790a4099c9d5f8de9d5788509` in `AM1975MA/Test`. The OLC110 source dependencies are present there and their exact identities are recorded in both OLC111 freezes.

## Official Cboe source snapshot

Archive: `OLC111_DATI_CBOE_20261116.zip`,274,801 bytes.

Archive SHA256: `0f47af693f32aa0ccf8026f1f46bdfa61e2576215871a6ed8ffab77371ba3b13`.

Persistent reference: `libfile_cb23eb1902ec8191a177a4bb13cae149`.

Restore `data/raw/` and the source manifest into `olc111/`; check each archive entry against `RESTORE_MANIFEST.json`. This snapshot contains five downloaded series, of which **only VIX, VIX9D and VIX3M are used**. VVIX and SKEW remain unused.

| Used source | SHA256 |
|---|---|
| `data/raw/VIX_History.csv` | `d4e2b1199951501b7757814b6e1c2356394922a7ea8ef16d85c3a4596e6e2c2d` |
| `data/raw/VIX9D_History.csv` | `c29cb0795e2ab676e5d1fdc42cb3f53d8e66c3daf36a492ec0192f033e690874` |
| `data/raw/VIX3M_History.csv` | `6fa2ba5f8b85bf62a98ba14acf5e03c712298dffe534d3c73998e21db1248a4b` |

The official URL pattern is `https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYMBOL}_History.csv`; source URLs, download timestamps, sizes and hashes are in `data/CBOE_SOURCE_MANIFEST.json`. A later download may have a different vintage and is not a byte-identical substitute. The script rejects mismatching inputs rather than silently mixing revised data with existing labels.

No credentials are included or required for the public source URLs. Access to the archived snapshots follows the owner's existing file permissions.
