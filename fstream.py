#
# Streamlit demo for financial analysis
#

# disable SSL warnings
from asyncio.windows_events import NULL
from numpy import save
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

abbr_list = { 
    '^IXIC':'NASDAQ Composite',
    '^GSPC':'S&P 500',
    '^DJI':'DOW Jones Average',    
    'NQ=F':'NASDAQ Futures',
    'ES=F':'S&P 500 Futures',
    'YM=F':'DOW Jones Futures',
    'KRW=X':'USD/KRW',
}
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
def fetch_history( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval, adj_timezone=False )
    return _hist

@st.experimental_singleton
def fetch_history_alt( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval, adj_timezone=False )
    return _hist

def get_usdkrw():

    _temp = requests.get( "https://api.exchangerate-api.com/v4/latest/USD", verify=False )
    exchange_rate = _temp.json()

    return exchange_rate['rates']['KRW']

def is_market_open():
    _temp = Ticker( 'aapl', verify=False )
    if _temp.price['aapl']['marketState'] == 'REGULAR': return True
    return False

def check_oversold( entry, rsi_L, cci_L ):

    if entry[ 'RSI(14)' ] > rsi_L:
        return False

    if entry[ 'CCI(14)' ] > cci_L:
        return False

    return True

def check_overbought( entry, rsi_H, cci_H ):

    if entry[ 'RSI(14)' ] < rsi_H:
        return False      

    if entry[ 'CCI(14)' ] < cci_H:
        return False            

    return True

def highlight_negative(s):

    is_negative = s < 0
    return ['color: red' if i else '' for i in is_negative]

def get_price_chart( st_list, st_hist, ticker, num_points ):

        hist = st_hist[ 'close' ][ ticker ]

        source1 = pd.DataFrame( {
            'Date': hist.index[-num_points:],
            'Price': hist[-num_points:].values
        } )

        ch = alt.Chart( source1 ).mark_line().encode(
            x=alt.X( 'Date:T' ),
            y=alt.Y( 'Price:Q', scale=alt.Scale( zero=False )  ),
            tooltip = [ 'Date', 'Price' ]
        )

        prev_close = st_list.price[ ticker ][ 'regularMarketPreviousClose' ]
        cur_price  = st_list.price[ ticker ][ 'regularMarketPrice'         ]

        source2 = pd.DataFrame( {
            'Date': hist.index[-num_points:],
            'Price': prev_close
        } )

        delta = ( cur_price - prev_close ) / prev_close * 100.
        title = abbr_list[ ticker ] if ticker in abbr_list else ticker
        prev = alt.Chart( source2 ).mark_line().encode(
            x=alt.X( 'Date:T' ),
            y=alt.Y( 'Price:Q' ),
            color=alt.value("#FFAA00"),
            tooltip = [ 'Date', 'Price' ]
        ).properties( title = f'{title}: {cur_price:.2f} ({delta:.2f}%)' )

        return ch+prev

def get_candle_chart( st_list, st_hist, ticker, num_points ):

        hist = st_hist[ 'close' ][ ticker ]

        # make source
        source1 = pd.DataFrame( {
            'Date':  hist.index[-num_points:],
            'High':  st_hist['high'][ticker][-num_points:].values,
            'Low':   st_hist['low'][ticker][-num_points:].values,
            'Open':  st_hist['open'][ticker][-num_points:].values,
            'Close': st_hist['close'][ticker][-num_points:].values
        } )

        # conditional color for bar
        open_close_color = alt.condition("datum.Open <= datum.Close",
                                          alt.value( "#06982d" ),
                                          alt.value( "#ae1325" ) )

        # base
        base = alt.Chart( source1 ).encode(
            x = alt.X( 'Date:T' ),
            color=open_close_color,
            tooltip = [ 'Date', 'Close' ]
        )

        # rule
        rule = base.mark_rule().encode(
            alt.Y(
                'Low:Q',
                title = 'Price',
                scale = alt.Scale( zero=False ),
            ),
            alt.Y2('High:Q')
        )

        # bar
        bar = base.mark_bar().encode(
            alt.Y('Open:Q'),
            alt.Y2('Close:Q')
        )

        # final candlestick
        ch = rule + bar

        # draw previous close line
        prev_close = st_list.price[ ticker ][ 'regularMarketPreviousClose' ]
        cur_price  = st_list.price[ ticker ][ 'regularMarketPrice'         ]

        source2 = pd.DataFrame( {
            'Date': hist.index[-num_points:],
            'Price': prev_close
        } )

        delta = ( cur_price - prev_close ) / prev_close * 100.
        title = abbr_list[ ticker ] if ticker in abbr_list else ticker
        prev = alt.Chart( source2 ).mark_line().encode(
            x=alt.X( 'Date:T' ),
            y=alt.Y( 'Price:Q' ),
            color=alt.value("#FFAA00"),
            tooltip = [ 'Date', 'Price' ]
        ).properties( title = f'{title}: {cur_price:.2f} ({delta:.2f}%)' )

        return ch+prev        

