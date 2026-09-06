"""Reproducible Eurostat sector VARs. Run from anywhere; no API key required."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR

ROOT = Path(__file__).resolve().parent
BASE = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
QUERIES = {
    'accounts': ('namq_10_a10', dict(geo='DE', sinceTimePeriod='1999-Q1', s_adj='SCA')),
    'compensation': ('namq_10_a10', dict(geo='DE', sinceTimePeriod='1999-Q1', unit='CP_MEUR', na_item='D1')),
    'employment': ('namq_10_a10_e', dict(geo='DE', sinceTimePeriod='1999-Q1', s_adj='SCA', unit='THS_PER')),
    'capital': ('nama_10_nfa_st', dict(geo='DE', sinceTimePeriod='1999', asset10='N11N', unit='CLV20_MEUR')),
    'investment': ('namq_10_gdp', dict(geo='DE', sinceTimePeriod='1999-Q1', s_adj='SCA', unit='CLV20_MEUR', na_item='P51G')),
    'regions': ('nama_10r_3empers', dict(geo=['DE'+x for x in '123456789ABCDEFG'], sinceTimePeriod='2020')),
}
SECTORS = {'TOTAL':'Germany', 'A':'Agriculture', 'B-E':'Industry', 'F':'Construction', 'G-I':'Trade, transport & hospitality', 'J':'Information & communication', 'K':'Finance', 'L':'Real estate', 'M_N':'Business services', 'O-Q':'Public services, education & health', 'R-U':'Other services'}

def decode(d):
    """Decode sparse JSON-stat in declared dimension order, including missing cells."""
    ids, sizes = d['id'], d['size']
    codes = [[k for k,v in sorted(d['dimension'][dim]['category']['index'].items(), key=lambda x:x[1])] for dim in ids]
    values = d.get('value', {})
    items = enumerate(values) if isinstance(values,list) else values.items()
    rows=[]
    for flat,value in items:
        if value is None: continue
        indices=np.unravel_index(int(flat), sizes)
        rows.append({**{dim:codes[i][indices[i]] for i,dim in enumerate(ids)}, 'value':value})
    return pd.DataFrame(rows)

def series(frame, **filters):
    for key,value in filters.items(): frame=frame[frame[key]==value]
    if frame['time'].duplicated().any(): raise ValueError(f'Ambiguous series: {filters}')
    return frame.set_index('time')['value'].sort_index().astype(float)

def estimate(frames, code):
    a,e=frames['accounts'],frames['employment']
    y=series(a,nace_r2=code,na_item='B1G',unit='CLV20_MEUR')
    nominal=series(a,nace_r2=code,na_item='B1G',unit='CP_MEUR')
    pay=series(frames['compensation'],nace_r2=code,s_adj='SA')
    employees=series(e,nace_r2=code,na_item='SAL_DC')
    employment=series(e,nace_r2=code,na_item='EMP_DC')
    prices=nominal/y
    levels=pd.concat({'output':y,'employment':employment,'wages':pay/employees*1000/prices,'prices':prices},axis=1).dropna()
    levels.index=pd.PeriodIndex(levels.index,freq='Q')
    levels=levels.asfreq('Q').reindex(pd.period_range(levels.index.min(),levels.index.max(),freq='Q'))
    if levels.isna().any().any() or (levels<=0).any().any(): raise ValueError(f'Missing/nonpositive observations for {code}')
    growth=100*np.log(levels).diff().dropna()
    # AIC is selected on training data only; the last 12 quarters remain held out.
    train=growth.iloc[:-12]
    lag=max(1,VAR(train).select_order(maxlags=4).selected_orders['aic'])
    fit_train=VAR(train).fit(lag)
    predictions=[]; actual=[]; naive=[]
    for i in range(len(train),len(growth)):
        history=growth.iloc[:i]
        rolling=VAR(history).fit(lag)
        predictions.append(rolling.forecast(history.values[-lag:],1)[0])
        actual.append(growth.iloc[i].values); naive.append(history.mean().values)
    rmse=np.sqrt(np.mean((np.array(predictions)-actual)**2,axis=0))
    naive_rmse=np.sqrt(np.mean((np.array(naive)-actual)**2,axis=0))
    fit=VAR(growth).fit(lag)
    # Generalized reduced-form impulses, normalized to a 1 percentage point innovation.
    # These are correlated forecast errors, NOT identified fiscal/productivity shocks.
    covariance=np.asarray(fit.sigma_u)
    innovations=covariance / np.diag(covariance)[None,:]
    irf=np.einsum('hij,jk->hik',fit.ma_rep(24),innovations)
    capital=series(frames['capital'],nace_r2=code)
    capital=capital.dropna()
    alpha=float(np.clip(1-(pay/nominal).tail(20).median(),.05,.8))
    return dict(name=SECTORS[code], sample=[str(levels.index[0]),str(levels.index[-1])], nobs=int(fit.nobs), lag=int(lag),
        stable=bool(fit.is_stable()), aic=float(fit.aic), whiteness_p=float(fit.test_whiteness(nlags=8).pvalue),
        rmse=rmse.tolist(), benchmark_rmse=naive_rmse.tolist(), variables=list(levels.columns),
        history=dict(time=levels.index.astype(str).tolist(), **{k:levels[k].tolist() for k in levels}),
        capital=dict(time=capital.index.tolist(),value=capital.tolist()),
        capital_share=alpha, irf=irf.tolist(), coefficients=fit.coefs.tolist(), covariance=covariance.tolist())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');parser.add_argument('--output',type=Path,default=ROOT/'model.json');args=parser.parse_args()
    sources=[];frames={}; raw={}
    for name,(dataset,params) in QUERIES.items():
        url=BASE+dataset+'?'+urlencode(dict(lang='EN',**params),doseq=True)
        path=ROOT/'data'/f'{name}.json'
        if args.refresh:
            with urlopen(url,timeout=120) as response: data=json.load(response)
            if not data.get('value'): raise ValueError(f'Empty source: {url}')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))
        data=json.loads(path.read_text());raw[name]=data;frames[name]=decode(data)
        if frames[name].empty: raise ValueError(f'Empty source: {name}')
        sources.append(dict(name=name,dataset=dataset,url=url,updated=data.get('updated')))
    models={}; excluded={}
    for code in SECTORS:
        try: models[code]=estimate(frames,code)
        except (ValueError,np.linalg.LinAlgError) as error: excluded[code]=str(error)
    if 'TOTAL' not in models: raise ValueError(excluded)
    regional=frames['regions'];regional=regional[(regional.wstatus=='EMP') & (regional.unit=='THS')]
    regions=[]
    for geo,group in regional.groupby('geo'):
        for year in sorted(group.time.unique(),reverse=True):
            g=group[group.time==year].set_index('nace_r2')['value']
            sectors=[s for s in SECTORS if s!='TOTAL']
            if all(s in g.index and g[s]>0 for s in sectors):
                total=float(sum(g[s] for s in sectors))
                regions.append(dict(code=geo,name=raw['regions']['dimension']['geo']['category']['label'][geo],year=year,employment=total,weights={s:float(g[s]/total) for s in sectors}));break
    investment=series(frames['investment'])
    output=dict(generated=datetime.now(timezone.utc).isoformat(),sources=sources,sectors=models,excluded=excluded,regions=regions,investment=dict(time=investment.index.tolist(),value=investment.tolist()))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(output,allow_nan=False))
    print(f'Estimated {len(models)} sectors; {len(regions)} states. Excluded: {excluded}')

if __name__=='__main__': main()
