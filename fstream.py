#
# Streamlit demo for financial analysis
#

# disable SSL warnings
from asyncio.windows_events import NULL
from numpy import NaN, save
from simplejson import OrderedDict
import urllib3
urllib3.disable_warnings( urllib3.exceptions.InsecureRequestWarning )

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import requests
import streamlit as st
import pandas as pd
import altair as alt
import talib  as ta
import os
import json
import datetime as dt
import fschart  as fc

from yahooquery import Ticker

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

_PARAM_FILE      = "param.json"

_DEFAULT_PORT    = [ 'SPY', 'QQQ' ]
_DEFAULT_MARKET  = [ '^IXIC', '^GSPC', '^DJI', 'KRW=X' ]
_DEFAULT_FUTURE  = [ 'NQ=F', 'ES=F', 'YM=F', 'KRW=X' ]
_DEFAULT_BENCH   = [ 'SPY' ]
_RSI_THRESHOLD_L =   30
_RSI_THRESHOLD_H =   70
_CCI_THRESHOLD_L = -100
_CCI_THRESHOLD_H =  100

attr_list = { 
    'regularMarketChangePercent':'Change(%)', 
    'regularMarketPrice':'Price',
    'trailingPE':'P/E',
    'fiftyTwoWeekHigh':'52W_H(%)',
    'fiftyTwoWeekLow':'52W_L(%)',
}
period_delta = {
    '1M' : [  30, 0 ],
    '3M' : [  90, 0 ],
    '6M' : [ 180, 0 ],
    '1Y' : [ 365, 0 ],
    '6H' : [  0,  6 ],
    '12H': [  0, 12 ],
    '1D' : [  1,  0 ],
    '5D' : [  5,  0 ],
}
params = {
    'port'   : _DEFAULT_PORT,
    'market' : _DEFAULT_MARKET,
    'future' : _DEFAULT_FUTURE,
    'bench'  : _DEFAULT_BENCH,
    'RSI_L'  : _RSI_THRESHOLD_L,
    'RSI_H'  : _RSI_THRESHOLD_H,
    'CCI_L'  : _CCI_THRESHOLD_L,
    'CCI_H'  : _CCI_THRESHOLD_H,
    'market_period' : '6H',
    'gain_period'   : '1M',
    'stock_period'  : '1M',
    'pattern_period': '1M'
}
bullish_pattern = [ 
    'CDLHAMMER', 
    'CDLINVERTEDHAMMER',
    'CDLENGULFING',
    'CDLPIERCING',
    'CDLMORNINGSTAR',
    'CDL3WHITESOLDIERS'
]
bearish_pattern = [ 
    'CDLHANGINGMAN', 
    'CDLSHOOTINGSTAR',
    'CDLENGULFING',
    'CDLEVENINGSTAR',
    'CDL3BLACKCROWS',
    'CDLDARKCLOUDCOVER'
]

# -------------------------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------------------------

@st.experimental_singleton
def fetch_tickers( tickers ):
    
    _list = Ticker( tickers, verify=False, asynchronous=True )
    return _list

@st.experimental_singleton
def fetch_history( _ticker_list, period, interval, cache_key ):

    _hist = _ticker_list.history( period, interval, adj_timezone=False )
    return _hist

