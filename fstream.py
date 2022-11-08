#
# Streamlit demo for financial analysis
#

# disable SSL warnings
from math import nan
import urllib3
urllib3.disable_warnings( urllib3.exceptions.InsecureRequestWarning )

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import altair as alt
import talib  as ta
import os
import json
import datetime as dt
import fschart  as fc
import argparse
import investpy

from yahooquery import Ticker
from numpy import NaN, isnan

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

_PARAM_FILE      = "param.json"

_DEFAULT_PORT    = { 'SPY':50, 'QQQ':50 }
_DEFAULT_MARKET  = [ '^IXIC', '^GSPC', '^DJI', 'KRW=X' ]
_DEFAULT_FUTURE  = [ 'NQ=F', 'ES=F', 'YM=F', 'KRW=X' ]
_DEFAULT_BENCH   = [ 'SPY' ]
_RSI_THRESHOLD_L =   30
_RSI_THRESHOLD_H =   70
_CCI_THRESHOLD_L = -100
_CCI_THRESHOLD_H =  100
_US_BOND         = [ 'U.S. 30Y', 'U.S. 10Y', 'U.S. 5Y', 'U.S. 3Y', 'U.S. 2Y', 'U.S. 1Y', 'U.S. 6M', 'U.S. 3M', 'U.S. 1M' ]

