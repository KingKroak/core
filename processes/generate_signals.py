import os
import pprint

import feedparser

import numpy as np
import pandas as pd

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

def get_quote_of_the_day():
    feed_url = "https://www.brainyquote.com/link/quotebr.rss"
    feed = feedparser.parse(feed_url)
    quote_str = ''
    for entry in feed.entries:
        quote_str = f'{entry.title} - {entry.description}'
        break
    return quote_str


def get_news_html():
    rss_url = "https://feeds.content.dowjones.io/public/rss/mw_topstories"
    feed = feedparser.parse(rss_url)

    news_str = ''
    for entry in feed.entries:
        news_str += f'<b>{entry.title}</b>'
        news_str += f'<p>{entry.link}</p>'
        news_str += f'<p>{entry.description}</p>'

    return news_str

def run(params: dict):

    syms = ['^VIX', 'CL=F', 'ES=F', 'ZN=F']
    prices = load_prices(syms)

    z_score = {}
    usd_vols = {}
    last_updated_time = {}

    detail_df = []

    for sym in syms:
        px = prices[sym]

        daily_px = px.resample('B').last()
        daily_vol = daily_px.diff().ewm(halflife=params['vol_hl']).std()
        ann_vol = np.log(daily_px).diff().ewm(halflife=params['vol_hl']).std() * np.sqrt(252) * 100.0

        signal_raw = px - px.ewm(halflife=pd.Timedelta(days=params['mean_hl']), times=px.index).mean()
        signal_vol = signal_raw.resample('D').last().ewm(halflife=params['signal_vol_hl']).std()
        signal_vol = signal_vol.asof(signal_raw.index)
        signal = (signal_raw / signal_vol).clip(-2, 2)

        record = (
            sym,
            px.index.values[-1],
            px.values[-1],
            signal.values[-1],
            ann_vol.values[-1],
            daily_vol.values[-1],
        )

        detail_df.append(record)

        print()
        print(sym)
        print(f'last time: {record[1]}')
        print(f'last price: {record[2]}')
        print(f'z_score: {record[3]}')
        print(f'ann_vol: {record[4]}')
        print(f'ret_vol: {record[5]}')

        z_score[sym] = signal.values[-1]
        usd_vols[sym] = daily_vol.values[-1] * CONTRACT_MULTIPLIERS.get(sym, 1)
        last_updated_time[sym] = signal.index.values[-1]

    # generate signal targets
    # declining vol and bond yields is good for equities
    equity_score = 1 + params['eq_score_wt'] * (-z_score['^VIX'] + z_score['ZN=F']) / 2
    # declining inflation (i.e. oil) is good for bonds
    bond_score = 1 + params['fi_score_wt'] * (-z_score['CL=F'])

    risk_scaler = params['risk_scaler']
    target_equity = equity_score / usd_vols['ES=F'] * risk_scaler
    target_bond = bond_score / usd_vols['ZN=F'] * risk_scaler

    print()
    print('ES target')
    print(target_equity)
    print('ZN target')
    print(target_bond)

    summary_df = [
        ('ES', target_equity, equity_score, usd_vols['ES=F']),
        ('ZN', target_bond, bond_score, usd_vols['ZN=F']),
    ]

    # create reports
    detail_df = pd.DataFrame.from_records(
        detail_df, index='sym', columns=['sym', 'last_timestamp', 'last_close', 'z_score', 'ann_vol', 'daily_vol'])
    summary_df = pd.DataFrame.from_records(
        summary_df, index='sym', columns=['sym', 'tgt_pos', 'score', 'usd_vol'])

    date_str = pd.Timestamp.utcnow().strftime('%Y.%m.%d')

    quote_of_the_day = get_quote_of_the_day()
    news_html = get_news_html()

    html_content = f"""
    <html>
      <body>
        <h2>Signal Report {date_str}</h2>
        <p>Generated at {pd.Timestamp.utcnow()}</p>
        <br></br>
        <h4>Quote of the day</h4>
        {quote_of_the_day}
        <h4>Summary</h4>
        {summary_df.to_html()}
        <h4>Details</h4>
        {detail_df.to_html()}
        <h4>Latest Headlines</h4>
        {news_html}
      </body>
    </html>
    """

    base_path = os.getcwd()
    if base_path.endswith('processes'):
        base_path = base_path.replace(f'processes', '')

    gmail_service = GmailService(f'{base_path}/utils/token.json', f'{base_path}/utils/credentials.json')
    gmail_service.send_email(
        'AtraxaBot',
        'atraxa.investments@gmail.com',
        f'Strategy Update - {date_str}',
        html_content,
        message_format='html'
    )


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