@st.experimental_singleton
def fill_table( _st_list, _st_hist, cache_key ):

    # from Ticker.price
    df1 = pd.DataFrame( _st_list.price )
    rm_index = [ x for x in df1.index if x not in attr_list ]
    df1.drop( rm_index, inplace=True )

    # from Ticker.summary_detail
    df2 = pd.DataFrame( _st_list.summary_detail )
    rm_index = [ x for x in df2.index if x not in attr_list ]
    df2.drop( rm_index, inplace=True )

    # concat
    df = pd.concat( [ df1, df2 ] )
    
    # compute RSI & CCI
    rsi_list = {}
    cci_list = {}
    for key in df.columns:
        
        # compute RSI
        rsi = ta.RSI( _st_hist['close'][ key ] )[-1]   
        rsi_list[ key ] = rsi
        
        # compute CCI
        cci = ta.CCI( _st_hist['high'][ key ], _st_hist['low'][ key ], _st_hist['close'][ key ] )[-1] 
        cci_list[ key ] = cci

    # rename column
    for key, val in attr_list.items():
        df.rename( index = { key:val }, inplace=True )

    # compute 52W_H & 52W_L
    for key in df.columns:
        # 52W_L
        try:
            new_entry  = df.loc[ 'Price'][ key ] - df.loc[ '52W_L(%)' ][ key ]
            new_entry /= df.loc[ '52W_L(%)' ][ key ]
            df.loc[ '52W_L(%)' ][ key ] = new_entry
        except:
            df.loc[ '52W_L(%)' ][ key ] = NaN
        
        # 52W_H
        try:
            new_entry  = df.loc[ 'Price'][ key ] - df.loc[ '52W_H(%)' ][ key ]
            new_entry /= df.loc[ '52W_H(%)' ][ key ]
            df.loc[ '52W_H(%)' ][ key ] = new_entry
        except:
            df.loc[ '52W_H(%)' ][ key ] = NaN

    # compute percentage
    for key in df.index:
        if '(%)' in key: df.loc[ key ] *= 100

    # replace ETF P/E
    fund_info = _st_list.fund_equity_holdings
    for key in df.columns:
        if _st_list.price[ key ][ 'quoteType' ] != 'ETF': continue
        try:
            df.loc[ 'P/E' ][ key ] = fund_info[ key ][ 'priceToEarnings' ]
        except:
            df.loc[ 'P/E' ][ key ] = NaN

    # add two rows
    df.loc[ 'RSI(14)' ] = rsi_list
    df.loc[ 'CCI(14)' ] = cci_list

    return df.transpose()

def is_market_open():
    _temp = Ticker( 'aapl', verify=False )
    if _temp.price['aapl']['marketState'] == 'REGULAR': return True
    return False

def highlight_negative( s ):

    is_negative = s < 0
    return [ 'color: red' if i else '' for i in is_negative ]

def save_params():
    with open( _PARAM_FILE, 'w' ) as fp:
        json.dump( params, fp, indent=4 )
    return

def load_params():
    with open( _PARAM_FILE, 'r' ) as fp:
        ret = json.load( fp )
    return ret

def get_num_points( index, delta ):

    last = index[-1]
    d    = dt.timedelta( days  = delta[0] )
    h    = dt.timedelta( hours = delta[1] )
    num_points = len( index [ index > ( last - d - h ) ] )

    return num_points

# -------------------------------------------------------------------------------------------------
# Functions (Callbacks)
# -------------------------------------------------------------------------------------------------

def cb_ticker_list():
    _temp_list = st.session_state.tickerlist.split( ' ' )
    
    # validate tickers
    _verified_list = []
    for elem in _temp_list:
        t = Ticker( elem, verify=False, validate=True )
        if t.price != {}: _verified_list.append( elem )

    # if nothing, use default port
    if _verified_list == []: _verified_list = _DEFAULT_PORT

    # update session string
    st.session_state.tickerlist = ' '.join( _verified_list )

    # store to parameter and save, then clear cache
    params[ 'port' ] = _verified_list
    save_params()
    st.experimental_singleton.clear()   # clear cache

def cb_gain_period():
    params[ 'gain_period' ] = st.session_state.gainperiod
    save_params()

def cb_rsi_margin():
    params[ 'RSI_L' ] = st.session_state.rsimargin[0]
    params[ 'RSI_H' ] = st.session_state.rsimargin[1]
    save_params()

def cb_cci_margin():
    params[ 'CCI_L' ] = st.session_state.ccimargin[0]
    params[ 'CCI_H' ] = st.session_state.ccimargin[1]
    save_params()

def cb_stock_period():
    params[ 'stock_period' ] = st.session_state.stockperiod
    save_params()

def cb_market_period():
    params[ 'market_period' ] = st.session_state.marketperiod
    save_params()

def cb_pattern_period():
    params[ 'pattern_period' ] = st.session_state.patternperiod
    save_params()

# -------------------------------------------------------------------------------------------------
# Layout
# -------------------------------------------------------------------------------------------------

