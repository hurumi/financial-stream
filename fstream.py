#
# Streamlit demo for financial analysis
#

# disable SSL warnings
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

from yahooquery import Ticker

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

port_tickers = [ 'MSFT', 'AAPL', 'SPLG', 'QQQ', 'JEPI', 'TSLA' ]
mark_tickers = [ 'NQ=F', 'ES=F', 'YM=F', 'KRW=X' ]
attr_list = { 
    'regularMarketChangePercent':'Change(%)', 
    'regularMarketPrice':'Price',
    'trailingPE':'P/E',
    'fiftyTwoWeekHigh':'52W_H(%)',
    'fiftyTwoWeekLow':'52W_L(%)',
    'NQ=F':'NASDAQ Futures',
    'ES=F':'S&P 500 Futures',
    'YM=F':'DOW Futures',
    'KRW=X':'USD/KRW',
}

_RSI_THRESHOLD_L =   30
_RSI_THRESHOLD_H =   70
_CCI_THRESHOLD_L = -100
_CCI_THRESHOLD_H =  100

# -------------------------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------------------------

@st.experimental_singleton
def fetch_tickers( tickers ):
    
    _list = Ticker( tickers, verify=False )
    return _list

@st.experimental_singleton
def fetch_history( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval )
    return _hist

def fetch_history_nocache( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval )
    return _hist    

def get_usdkrw():

    _temp = requests.get( "https://api.exchangerate-api.com/v4/latest/USD", verify=False )
    exchange_rate = _temp.json()

    return exchange_rate['rates']['KRW']

def check_oversold( entry ):

    if entry[ 'RSI(14)' ] > _RSI_THRESHOLD_L:
        return False

    if entry[ 'CCI(14)' ] > _CCI_THRESHOLD_L:
        return False

    return True

def check_overbought( entry ):

    if entry[ 'RSI(14)' ] < _RSI_THRESHOLD_H:
        return False      

    if entry[ 'CCI(14)' ] < _CCI_THRESHOLD_H:
        return False            

    return True

def highlight_negative(s):

    is_negative = s < 0
    return ['color: red' if i else '' for i in is_negative]

def get_price_chart( ticker, num_points ):

    hist = stock_histo[ 'close' ][ ticker ]
    source = pd.DataFrame( {
    'Date': hist.index[-num_points:],
    'Price': hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Date', 'Price' ]
    )
    return ch

def get_bband_chart( ticker, num_points ):

    bband_up, bband_mid, bband_low = ta.BBANDS( stock_histo['close'][ ticker ], 20, 2 )
    source1 = pd.DataFrame( {
    'Metric': 'BBAND_UPPER',
    'Date'  : bband_up.index[-num_points:],
    'Price' : bband_up[-num_points:]
    } )
    source2 = pd.DataFrame( {
    'Metric': 'BBAND_MIDDLE',
    'Date'  : bband_mid.index[-num_points:],
    'Price' : bband_mid[-num_points:]
    } )
    source3 = pd.DataFrame( {
    'Metric': 'BBAND_LOWER',
    'Date'  : bband_low.index[-num_points:],
    'Price' : bband_low[-num_points:]
    } )
    source = pd.concat( [ source1, source2, source3 ] )
    ch = alt.Chart( source ).mark_line( strokeDash=[2,3] ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.Color( 'Metric', legend=None ),
    )
    return ch

def get_ma_chart( ticker, num_points, period, colorstr ):

    ma = ta.SMA( stock_histo['close'][ ticker ], period )
    source = pd.DataFrame( {
    'Metric': f'MA{period}',
    'Date'  : ma.index[-num_points:],
    'Price' : ma[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.value( colorstr ),
        strokeWidth = alt.value( 1 ),
    )
    return ch

def get_rsi_chart( ticker, num_points ):

    rsi_hist = ta.RSI( stock_histo['close'][ ticker ] )
    source = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': rsi_hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        tooltip = [ 'Date', 'RSI' ]
    )
    source_up = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': _RSI_THRESHOLD_H
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': _RSI_THRESHOLD_L
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn

def get_cci_chart( ticker, num_points ):

    cci_hist = ta.CCI( stock_histo['high'][ ticker ], stock_histo['low'][ ticker ], stock_histo['close'][ ticker ] )
    source = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': cci_hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        tooltip = [ 'Date', 'CCI' ]
    )
    source_up = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': _CCI_THRESHOLD_H
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': _CCI_THRESHOLD_L
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn    

def get_macd_charts( ticker, num_points ):

    macd, macdsignal, macdhist = ta.MACD( stock_histo['close'][ ticker ] )
    source1 = pd.DataFrame( {
    'Metric': 'MACD(12)',
    'Date'  : macd.index[-num_points:],
    'Value' : macd[-num_points:]
    } )
    source2 = pd.DataFrame( {
    'Metric': 'MACD(26)',
    'Date'  : macdsignal.index[-num_points:],
    'Value' : macdsignal[-num_points:]
    } )
    source3 = pd.DataFrame( {
    'Metric': 'MACDHIST',
    'Date'  : macdhist.index[-num_points:],
    'Hist'  : macdhist[-num_points:]
    } )
    source = pd.concat( [ source1, source2 ] )

    ch1 = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Value', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Value' ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    )
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