def get_bband_chart( st_hist, ticker, num_points ):

    bband_up, bband_mid, bband_low = ta.BBANDS( st_hist['close'][ ticker ], 20, 2 )
    source1 = pd.DataFrame( {
        'Metric': 'BBAND_UPPER',
        'Date'  : bband_up.index[-num_points:],
        'Price' : bband_up[-num_points:].values
    } )
    source2 = pd.DataFrame( {
        'Metric': 'BBAND_MIDDLE',
        'Date'  : bband_mid.index[-num_points:],
        'Price' : bband_mid[-num_points:].values
    } )
    source3 = pd.DataFrame( {
        'Metric': 'BBAND_LOWER',
        'Date'  : bband_low.index[-num_points:],
        'Price' : bband_low[-num_points:].values
    } )
    source = pd.concat( [ source1, source2, source3 ] )
    ch = alt.Chart( source ).mark_line( strokeDash=[2,3] ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.Color( 'Metric', legend=None ),
    )
    return ch

def get_ma_chart( st_hist, ticker, num_points, period, colorstr ):

    ma = ta.SMA( st_hist['close'][ ticker ], period )
    source = pd.DataFrame( {
        'Metric': f'MA{period}',
        'Date'  : ma.index[-num_points:],
        'Price' : ma[-num_points:].values
    } )
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.value( colorstr ),
        strokeWidth = alt.value( 1 ),
    )
    return ch

