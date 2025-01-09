import os

import numpy as np
import pandas as pd

DATA_PATH = 'data/yahoo'

def run():
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
    for sym in ['^VIX', 'CL=F', 'ES=F', 'ZN=F']:
        px1 = dfs[f'{sym}_daily']['close']
        px1.index += pd.Timedelta(days=1)
        px2 = dfs[f'{sym}_intraday']['close']

        px = pd.concat([px1[px1.index < px2.index.min()], px2])

        signal_raw = px - px.ewm(halflife=pd.Timedelta(days=10), times=px.index).mean()
        signal_vol = signal_raw.resample('D').last().ewm(halflife=180).std()
        signal_vol = signal_vol.asof(signal_raw.index)
        signal = (signal_raw / signal_vol)  # .clip(-2, 2)

        print(sym)
        print(signal.tail(1))

        if sym in {'ES=F', 'ZN=F'}:
            daily_px = px.resample('B').last()
            ann_vol = np.log(daily_px).diff().ewm(halflife=20).std() * 100 * np.sqrt(252)
            print(ann_vol.tail(1))



if __name__ == '__main__':
    run()