def get_market_chart( ticker, num_points ):

        hist = market_histo[ 'close' ][ ticker ]
        source = pd.DataFrame( {
        'Date': hist.index[-num_points:],
        'Price': hist[-num_points:]
        } )
        ch = alt.Chart( source ).mark_line().encode(
            x=alt.X( 'Date' ),
            y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
            tooltip = [ 'Date', 'Price' ]
        )

        prev_close = market_list.price[ option ][ 'regularMarketPreviousClose' ]
        source = pd.DataFrame( {
        'Date': hist.index[-num_points:],
        'Price': prev_close
        } )

        delta = ( hist[-1] - prev_close ) / prev_close * 100.
        prev = alt.Chart( source ).mark_line().encode(
            x=alt.X( 'Date' ),
            y=alt.Y( 'Price' ),
            color=alt.value("#FFAA00"),
            tooltip = [ 'Date', 'Price' ]
        ).properties( title = f'{attr_list[ option ]} ({delta:.2f}%)' )

        return ch+prev

# -------------------------------------------------------------------------------------------------
# Layout
# -------------------------------------------------------------------------------------------------

# add sidebar
st.sidebar.title( 'Financial Stream' )
menu = st.sidebar.radio( "MENU", ( 'Market', 'Portfolio', 'Stock' ) )

# -------------------------------------------------------------------------------------------------
# Fetch data
# -------------------------------------------------------------------------------------------------

stock_list   = fetch_tickers( port_tickers )
market_list  = fetch_tickers( mark_tickers )
stock_histo  = fetch_history( stock_list,  period='1y', interval='1d' )
market_histo = fetch_history_nocache( market_list, period='5d', interval='5m' )

# -------------------------------------------------------------------------------------------------
# Generate data
# -------------------------------------------------------------------------------------------------

# data from Ticker.price
table_data = {}
for key, val in stock_list.price.items():
    # initialize
    entry = {}

    # for each items
    for sub_key, sub_val in val.items():
        if sub_key in attr_list:
            if "Percent" in sub_key: sub_val *= 100.
            entry[ attr_list[ sub_key ] ] = sub_val

    # compute RSI
    rsi = ta.RSI( stock_histo['close'][ key ] )[-1]
    entry[ 'RSI(14)' ] = rsi

    # compute CCI
    cci = ta.CCI( stock_histo['high'][ key ], stock_histo['low'][ key ], stock_histo['close'][ key ] )[-1]
    entry[ 'CCI(14)' ] = cci
    
    # replace
    table_data[ key ] = entry

