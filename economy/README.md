# German economy model

The companion static dashboard lives in `political-dynamics/tim-umbach/economy-lab.html`.
This directory owns the data snapshots and reproducible estimation pipeline.

```bash
python -m pip install -r economy/requirements.txt
python economy/estimate.py --output ../tim-umbach/data/economy-model.json
python -m unittest discover -s economy -p 'test_*.py'
# Download a new official vintage (no key):
python economy/estimate.py --refresh --output ../tim-umbach/data/economy-model.json
```

The pipeline fits eleven VARs (Germany plus non-overlapping A*10 sectors) to
1999 onward quarterly log growth of real GVA, persons employed, real compensation
per employee, and the GVA deflator. Compensation uses SA; output and employment
use SCA. Pay is D1/SAL_DC deflated by nominal/real GVA, not household CPI real wages.
Missing observations are not filled. No quarterly capital observations are invented:
capital appears as annual net fixed assets (`N11N`, chain-linked 2020 million EUR).

AIC chooses 1–4 lags using the sample before the 12-quarter holdout. Expanding-window
one-step forecasts are compared with historical mean growth; final coefficients
are refit on the full sample. The exported snapshot includes sample, covariance,
coefficients, stability, residual whiteness and RMSE. Generalized innovations use
Sigma[:,j]/Sigma[j,j], not a recursive causal ordering. VARs are not identified
policy models. No parameter uncertainty interval is claimed.

The browser offers an optional neoclassical-synthesis closure conditional on VAR
output: partial adjustment of prices/nominal wages, Cobb–Douglas labour demand,
and calibrated capital accumulation. It does not estimate a structural DSGE or
ECB reaction function. Fixed nominal exchange rates and fixed foreign prices are
scenario assumptions. Capital share uses a clipped recent non-compensation share;
inertia (0.65), investment accelerator (2), quarterly I/K (0.015) and depreciation
(0.0125) are calibrated. Household optimization, fiscal accounts, international
trade equations and endogenous productivity are outside this implementation.

Regional projections weight separate sector employment responses by each state's
latest complete set of A*10 employment shares. They are composition exposures,
not estimated regional VARs, and do not reconcile to the independently fitted
aggregate model. Selecting a sector holds all other sectors at baseline.

Eurostat JSON-stat snapshots are in `data/`; exact queries and source update dates
are exported. Source series can be revised. Investment data are supplied for future
estimation extensions; the current capital scenario explicitly uses calibrated I/K.
All source definitions: https://ec.europa.eu/eurostat/cache/metadata/en/nama10_esms.htm
API: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started/api
