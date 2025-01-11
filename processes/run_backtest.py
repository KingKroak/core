import os
import pprint

import feedparser

import numpy as np
import pandas as pd
from fontTools.ttLib.tables.otTraverse import dfs_base_table

from utils.gmail import GmailService

DATA_PATH = '../data/yahoo'

CONTRACT_MULTIPLIERS = {
    'ZN=F': 1000,
    'ES=F': 50,
}

def load_prices(syms):
    csv_files = [f for f in os.listdir(DATA_PATH) if f.endswith('.csv')]

    # load files
    dfs = {}
    for csv_file in csv_files:
        symbol = os.path.splitext(csv_file)[0]
        file_path = os.path.join(DATA_PATH, csv_file)
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        dfs[symbol] = df.set_index('date').sort_index()

    # splice the two series together
    prices = {}
    for sym in syms:
        px1 = dfs[f'{sym}_daily']['close']
        px1.index += pd.Timedelta(days=1)
        px2 = dfs[f'{sym}_intraday']['close']

        px = pd.concat([px1[px1.index < px2.index.min()], px2])
        prices[sym] = px

    return prices

def run(params):

    syms = ['^VIX', 'CL=F', 'ES=F', 'ZN=F', 'AUDUSD=X']
    prices = load_prices(syms)

    z_scores = pd.DataFrame()
    daily_vols = pd.DataFrame()

    for sym in syms:
        px = prices[sym]

        daily_px = px.resample('B').last()
        daily_vol = daily_px.diff().ewm(halflife=params['vol_hl']).std()

        signal_raw = px - px.ewm(halflife=pd.Timedelta(days=params['mean_hl']), times=px.index).mean()
        signal_vol = signal_raw.resample('D').last().ewm(halflife=params['signal_vol_hl']).std()
        signal_vol = signal_vol.asof(signal_raw.index)
        signal = (signal_raw / signal_vol).clip(-2, 2)

        z_scores[sym] = signal
        daily_vols[sym] = daily_vol

    # pnl
    px_es = prices['ES=F']
    px_zn = prices['ZN=F']
    px_zn = px_zn.asof(px_es.index)

    # generate signal targets
    # declining vol and bond yields is good for equities
    equity_score = 1 + params['eq_score_wt'] * (-z_scores['^VIX'] + z_scores['ZN=F']) / 2
    # declining inflation (i.e. oil) is good for bonds
    bond_score = 1 + params['fi_score_wt'] * (-z_scores['CL=F'])

    risk_scaler = 1 / params['risk_scaler']
    tgt_holding_es = equity_score / (daily_vols['ES=F'] * risk_scaler * CONTRACT_MULTIPLIERS.get('ES=F'))
    tgt_holding_es = tgt_holding_es.asof(px_es.index)
    tgt_holding_zn = bond_score / (daily_vols['ZN=F'] * risk_scaler * CONTRACT_MULTIPLIERS.get('ZN=F'))
    tgt_holding_zn = tgt_holding_zn.asof(px_zn.index)

    returns = px_zn.diff().shift(-1) * tgt_holding_zn + px_es.diff().shift(-1) * tgt_holding_es
    daily_rets = returns.resample('B').sum()
    print(daily_rets.std())
    print(daily_rets.mean())


if __name__ == '__main__':

    params = {
        'vol_hl': 20,
        'mean_hl': 10,
        'signal_vol_hl': 180,
        'eq_score_wt': 0.5,
        'fi_score_wt': 0.5,
        'risk_scaler': 10000,
    }

    pprint.pp(params)
    run(params)