# add sidebar
st.sidebar.title( 'Financial Stream' )
menu   = st.sidebar.radio( "MENU", ( 'Market', 'Portfolio', 'Stock', 'Pattern' ) )
button = st.sidebar.button( "Clear Cache" )
if button: st.experimental_singleton.clear() 

# -------------------------------------------------------------------------------------------------
# Fetch data
# -------------------------------------------------------------------------------------------------

# check if param file exists
if os.path.isfile( _PARAM_FILE ): params=load_params()
else: save_params()

# portfolio and benchmark
stock_list   = fetch_tickers    ( params['port'  ] )
bench_list   = fetch_tickers    ( params['bench' ] )

# according to market open
if is_market_open():
    market_list = fetch_tickers( params['market'] )
else:
    market_list = fetch_tickers( params['future'] )

# -------------------------------------------------------------------------------------------------
# Portfolio
# -------------------------------------------------------------------------------------------------

if menu == 'Portfolio':

    st.subheader( 'Portfolio' )

    # enter ticker list
    ticker_str = st.text_input( "Ticker list", ' '.join( params['port'] ),
                                key='tickerlist',
                                on_change=cb_ticker_list )

    if st.button( 'Refresh' ):
        st.experimental_singleton.clear()

    # ---------------------------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------------------------

    # historical prices
    stock_hist = fetch_history( stock_list,  period='1y', interval='1d', cache_key='stock' )

    # fill data from stock list
    df  = fill_table( stock_list, stock_hist, cache_key="stock" ).sort_values( by='RSI(14)' )
    dfs = df.style.apply( highlight_negative, axis=1 ).format( precision=2, na_rep='-' )
    st.write( dfs )

    # ---------------------------------------------------------------------------------------------
    # Backtest
    # ---------------------------------------------------------------------------------------------

    with st.expander( "Accumulated Gain (%)" ):
        # points selector
        values = [ '1M', '3M', '6M', '1Y' ]
        period = st.selectbox( 'Period', values, 
                                index=values.index( params['gain_period'] ),
                                key='gainperiod',
                                on_change=cb_gain_period )

        # load data
        bench_hist = fetch_history( bench_list,  period='1y', interval='1d', cache_key='bench' )
        num_points = get_num_points( bench_hist['close'][ params['bench'][0] ].index, period_delta[period] )

        # draw chart
        bt_src, bt_inf = fc.get_btest_source( stock_hist, bench_hist, num_points, params )
        btest_chart    = fc.get_btest_chart ( bt_src )
        st.altair_chart( btest_chart, use_container_width=True )

        # write basic statistics
        bt_inf_s = bt_inf.style.format( precision=2, na_rep='-' )
        st.dataframe( bt_inf_s )

    # ---------------------------------------------------------------------------------------------
    # Oversold & Overbought
    # ---------------------------------------------------------------------------------------------

    st.subheader( 'Over stocks' )

    # range selector
    col1, col2 = st.columns(2)
    with col1:
        # RSI margin
        rsi_L, rsi_H = st.select_slider(
            'Normal RSI Range',
            options=[ i for i in range( 0, 105, 5 ) ],
            value = (params['RSI_L'], params['RSI_H']),
            key='rsimargin',
            on_change=cb_rsi_margin )
    with col2:
        # CCI margin
        cci_L, cci_H = st.select_slider(
            'Normal CCI Range',
            options=[ i for i in range( -200, 210, 10 ) ],
            value = (params['CCI_L'], params['CCI_H']),
            key='ccimargin',
            on_change=cb_cci_margin )

    # generate oversold and overbought data
    oversold_idx  = df['RSI(14)'] < rsi_L
    oversold_idx *= df['CCI(14)'] < cci_L
    oversold_df   = df[ oversold_idx ]

    overbought_idx  = df['RSI(14)'] > rsi_H
    overbought_idx *= df['CCI(14)'] > cci_H
    overbought_df   = df[ overbought_idx ]

    # sub title
    st.markdown( '##### Oversold' )
    st.text( f'RSI<{rsi_L} and CCI<{cci_L}' )
    if len( oversold_df.index ) > 0:
        dfs = oversold_df.style.apply( highlight_negative, axis=1 ).format( precision=2, na_rep='-' )
        st.write( dfs )

    # sub title
    st.markdown( '##### Overbought' )
    st.text( f'RSI>{rsi_H} and CCI>{cci_H}' )
    if len( overbought_df.index ) > 0:
        dfs = overbought_df.style.apply( highlight_negative, axis=1 ).format( precision=2, na_rep='-' )
        st.write( dfs )