sector_tickers = {
    'XLK': 'Technology',
    'XLC': 'Communication Services',
    'XLY': 'Consumer Cyclical',
    'XLF': 'Financial',
    'XLV': 'Healthcare',
    'XLP': 'Consumer Defensive',
    'XLI': 'Industrials',
    'XLRE':'Real Estate',
    'XLE': 'Energy', 
    'XLU': 'Utilities', 
    'XLB': 'Materials',
    'SPY': 'S&P 500',
}
fix_ticker_list = {
    'BRK.B': 'BRK-B',
    'LIN.L': 'LIN',
}
attr_list = { 
    'regularMarketChangePercent':'Change(%)', 
    'regularMarketPrice':'Price',
    'trailingPE':'P/E',
    'fiftyTwoWeekHigh':'52W_H(%)',
    'fiftyTwoWeekLow':'52W_L(%)',
}
attr_color_scheme = {
    'Change(%)': [ [ -10000,   0, 'red'   ], [  0, 10000, 'green' ] ],
    'Price'    : [ ],
    'P/E'      : [ [ -10000,  30, 'green' ], [ 70, 10000, 'red'   ] ],
    '52W_L(%)' : [                           [ 30, 10000, 'red'   ] ],
    '52W_H(%)' : [ [ -10000, -15, 'red'   ] ],
    'RSI(14)'  : [ [ -10000,  30, 'red'   ], [ 70, 10000, 'red'   ] ],
    'CCI(14)'  : [ [ -10000,-100, 'red'   ], [100, 10000, 'red'   ] ],
    'Alloc'    : [ ],
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
    '1W' : [  7,  0 ],    
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
params = {
    'port'   : _DEFAULT_PORT,
    'market' : _DEFAULT_MARKET,
    'future' : _DEFAULT_FUTURE,
    'bench'  : _DEFAULT_BENCH,
    'RSI_L'  : _RSI_THRESHOLD_L,
    'RSI_H'  : _RSI_THRESHOLD_H,
    'CCI_L'  : _CCI_THRESHOLD_L,
    'CCI_H'  : _CCI_THRESHOLD_H,
    'market_period' : '12H',
    'sector_period' : '1W',
    'gain_period'   : '3M',
    'stock_period'  : '3M',
    'pattern_period': '3M',
}

# -------------------------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------------------------

def fetch_tickers( tickers ):
    
    _list = Ticker( tickers, verify=False, asynchronous=True )
    return _list

@st.experimental_singleton
def fetch_info( _tickers_list, cache_key ):
    
    info = {}
    info[ 'price'     ] = _tickers_list.price
    info[ 'summary'   ] = _tickers_list.summary_detail
    info[ 'fund'      ] = _tickers_list.fund_holding_info

    return info

@st.experimental_singleton
def fetch_history( _ticker_list, period, interval, cache_key ):

    _hist = _ticker_list.history( period, interval, adj_timezone=False )
    return _hist

@st.experimental_singleton
def fetch_bond_history( bond_name, cache_key ):

    to_date = dt.datetime.today()
    fr_date = to_date - dt.timedelta( days = 365 )
    to_date_str = to_date.strftime( '%d/%m/%Y' )
    fr_date_str = fr_date.strftime( '%d/%m/%Y' )

    result = investpy.get_bond_historical_data( bond=bond_name, from_date=fr_date_str, to_date=to_date_str )

    return result

@st.experimental_singleton
def fill_table( _st_info, _st_hist, cache_key ):

    # from Ticker.price
    df1 = pd.DataFrame( _st_info['price'] )
    rm_index = [ x for x in df1.index if x not in attr_list ]
    df1.drop( rm_index, inplace=True )

    # from Ticker.summary_detail
    df2 = pd.DataFrame( _st_info['summary'] )
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
    for key in df.columns:
        if _st_info[ 'price' ][ key ][ 'quoteType' ] != 'ETF': continue
        try:
            df.loc[ 'P/E' ][ key ] = _st_info[ 'fund' ][ key ][ 'equityHoldings' ][ 'priceToEarnings' ]
        except:
            try:
                df.loc[ 'P/E' ][ key ] = NaN
            except:
                pass

    # allocation
    alo_list = []
    for key in df.columns:
        alo_list.append( params['port'][key] )

    # add rows
    df.loc[ 'RSI(14)' ] = rsi_list
    df.loc[ 'CCI(14)' ] = cci_list
    df.loc[ 'Alloc'   ] = alo_list

    return df.transpose()

def is_market_open():
    
    t=Ticker( params['market'][0], verify=False )
    if t.price[ params['market'][0] ]['marketState'] == 'REGULAR': return True
    return False

def highlight_color( s ):

    try:
        # get color scheme for given column
        scheme = attr_color_scheme[ s.name ]

        # build color list
        color_list = []
        for elem in s:
            color_str = ''
            for cond in scheme:
                if elem >= cond[0] and elem < cond[1]: color_str = f'color: {cond[2]}'
            color_list.append( color_str )
    except:
        color_list = [ '' ]*len( s )

    return color_list

def save_params( _params ):

    # save to session
    st.session_state.params = _params

    # save to file
    if args.nosave == False:
        with open( _PARAM_FILE, 'w' ) as fp:
            json.dump( _params, fp, indent=4 )

    return

def load_params():

    # check if first load, load from file
    if 'params' not in st.session_state:
        with open( _PARAM_FILE, 'r' ) as fp:
            ret = json.load( fp )
        st.session_state.params = ret
    # otherwise, load from session
    else:
        ret = st.session_state.params

    return ret

def get_num_points( index, delta ):

    last = index[-1]
    d    = dt.timedelta( days  = delta[0] )
    h    = dt.timedelta( hours = delta[1] )
    num_points = len( index [ index >= ( last - d - h ) ] )

    # at least 2
    return max( 2, num_points )

def get_shortcut( port_dic ):

    # short-cut variables
    port_key = list( port_dic )
    port_str = ' '.join( [ f'{k}:{v}' for k, v in port_dic.items() ] )

    return port_key, port_str

def get_port_gains():

    # get latest value
    last_price = [ stock_info['price'][option]['regularMarketPrice'] for option in port_k ]

    # portfolio allocation
    port_alloc  = [ params['port'][option] for option in port_k ]
    total_alloc = sum( port_alloc )
        
    # for each time delta
    time_delta = [ 1, 7, 30, 90, 180, 365 ]
    port_gain  = []
    for delta in time_delta:

        # get historic price
        if delta != 1:
            prev_price = []
            for option in port_k:
                num_points = get_num_points( stock_hist['close'][option].index, [ delta, 0 ] )
                while isnan( stock_hist['close'][option][-num_points] ): num_points-=1
                prev_price.append( stock_hist['close'][option][-num_points] )
        else:
            prev_price = [ stock_info['price'][option]['regularMarketPreviousClose'] for option in port_k ]

        # compute gains
        prev_gain = []
        for index, price in enumerate( prev_price ):
            prev_gain.append( ( last_price[index]-price )/price*port_alloc[index]/total_alloc )

        # final gain
        port_gain.append( sum( prev_gain )*100. )
    
    return port_gain

def get_gain_str( name, value ):

    if value >=0:
        style_str = f'<button style="border-radius:10px;border:none;color:green;background-color:palegreen">'
        temp_str  = f'<b>{name}</b>: {style_str} &#8593;&nbsp;{value:.2f}%</button>'
    else:
        style_str = f'<button style="border-radius:10px;border:none;color:red;background-color:mistyrose">'
        temp_str = f'<b>{name}</b>: {style_str} &#8595;&nbsp;{-value:.2f}%</button>'

    temp_str += '&nbsp;'*5
    return temp_str

def fix_ticker( ticker ):

    if ticker in fix_ticker_list: return fix_ticker_list[ ticker ]
    return ticker

# -------------------------------------------------------------------------------------------------
# Functions (Callbacks)
# -------------------------------------------------------------------------------------------------

def cb_ticker_list():
    _temp_list = st.session_state.tickerlist.split( ' ' )
    
    # validate tickers
    _ticker_list = {}
    for elem in _temp_list:

        # split ticker and allocation
        elem_sub = elem.split(':')
        _ticker = elem_sub[0].upper()
        if len( elem_sub ) > 1: _alloc = int( elem_sub[1] )
        else: _alloc = 1

        # store
        _ticker_list[ _ticker ] = _alloc

    # validate
    _verified_list = {}
    t = Ticker( list( _ticker_list ), verify=False, validate=True )
    for k in _ticker_list:
        if k in t.symbols:
            _verified_list[ k ] = _ticker_list[ k ]

    # if nothing, use default port
    if _verified_list == {}: _verified_list = _DEFAULT_PORT

    # update session string
    _temp_k, _temp_str = get_shortcut( _verified_list )
    st.session_state.tickerlist = _temp_str

    # store to parameter and save
    params[ 'port' ] = _verified_list
    save_params( params )

    # clear portfolio cache
    st.session_state.stcnt += 1

def cb_gain_period():
    params[ 'gain_period' ] = st.session_state.gainperiod
    save_params( params )

def cb_rsi_margin():
    params[ 'RSI_L' ] = st.session_state.rsimargin[0]
    params[ 'RSI_H' ] = st.session_state.rsimargin[1]
    save_params( params )

def cb_cci_margin():
    params[ 'CCI_L' ] = st.session_state.ccimargin[0]
    params[ 'CCI_H' ] = st.session_state.ccimargin[1]
    save_params( params )

def cb_stock_period():
    params[ 'stock_period' ] = st.session_state.stockperiod
    save_params( params )

def cb_market_period():
    params[ 'market_period' ] = st.session_state.marketperiod
    save_params( params )

def cb_sector_period():
    params[ 'sector_period' ] = st.session_state.sectorperiod
    save_params( params )

def cb_pattern_period():
    params[ 'pattern_period' ] = st.session_state.patternperiod
    save_params( params )

# -------------------------------------------------------------------------------------------------
# Commandline arguments
# -------------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser( description='Financial Stream' )
parser.add_argument( '--nosave', action='store_true' )
args = parser.parse_args()

# -------------------------------------------------------------------------------------------------
# Layout
# -------------------------------------------------------------------------------------------------

# add sidebar
st.sidebar.title( 'Financial Stream' )
menu   = st.sidebar.radio( "MENU", ( 'Market', 'Sector', 'Portfolio', 'Stock', 'Pattern', 'Bond' ) )
button = st.sidebar.button( "Clear Cache" )
if button: st.experimental_singleton.clear() 
st.sidebar.markdown( '[**GitHub**](https://github.com/hurumi/financial-stream)' )

# -------------------------------------------------------------------------------------------------
# Fetch data
# -------------------------------------------------------------------------------------------------

# check if param file exists
if os.path.isfile( _PARAM_FILE ): params=load_params()
else: save_params( params )

# get shortcut variables
port_k, port_str = get_shortcut( params['port'] )

# portfolio and benchmark
stock_list = fetch_tickers( port_k )
bench_list = fetch_tickers( params['bench'] )

# -------------------------------------------------------------------------------------------------
# Clear cache counter if necessary
# -------------------------------------------------------------------------------------------------

if 'stcnt' not in st.session_state: st.session_state.stcnt = 0
if 'mkcnt' not in st.session_state: st.session_state.mkcnt = 0
if 'secnt' not in st.session_state: st.session_state.secnt = 0
if 'bdcnt' not in st.session_state: st.session_state.bdcnt = 0

# -------------------------------------------------------------------------------------------------
# Portfolio
# -------------------------------------------------------------------------------------------------

if menu == 'Portfolio':

    st.subheader( 'Portfolio' )

    # enter ticker list
    ticker_str = st.text_input( "Ticker list", port_str,
                                key='tickerlist',
                                on_change=cb_ticker_list )

    if st.button( 'Refresh' ):
        st.session_state.stcnt += 1

    # ---------------------------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------------------------

    # historical prices
    stock_info = fetch_info   ( stock_list, cache_key='stock'+str(st.session_state.stcnt) )
    stock_hist = fetch_history( stock_list, period='1y', interval='1d', cache_key='stock'+str(st.session_state.stcnt) )

    # fill data from stock list
    df  = fill_table( stock_info, stock_hist, cache_key="stock"+str(st.session_state.stcnt) ).sort_values( by='RSI(14)' )
    dfs = df.style.apply( highlight_color, axis=0 ).format( "{:.2f}", na_rep='-' )
    st.write( dfs )

    # get portfolio gains (1D, 1W, 1M, 3M, 6M, 1Y)
    port_gain_list = get_port_gains()
    port_gain_str  = get_gain_str( '1D', port_gain_list[0] )
    port_gain_str += get_gain_str( '1W', port_gain_list[1] )
    port_gain_str += get_gain_str( '1M', port_gain_list[2] )
    port_gain_str += get_gain_str( '3M', port_gain_list[3] )
    port_gain_str += get_gain_str( '6M', port_gain_list[4] )
    port_gain_str += get_gain_str( '1Y', port_gain_list[5] )
    st.markdown( '<p style="text-align: center;">'+port_gain_str+'</p>', True )

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
        bench_hist = fetch_history( bench_list,  period='1y', interval='1d', cache_key='bench'+str(st.session_state.stcnt) )

        # compute min number of points
        _temp_list =  [ get_num_points( bench_hist['close'][ elem ].index, period_delta[period] ) for elem in params['bench'] ]
        _temp_list += [ get_num_points( stock_hist['close'][ elem ].index, period_delta[period] ) for elem in params['port' ] ]
        num_points = min( _temp_list )

        # draw chart
        bt_src, bt_inf = fc.get_btest_source( stock_hist, bench_hist, num_points, params )
        btest_chart    = fc.get_btest_chart ( bt_src )
        st.altair_chart( btest_chart, use_container_width=True )

        # write basic statistics
        bt_inf_s = bt_inf.style.format( "{:.2f}", na_rep='-' )
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
        dfs = oversold_df.style.apply( highlight_color, axis=0 ).format( "{:.2f}", na_rep='-' )
        st.write( dfs )

    # sub title
    st.markdown( '##### Overbought' )
    st.text( f'RSI>{rsi_H} and CCI>{cci_H}' )
    if len( overbought_df.index ) > 0:
        dfs = overbought_df.style.apply( highlight_color, axis=0 ).format( "{:.2f}", na_rep='-' )
        st.write( dfs )

# -------------------------------------------------------------------------------------------------
# Each stock
# -------------------------------------------------------------------------------------------------

if menu == 'Stock':

    # sub title
    st.subheader( 'Stock chart' )

    # stock selector
    option = st.selectbox( 'Ticker', port_k, key='stockticker' )

    # points selector
    values = [ '1M', '3M', '6M', '1Y' ]
    period = st.selectbox( 'Period', values, 
                            index=values.index( params['stock_period'] ),
                            key='stockperiod',
                            on_change=cb_stock_period )

    # historical prices
    stock_info = fetch_info    ( stock_list, cache_key='stock'+str(st.session_state.stcnt) )
    stock_hist = fetch_history ( stock_list, period='1y', interval='1d', cache_key='stock'+str(st.session_state.stcnt) )
    num_points = get_num_points( stock_hist['close'][option].index, period_delta[period] )

    # detailed information (JSON format)
    with st.expander( "Detailed information" ):
        
        st.text( 'Summary detail' )
        st.json( stock_info[ 'summary' ][ option ] )

        if stock_info['price'][ option ][ 'quoteType' ] == 'ETF':
            st.text( 'ETF data' )
            st.json( stock_info[ 'fund' ][ option ] )

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
        ma120_flag  = st.checkbox( 'MA120 (BLUE)' )

    # price chart
    price_chart = fc.get_candle_chart( stock_info, stock_hist, option, num_points )

    # bollinger band chart
    if bband_flag:
        price_chart = fc.get_bband_chart( stock_hist, option, num_points ) + price_chart

    # MA20 chart
    if ma20_flag:
        price_chart = fc.get_ma_chart( stock_hist, option, num_points, 20, 'red' ) + price_chart

    # MA60 chart
    if ma60_flag:
        price_chart = fc.get_ma_chart( stock_hist, option, num_points, 60, 'green' ) + price_chart

    # MA120 chart
    if ma120_flag:
        price_chart = fc.get_ma_chart( stock_hist, option, num_points, 120, 'blue' ) + price_chart

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
        st.session_state.mkcnt += 1

    # check market open
    if is_market_open():
        ticker_list = params[ 'market' ]
    else:
        ticker_list = params[ 'future' ]

    # load historical data
    market_list = fetch_tickers( ticker_list )
    market_info = fetch_info   ( market_list, cache_key='market'+str(st.session_state.mkcnt) )
    market_hist = fetch_history( market_list, period='5d', interval='5m', cache_key='market'+str(st.session_state.mkcnt) )

    # if unmatched (when market changes), change cache key and try again
    if set( market_info['price'].keys() ) != set( ticker_list ):
        st.session_state.mkcnt += 1
        market_info = fetch_info   ( market_list, cache_key='market'+str(st.session_state.mkcnt) )
        market_hist = fetch_history( market_list, period='5d', interval='5m', cache_key='market'+str(st.session_state.mkcnt) )

    # draw
    for option in ticker_list:
        num_points = get_num_points( market_hist['close'][option].index, period_delta[period] )
        market_chart = fc.get_price_chart( market_info, market_hist, option, num_points, True )
        st.altair_chart( market_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Sector
# -------------------------------------------------------------------------------------------------

if menu == 'Sector':

    # sub title
    st.subheader( 'Sector chart' )

    # points selector
    values = [ '1D', '1W', '1M', '3M', '6M', '1Y' ]
    period = st.selectbox( 'Period', values, 
                            index=values.index( params['sector_period'] ), 
                            key="sectorperiod", 
                            on_change=cb_sector_period )

    if st.button( 'Refresh' ):
        st.session_state.secnt += 1

    # load historical data
    sector_list = fetch_tickers( sector_tickers )
    sector_info = fetch_info   ( sector_list, cache_key='sector'+str(st.session_state.secnt) )
    sector_hist = fetch_history( sector_list, period='1y', interval='1d', cache_key='sector'+str(st.session_state.secnt) )

    # compute duration
    num_points  = get_num_points( sector_hist['close'][list(sector_tickers)[0]].index, period_delta[period] )
    
    # get source
    se_chart = fc.get_sector_chart( sector_info, sector_hist, num_points )

    # draw
    st.altair_chart( se_chart, use_container_width=True )

    # stock selector
    r_sector_tickers = { v:k for k, v in sector_tickers.items() }
    option = st.selectbox( 'Sector', r_sector_tickers, key='stockticker' )

    # top holdings performance
    with st.expander( 'Top holdings performance' ):
        r_option = r_sector_tickers[option]

        # fix_ticker fixes ticker name error in yahoo finance (temporary solution)
        top_tickers = [ fix_ticker( elem['symbol'] ) for elem in sector_info['fund'][r_option]['holdings'] ]
        top_list = fetch_tickers( top_tickers ) 
        top_info = fetch_info   ( top_list, cache_key=r_option+str(st.session_state.secnt) )
        top_hist = fetch_history( top_list, period='1y', interval='1d', cache_key=r_option+str(st.session_state.secnt) )

        # get source
        to_chart = fc.get_sector_chart( top_info, top_hist, num_points )

        # draw
        st.altair_chart( to_chart, use_container_width=True )

    # sector chart
    se_chart = fc.get_price_chart( sector_info, sector_hist, r_sector_tickers[option], num_points )

    # draw
    st.altair_chart( se_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Pattern
# -------------------------------------------------------------------------------------------------

if menu == 'Pattern':

    # historical prices
    stock_info = fetch_info    ( stock_list, cache_key='stock'+str(st.session_state.stcnt) )
    stock_hist = fetch_history ( stock_list, period='1y', interval='1d', cache_key='stock'+str(st.session_state.stcnt) )
    num_points = get_num_points( stock_hist['close'][port_k[0]].index, period_delta['1M'] )

    # ---------------------------------------------------------------------------------------------
    # Pattern logs for all portfolio stocks
    # ---------------------------------------------------------------------------------------------

    st.subheader( 'Pattern logs (1M)' )
    
    col1, col2 = st.columns(2)
    with col1:
        # bullish patterns
        st.markdown( '##### Bullish patterns' )
        _temp        = []
        for option in port_k:
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
        for option in port_k:
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
    option = st.selectbox( 'Ticker', port_k, key='stockticker' )

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
    price_chart = fc.get_candle_chart( stock_info, stock_hist, option, num_points )

    # bullish chart
    price_chart += fc.get_pattern_chart( bullish_histo, bearish_histo )

    # draw
    st.altair_chart( price_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Bond
# -------------------------------------------------------------------------------------------------

if menu == 'Bond':

    # sub title
    st.subheader( 'US Bond' )

    col1, col2 = st.columns( 2 )
    # Bond selector
    values = _US_BOND
    bond1  = col1.selectbox( 'Bond 1', values, index=1, key="bond1period" )
    bond2  = col2.selectbox( 'Bond 2', values, index=4, key="bond2period" )

    # points selector
    values = [ '1Y', '6M', '3M', '1M' ]
    period = st.selectbox( 'Period', values, key="bondperiod" )

    if st.button( 'Refresh' ):
        st.session_state.bdcnt += 1

    # fetch data
    df1 = fetch_bond_history( bond1, cache_key='bond1'+str(st.session_state.bdcnt) )
    df2 = fetch_bond_history( bond2, cache_key='bond2'+str(st.session_state.bdcnt) )

    # get charts
    num_points1 = get_num_points( df1['Close'].index, period_delta[period] )
    num_points2 = get_num_points( df2['Close'].index, period_delta[period] )
    num_points  = min( num_points1, num_points2 )
    ch1, ch2    = fc.get_bond_chart( [ bond1, df1 ], [ bond2, df2 ], num_points )

    # draw
    st.altair_chart( ch1, use_container_width=True )
    st.altair_chart( ch2, use_container_width=True )