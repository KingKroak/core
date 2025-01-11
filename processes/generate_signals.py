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

    syms = ['^VIX', 'CL=F', 'ES=F', 'ZN=F', 'AUDUSD=X']
    raw_prices = load_prices(syms)

    detail_df = []

    last_updated_times = {}
    last_updated_values = {}

    prices = pd.DataFrame()

    for sym in syms:
        ts = raw_prices[sym]
        ts.name = sym
        last_updated_times[sym] = ts.index.values[-1]
        last_updated_values[sym] = ts.values[-1]
        prices = prices.join(ts, how='outer')

    prices = prices.ffill()
    daily_px = prices.resample('B').last()
    daily_vol = daily_px.diff().ewm(halflife=params['vol_hl']).std()
    ann_pct_vol = np.log(daily_px).diff().ewm(halflife=params['vol_hl']).std() * np.sqrt(252) * 100.0

    price_change = prices - prices.ewm(halflife=pd.Timedelta(days=params['mean_hl']), times=prices.index).mean()
    price_change_vol = price_change.resample('B').last().ewm(halflife=params['signal_vol_hl']).std()
    price_change_vol = price_change_vol.asof(price_change.index)
    z_score = (price_change / price_change_vol).clip(-2, 2)

    for sym in syms:
        record = (
            sym,
            last_updated_times[sym],
            last_updated_values[sym],
            z_score[sym].values[-1],
            ann_pct_vol[sym].values[-1],
            daily_vol[sym].values[-1],
        )

        detail_df.append(record)

        print()
        print(sym)
        print(f'last time: {record[1]}')
        print(f'last price: {record[2]}')
        print(f'z_score: {record[3]}')
        print(f'ann_vol: {record[4]}')
        print(f'ret_vol: {record[5]}')

    # generate signal targets
    # declining vol and bond yields is good for equities
    equity_scores = 1 + params['eq_score_wt'] * (-z_score['^VIX'] + z_score['ZN=F']) / 2
    # declining inflation (i.e. oil) is good for bonds
    bond_scores = 1 + params['fi_score_wt'] * (-z_score['CL=F'])

    risk_scaler = 1 / params['risk_scaler']
    vols = daily_vol.asof(equity_scores.index)
    tgt_holdings_es = equity_scores / (vols['ES=F'] * risk_scaler * CONTRACT_MULTIPLIERS.get('ES=F'))
    tgt_holdings_zn = bond_scores / (vols['ZN=F'] * risk_scaler * CONTRACT_MULTIPLIERS.get('ZN=F'))

    # run backtest to determine the expected std. dev.

    returns = 0
    returns += prices['ZN=F'].diff().shift(-1) * CONTRACT_MULTIPLIERS.get('ZN=F') * tgt_holdings_zn
    returns += prices['ES=F'].diff().shift(-1) * CONTRACT_MULTIPLIERS.get('ES=F') * tgt_holdings_es

    daily_rets = returns.resample('B').sum()
    daily_portfolio_vols = daily_rets.ewm(halflife=90).std()

    print()
    print('Daily Portfolio Return Std (USD)')
    print(daily_rets.std())
    print('Daily Portfolio Return Mean (USD)')
    print(daily_rets.mean())
    print('IR')
    print(daily_rets.mean() / daily_rets.std() * 16)
    print('Daily Portfolio Vol (USD)')
    print(daily_portfolio_vols.values[-1])

    print()
    print('ES target')
    print(tgt_holdings_es.values[-1])
    print('ZN target')
    print(tgt_holdings_zn.values[-1])

    aud_usd_rate = last_updated_values['AUDUSD=X']

    summary_df = [
        ('ES', tgt_holdings_es.values[-1], equity_scores, vols['ES=F'].values[-1]),
        ('ZN', tgt_holdings_zn.values[-1], bond_scores, vols['ZN=F'].values[-1]),
    ]

    summary2_df = [
        ('Expected Daily Risk (USD)', daily_portfolio_vols.values[-1]),
        ('AUD/USD FX Rate', aud_usd_rate),
        ('Risk Scaler', params['risk_scaler'])
    ]

    # create reports
    detail_df = pd.DataFrame.from_records(
        detail_df, index='sym', columns=['sym', 'last_timestamp', 'last_close', 'z_score', 'ann_vol', 'daily_vol'])
    summary_df = pd.DataFrame.from_records(
        summary_df, index='sym', columns=['sym', 'tgt_pos', 'score', 'usd_vol'])
    summary2_df = pd.DataFrame.from_records(
        summary2_df, index='sym', columns=['sym', 'value'])
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
        {summary2_df.to_html()}
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
        'risk_scaler': 3000,
    }

    pprint.pp(params)
    run(params)