# -------------------------------------------------------------------------------------------------
# Each stock
# -------------------------------------------------------------------------------------------------

if menu == 'Stock':

    # sub title
    st.subheader( 'Stock chart' )

    # stock selector
    option = st.selectbox( 'Ticker', params['port'], key='stockticker' )

    # points selector
    values = [ '1M', '3M', '6M', '1Y' ]
    period = st.selectbox( 'Period', values, 
                            index=values.index( params['stock_period'] ),
                            key='stockperiod',
                            on_change=cb_stock_period )

    # historical prices
    stock_hist = fetch_history( stock_list,  period='1y', interval='1d', cache_key='stock' )
    num_points = get_num_points( stock_hist['close'][option].index, period_delta[period] )

    # detailed information (JSON format)
    with st.expander( "Detailed information" ):
        
        st.text( 'Summary detail' )
        st.json( stock_list.summary_detail[ option ] )

        st.text( 'Financial data' )
        if stock_list.price[ option ][ 'quoteType' ] == 'EQUITY':
            st.json( stock_list.financial_data[ option ] )
        else:
            st.json( stock_list.fund_holding_info[ option ] )

    # ---------------------------------------------------------------------------------------------
    # price history chart
    # ---------------------------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bband_flag = st.checkbox( 'Bollinger band' )
    with col2:
        ma20_flag  = st.checkbox( 'MA20 (RED)' )
    with col3:
        ma60_flag  = st.checkbox( 'MA60 (GREEN)' )
    with col4:
        ma120_flag  = st.checkbox( 'MA120 (ORANGE)' )

    # price chart
    price_chart = fc.get_candle_chart( stock_list, stock_hist, option, num_points )

    # bollinger band chart
    if bband_flag:
        price_chart += fc.get_bband_chart( stock_hist, option, num_points )

    # MA20 chart
    if ma20_flag:
        price_chart += fc.get_ma_chart( stock_hist, option, num_points, 20, 'red' )

    # MA60 chart
    if ma60_flag:
        price_chart += fc.get_ma_chart( stock_hist, option, num_points, 60, 'green' )

    # MA120 chart
    if ma120_flag:
        price_chart += fc.get_ma_chart( stock_hist, option, num_points, 120, 'orange' )

    # draw
    st.altair_chart( price_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # RSI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    rsi_chart = fc.get_rsi_chart( stock_hist, option, num_points, params )

    # draw
    st.altair_chart( rsi_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # CCI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    cci_chart = fc.get_cci_chart( stock_hist, option, num_points, params )

    # draw
    st.altair_chart( cci_chart, use_container_width=True )    

    # ---------------------------------------------------------------------------------------------
    # MACD history chart
    # ---------------------------------------------------------------------------------------------
    
    # macd chart
    macd_chart, macd_hist_chart = fc.get_macd_charts( stock_hist, option, num_points )

    # draw
    st.altair_chart( macd_chart,      use_container_width=True )
    st.altair_chart( macd_hist_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Market
# -------------------------------------------------------------------------------------------------

if menu == 'Market':

    # sub title
    st.subheader( 'Market chart' )

    # points selector
    values = [ '6H', '12H', '1D', '5D' ]
    period = st.selectbox( 'Period', values, 
                            index=values.index( params['market_period'] ), 
                            key="marketperiod", 
                            on_change=cb_market_period )

    if st.button( 'Refresh' ):
        st.experimental_singleton.clear()

    # check market open
    if is_market_open():
        ticker_list = params[ 'market' ]
    else:
        ticker_list = params[ 'future' ]

    # load historical data
    market_hist = fetch_history( market_list, period='5d', interval='5m', cache_key='market' )

    # draw
    for option in ticker_list:
        num_points = get_num_points( market_hist['close'][option].index, period_delta[period] )
        market_chart = fc.get_price_chart( market_list, market_hist, option, num_points )
        st.altair_chart( market_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Pattern
# -------------------------------------------------------------------------------------------------

if menu == 'Pattern':

    # historical prices
    stock_hist = fetch_history( stock_list,  period='1y', interval='1d', cache_key='stock' )
    num_points = get_num_points( stock_hist['close'][params['port'][0]].index, period_delta['1M'] )

    # ---------------------------------------------------------------------------------------------
    # Pattern logs for all portfolio stocks
    # ---------------------------------------------------------------------------------------------

    st.subheader( 'Pattern logs (1M)' )
    
    col1, col2 = st.columns(2)
    with col1:
        # bullish patterns
        st.markdown( '##### Bullish patterns' )
        _temp        = []
        for option in params['port']:
            for method in bullish_pattern:
                data = getattr( ta, method )( stock_hist['open'][option][-num_points:], 
                                    stock_hist['high'][option][-num_points:], 
                                    stock_hist['low'][option][-num_points:], 
                                    stock_hist['close'][option][-num_points:] )
                for d, v in data.items():
                    if v>0: _temp.append( f'{d}: [{option:5}] {method}' )
        _temp.sort()
        st.code( '\n'.join( _temp ) )
        
    with col2:
        # bearish patterns
        st.markdown( '##### Bearish patterns' )
        _temp = []        
        for option in params['port']:
            for method in bearish_pattern:
                data = getattr( ta, method )( stock_hist['open'][option][-num_points:], 
                                    stock_hist['high'][option][-num_points:], 
                                    stock_hist['low'][option][-num_points:], 
                                    stock_hist['close'][option][-num_points:] )
                for d, v in data.items():
                    if v<0: _temp.append( f'{d}: [{option:5}] {method}' )
        _temp.sort()
        st.code( '\n'.join( _temp ) )

    # ---------------------------------------------------------------------------------------------
    # Pattern chart for selected stock
    # ---------------------------------------------------------------------------------------------

    # sub title
    st.subheader( 'Pattern chart' )

    # stock selector (share key with stock menu)
    option = st.selectbox( 'Ticker', params['port'], key='stockticker' )

    # points selector
    values = [ '1M', '3M', '6M', '1Y' ]
    period = st.selectbox( 'Period', values,
                            index=values.index( params['pattern_period'] ),
                            key="patternperiod",
                            on_change=cb_pattern_period )

    num_points = get_num_points( stock_hist['close'][option].index, period_delta[period] )

    # bullish data
    _bullish_histo = stock_hist['close'][option][-num_points:].copy()    
    for idx, method in enumerate( bullish_pattern ):
        _temp = getattr( ta, method )( stock_hist['open'][option][-num_points:], 
                            stock_hist['high'][option][-num_points:], 
                            stock_hist['low'][option][-num_points:], 
                            stock_hist['close'][option][-num_points:] )
        if idx == 0: data  = _temp
        else:        data += _temp
    
    _bullish_histo[ data <= 0 ] = 0
    bullish_histo = _bullish_histo[ _bullish_histo > 0 ]

    # bearish data
    _bearish_histo = stock_hist['close'][option][-num_points:].copy()    
    for idx, method in enumerate( bearish_pattern ):
        _temp = getattr( ta, method )( stock_hist['open'][option][-num_points:], 
                            stock_hist['high'][option][-num_points:], 
                            stock_hist['low'][option][-num_points:], 
                            stock_hist['close'][option][-num_points:] )
        if idx == 0: data  = _temp
        else:        data += _temp                            
    
    _bearish_histo[ data >= 0 ] = 0
    bearish_histo = _bearish_histo[ _bearish_histo > 0 ]

    # price chart
    price_chart = fc.get_candle_chart( stock_list, stock_hist, option, num_points )

    # bullish chart
    price_chart += fc.get_pattern_chart( bullish_histo, bearish_histo )

    # draw
    st.altair_chart( price_chart, use_container_width=True )