def get_rsi_chart( st_hist, ticker, num_points ):

    rsi_hist = ta.RSI( st_hist['close'][ ticker ] )
    source = pd.DataFrame( {
        'Date': rsi_hist.index[-num_points:],
        'RSI': rsi_hist[-num_points:].values
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        tooltip = [ 'Date', 'RSI' ]
    ).properties( title = f'RSI(14): {rsi_hist[-1]:.2f}' )
    source_up = pd.DataFrame( {
        'Date': rsi_hist.index[-num_points:],
        'RSI': params['RSI_H']
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
        'Date': rsi_hist.index[-num_points:],
        'RSI': params['RSI_L']
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn

def get_cci_chart( st_hist, ticker, num_points ):

    cci_hist = ta.CCI( st_hist['high'][ ticker ], st_hist['low'][ ticker ], st_hist['close'][ ticker ] )
    source = pd.DataFrame( {
        'Date': cci_hist.index[-num_points:],
        'CCI': cci_hist[-num_points:].values
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        tooltip = [ 'Date', 'CCI' ]
    ).properties( title = f'CCI(14): {cci_hist[-1]:.2f}' )
    source_up = pd.DataFrame( {
        'Date': cci_hist.index[-num_points:],
        'CCI': params['CCI_H']
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
        'Date': cci_hist.index[-num_points:],
        'CCI': params['CCI_L']
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn    

def get_macd_charts( st_hist, ticker, num_points ):

    macd, macdsignal, macdhist = ta.MACD( st_hist['close'][ ticker ] )
    source1 = pd.DataFrame( {
        'Metric': 'MACD(12)',
        'Date'  : macd.index[-num_points:],
        'Value' : macd[-num_points:].values
    } )
    source2 = pd.DataFrame( {
        'Metric': 'MACD(26)',
        'Date'  : macdsignal.index[-num_points:],
        'Value' : macdsignal[-num_points:].values
    } )
    source3 = pd.DataFrame( {
        'Metric': 'MACDHIST',
        'Date'  : macdhist.index[-num_points:],
        'Hist'  : macdhist[-num_points:].values
    } )
    source = pd.concat( [ source1, source2 ] )

    ch1 = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Value', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Value' ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    ).properties( title = 'MACD' )
    ch2 = alt.Chart( source3 ).mark_bar().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Hist' ),
        tooltip = [ 'Date', 'Hist' ],
        color=alt.condition(
            alt.datum.Hist > 0,
            alt.value("green"),  # The positive color
            alt.value("red")  # The negative color
        )        
    )
    return ch1, ch2

def get_btest_chart( po_hist, be_hist, num_points ):

    # get benchmark data
    _source = []    
    for ticker in params['bench']:

        data = be_hist[ 'close' ][ ticker ]
        data /= data[-num_points]
        data -= 1
        data *= 100

        _temp = pd.DataFrame( {
            'Metric': ticker,
            'Date'  : data.index[-num_points:],
            'Gain' : data[-num_points:].values
        } )
        _source.append( _temp )

    # get portfolio data
    for index, ticker in enumerate( params['port'] ):
        _temp = po_hist[ 'close' ][ ticker ]
        _temp /= _temp[-num_points]
        _temp -= 1
        _temp *= 100
        if index == 0: _data  = _temp
        else:          _data += _temp
    _data /= len( params['port'] )

    _temp = pd.DataFrame( {
        'Metric': 'Portfolio',
        'Date'  : _data.index[-num_points:],
        'Gain' : _data[-num_points:].values
    } )
    _source.append( _temp )

    # concat data
    source = pd.concat( _source )

    # benchmark chart
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Gain', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Gain' ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    )

    return ch

def get_pattern_chart( bullish_histo, bearish_histo ):

    domain = [ 'Bullish', 'Bearish' ]
    range_ = [ '#006400', 'red' ]

    source1 = pd.DataFrame( {
        'Signal': 'Bullish',
        'Date'  : bullish_histo.index,
        'Value' : bullish_histo.values
    } )
    source2 = pd.DataFrame( {
        'Signal': 'Bearish',
        'Date'  : bearish_histo.index,
        'Value' : bearish_histo.values
    } )
    source = pd.concat( [ source1, source2 ] )

    ch = alt.Chart( source ).mark_point( size=150 ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Value', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Signal', 'Date', 'Value' ],
        color = alt.Color( 'Signal', legend=alt.Legend( orient="top-left" ), scale=alt.Scale(domain=domain, range=range_) )
    )

    return ch

def fill_table( stock_list ):

    # data from Ticker.price
    _table_data = {}
    
    for key, val in stock_list.price.items():
        
        # initialize
        entry = {}

        try:
            # for each items
            for sub_key, sub_val in val.items():
                if sub_key in attr_list:
                    if "Percent" in sub_key: sub_val *= 100.
                    entry[ attr_list[ sub_key ] ] = sub_val

            # compute RSI
            rsi = ta.RSI( stock_hist['close'][ key ] )[-1]
            entry[ 'RSI(14)' ] = rsi

            # compute CCI
            cci = ta.CCI( stock_hist['high'][ key ], stock_hist['low'][ key ], stock_hist['close'][ key ] )[-1]
            entry[ 'CCI(14)' ] = cci
        
            # replace
            _table_data[ key ] = entry
        except:
            pass

    # data from Ticker.summary_detail
    for key, val in stock_list.summary_detail.items():
        
        # initialize
        entry = _table_data[ key ]

        try:
            for sub_key, sub_val in val.items():
                if sub_key in attr_list:
                    if "Percent" in sub_key: sub_val *= 100.
                    if sub_key == 'fiftyTwoWeekHigh' or sub_key == 'fiftyTwoWeekLow':
                        sub_val = ( entry[ 'Price' ]-sub_val ) / sub_val * 100.
                    entry[ attr_list[ sub_key ] ] = sub_val

            _table_data[ key ] = entry
        except:
            pass

    return _table_data

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

# historical prices
stock_hist  = fetch_history    ( stock_list,  period='1y', interval='1d' )
bench_hist  = fetch_history_alt( bench_list,  period='1y', interval='1d' )
market_hist = fetch_history    ( market_list, period='5d', interval='5m' )

# -------------------------------------------------------------------------------------------------
# Generate data
# -------------------------------------------------------------------------------------------------

# fill data from stock list
table_data = fill_table( stock_list )

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
        st.experimental_rerun()

    # ---------------------------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------------------------

    df = pd.DataFrame.from_dict( table_data, orient='index' ).sort_values( by='RSI(14)' )
    df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
    st.write( df )

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

        num_points = get_num_points( bench_hist['close'][ params['bench'][0] ].index, period_delta[period] )

        # draw chart
        btest_chart = get_btest_chart( stock_hist, bench_hist, num_points )
        st.altair_chart( btest_chart, use_container_width=True )

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
    oversold_data   = {}
    overbought_data = {}
    for key, val in table_data.items():
        if check_oversold  ( val, rsi_L, cci_L ): oversold_data  [ key ] = val
        if check_overbought( val, rsi_H, cci_H ): overbought_data[ key ] = val

    # sub title
    st.markdown( '##### Oversold' )

    # write noted list
    st.text( f'RSI<{rsi_L} and CCI<{cci_L}' )
    
    if oversold_data != {}:
        df = pd.DataFrame.from_dict( oversold_data, orient='index' ).sort_values( by='RSI(14)' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

    # sub title
    st.markdown( '##### Overbought' )

    # write noted list
    st.text( f'RSI>{rsi_H} and CCI>{cci_H}' )
    
    if overbought_data != {}:
        df = pd.DataFrame.from_dict( overbought_data, orient='index' ).sort_values( by='RSI(14)' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

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

    num_points = get_num_points( stock_hist['close'][option].index, period_delta[period] )

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
    price_chart = get_candle_chart( stock_list, stock_hist, option, num_points )

    # bollinger band chart
    if bband_flag:
        price_chart += get_bband_chart( stock_hist, option, num_points )

    # MA20 chart
    if ma20_flag:
        price_chart += get_ma_chart( stock_hist, option, num_points, 20, 'red' )

    # MA60 chart
    if ma60_flag:
        price_chart += get_ma_chart( stock_hist, option, num_points, 60, 'green' )

    # MA120 chart
    if ma120_flag:
        price_chart += get_ma_chart( stock_hist, option, num_points, 120, 'orange' )

    # draw
    st.altair_chart( price_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # RSI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    rsi_chart = get_rsi_chart( stock_hist, option, num_points )

    # draw
    st.altair_chart( rsi_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # CCI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    cci_chart = get_cci_chart( stock_hist, option, num_points )

    # draw
    st.altair_chart( cci_chart, use_container_width=True )    

    # ---------------------------------------------------------------------------------------------
    # MACD history chart
    # ---------------------------------------------------------------------------------------------
    
    # macd chart
    macd_chart, macd_hist_chart = get_macd_charts( stock_hist, option, num_points )

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
        st.experimental_rerun()

    # check market open
    if is_market_open():
        ticker_list = params[ 'market' ]
    else:
        ticker_list = params[ 'future' ]

    for option in ticker_list:
        num_points = get_num_points( market_hist['close'][option].index, period_delta[period] )
        market_chart = get_price_chart( market_list, market_hist, option, num_points )
        st.altair_chart( market_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Pattern
# -------------------------------------------------------------------------------------------------

if menu == 'Pattern':

    # limit period range (1 Month)
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
    price_chart = get_candle_chart( stock_list, stock_hist, option, num_points )

    # bullish chart
    price_chart += get_pattern_chart( bullish_histo, bearish_histo )

    # draw
    st.altair_chart( price_chart, use_container_width=True )