# data from Ticker.summary_detail
for key, val in stock_list.summary_detail.items():
    entry = table_data[ key ]
    for sub_key, sub_val in val.items():
        if sub_key in attr_list:
            if "Percent" in sub_key: sub_val *= 100.
            if sub_key == 'fiftyTwoWeekHigh' or sub_key == 'fiftyTwoWeekLow':
                sub_val = ( entry[ 'Price' ]-sub_val ) / sub_val * 100.
            entry[ attr_list[ sub_key ] ] = sub_val

    table_data[ key ] = entry 

# check over conditions
oversold_data   = {}
overbought_data = {}
for key, val in table_data.items():
    if check_oversold  ( val ): oversold_data  [ key ] = val
    if check_overbought( val ): overbought_data[ key ] = val

# -------------------------------------------------------------------------------------------------
# Portfolio
# -------------------------------------------------------------------------------------------------

if menu == 'Portfolio':
    # sub title
    st.subheader( 'Portfolio' )
    
    # write summary
    df = pd.DataFrame.from_dict( table_data, orient='index' )
    df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
    st.write( df )

    # sub title
    st.subheader( 'Oversold' )

    # write noted list
    st.text( f'RSI<{_RSI_THRESHOLD_L} and CCI<{_CCI_THRESHOLD_L}' )
    
    if oversold_data != {}:
        df = pd.DataFrame.from_dict( oversold_data, orient='index' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

    # sub title
    st.subheader( 'Overbought' )

    # write noted list
    st.text( f'RSI>{_RSI_THRESHOLD_H} and CCI>{_CCI_THRESHOLD_H}' )
    
    if overbought_data != {}:
        df = pd.DataFrame.from_dict( overbought_data, orient='index' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

# -------------------------------------------------------------------------------------------------
# Each stock
# -------------------------------------------------------------------------------------------------

if menu == 'Stock':
    # sub title
    st.subheader( 'Stock chart' )

    # stock selector
    option = st.selectbox( 'Ticker', port_tickers )

    # points selector
    num_points = st.selectbox( 'Number of data points (x 1d)', [ 30, 60, 120 ] )

    # ---------------------------------------------------------------------------------------------
    # price history chart
    # ---------------------------------------------------------------------------------------------

    st.write( f'{num_points}-point Price' )

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
    price_chart = get_price_chart( option, num_points )

    # bollinger band chart
    if bband_flag:
        price_chart += get_bband_chart( option, num_points )

    # MA20 chart
    if ma20_flag:
        price_chart += get_ma_chart( option, num_points, 20, 'red' )

    # MA60 chart
    if ma60_flag:
        price_chart += get_ma_chart( option, num_points, 60, 'green' )

    # MA120 chart
    if ma120_flag:
        price_chart += get_ma_chart( option, num_points, 120, 'orange' )

    # draw
    st.altair_chart( price_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # RSI history chart
    # ---------------------------------------------------------------------------------------------

    st.write( f'{num_points}-point RSI(14)' )

    # rsi chart
    rsi_chart = get_rsi_chart( option, num_points )

    # draw
    st.altair_chart( rsi_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # CCI history chart
    # ---------------------------------------------------------------------------------------------

    st.write( f'{num_points}-point CCI(14)' )

    # rsi chart
    cci_chart = get_cci_chart( option, num_points )

    # draw
    st.altair_chart( cci_chart, use_container_width=True )    

    # ---------------------------------------------------------------------------------------------
    # MACD history chart
    # ---------------------------------------------------------------------------------------------

    st.write( f'{num_points}-point MACD' )
    
    # macd chart
    macd_chart, macd_hist_chart = get_macd_charts( option, num_points )

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
    num_points = st.selectbox( 'Number of data points (x 5m)', [ 30, 60, 120 ] )
    
    # refresh button
    st.button( 'Refresh' )

    for option in mark_tickers:
        market_chart = get_market_chart( option, num_points )
        st.altair_chart( market_chart, use_container_width=True )