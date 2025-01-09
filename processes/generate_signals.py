import os

import numpy as np
import pandas as pd

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

def run():
    syms = ['^VIX', 'CL=F', 'ES=F', 'ZN=F']
    prices = load_prices(syms)

    z_score = {}
    usd_vols = {}
    last_updated_time = {}

    for sym in syms:
        px = prices[sym]

        daily_px = px.resample('B').last()
        daily_vol = daily_px.diff().ewm(halflife=20).std()
        ann_vol = np.log(daily_px).diff().ewm(halflife=20).std() * np.sqrt(252) * 100.0

        signal_raw = px - px.ewm(halflife=pd.Timedelta(days=10), times=px.index).mean()
        signal_vol = signal_raw.resample('D').last().ewm(halflife=180).std()
        signal_vol = signal_vol.asof(signal_raw.index)
        signal = (signal_raw / signal_vol)  # .clip(-2, 2)

        print()
        print(sym)
        print(f'last time: {px.index.values[-1]}')
        print(f'last price: {px.values[-1]}')
        print(f'z_score: {signal.values[-1]}')
        print(f'ann_vol: {ann_vol.values[-1]}')
        print(f'ret_vol: {daily_vol.values[-1]}')

        z_score[sym] = signal.values[-1]
        usd_vols[sym] = daily_vol.values[-1] * CONTRACT_MULTIPLIERS.get(sym, 1)
        last_updated_time[sym] = signal.index.values[-1]

    # generate signal targets
    # declining vol and bond yields is good for equities
    equity_score = 1 + 0.5 * (-z_score['^VIX'] + z_score['ZN=F']) / 2
    # declining inflation (i.e. oil) is good for bonds
    bond_score = 1 + 0.5 * (-z_score['CL=F'])

    risk_scaler = 10000
    target_equity = equity_score / usd_vols['ES=F'] * risk_scaler
    target_bond = bond_score / usd_vols['ZN=F'] * risk_scaler

    print()
    print('ES target')
    print(target_equity)
    print('ZN target')
    print(target_bond)



if __name__ == '__main__':
    run()