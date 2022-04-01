#
# Chart functions for financial analysis
#

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import streamlit as st
import pandas    as pd
import altair    as alt
import talib     as ta
import datetime  as dt
import numpy     as np
import requests

from bs4 import BeautifulSoup
from numpy import NaN
from io import BytesIO
from PIL import Image

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

# Priority: (1) abbr_list (2) shortName field (3) longName field
abbr_list = { 
    'NQ=F':'NASDAQ Futures',
    'ES=F':'S&P 500 Futures',
    'YM=F':'DOW Jones Futures',
    'XLE': 'Energy', 
    'XLU': 'Utilities', 
    'XLB': 'Materials', 
    'XLRE':'Real Estate',
    'XLV': 'Healthcare',
    'XLP': 'Consumer Defensive',
    'XLI': 'Industrials',
    'XLC': 'Communication Services',
    'XLF': 'Financial',
    'XLK': 'Technology',
    'XLY': 'Consumer Cyclical',
}

# -------------------------------------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------------------------------------

def compute_mdd( data ):

    mdd = ( data - data.cummax() ).min()
    return mdd

def get_display_name( _ticker, _st_info ):

    if _ticker in abbr_list: return abbr_list[ _ticker ]
    if _st_info['price'][_ticker]['shortName'] != None: return _st_info['price'][_ticker]['shortName']
    if _st_info['price'][_ticker]['longName' ] != None: return _st_info['price'][_ticker]['longName' ]
    return _ticker

# -------------------------------------------------------------------------------------------------
# Chart Functions
# -------------------------------------------------------------------------------------------------

def get_price_chart( st_info, st_hist, ticker, num_points, prev_line=False ):

        hist = st_hist[ 'close' ][ ticker ]

        prev_close = st_info['price'][ ticker ][ 'regularMarketPreviousClose' ]
        cur_price  = st_info['price'][ ticker ][ 'regularMarketPrice'         ]
        perd_close = st_hist['close'][ ticker ][ -num_points ]

        delta1 = ( cur_price - prev_close ) / prev_close * 100.
        delta2 = ( cur_price - perd_close ) / perd_close * 100.
        title = get_display_name( ticker, st_info ) + f' ({ticker})'

        source = pd.DataFrame( {
            'Date': hist.index[-num_points:],
            'Price': hist[-num_points:].values
        } )

        ch = alt.Chart( source ).mark_line().encode(
            x=alt.X( 'Date:T' ),
            y=alt.Y( 'Price:Q', scale=alt.Scale( zero=False )  ),
            tooltip = [ 'Date', alt.Tooltip( 'Price', format='.2f' ) ]
        ).properties( title = f'{title}: {cur_price:.2f} (D {delta1:.2f}% / P {delta2:.2f}%)' )

        # draw previous close line
        if prev_line:
            ln = alt.Chart( pd.DataFrame( {'Price': [prev_close]} ) )
            ch = ch + ln.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='Price' )

        return ch

def get_candle_chart( st_info, st_hist, ticker, num_points, prev_line=False ):

        hist = st_hist[ 'close' ][ ticker ]

        prev_close = st_info['price'][ ticker ][ 'regularMarketPreviousClose' ]
        cur_price  = st_info['price'][ ticker ][ 'regularMarketPrice'         ]
        perd_close = st_hist['close'][ ticker ][ -num_points ]

        delta1 = ( cur_price - prev_close ) / prev_close * 100.
        delta2 = ( cur_price - perd_close ) / perd_close * 100.
        title = get_display_name( ticker, st_info ) + f' ({ticker})'

        # make source
        source = pd.DataFrame( {
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
        base = alt.Chart( source ).encode(
            x = alt.X( 'Date:T' ),
            color=open_close_color,
            tooltip = [ 'Date', alt.Tooltip( 'Close', format='.2f' ) ]
        ).properties( title = f'{title}: {cur_price:.2f} (D {delta1:.2f}% / P {delta2:.2f}%)' )

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
        if prev_line:
            ln = alt.Chart( pd.DataFrame( {'Price': [prev_close]} ) )
            ch = ch + ln.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='Price' )

        return ch      

def get_bband_chart( st_hist, ticker, num_points ):

    bband_up, bband_mid, bband_low = ta.BBANDS( st_hist['close'][ ticker ], 20, 2 )

    # prepare source
    source = pd.DataFrame( {
        'Date' : bband_up.index[-num_points:],
        'Upper': bband_up[-num_points:].values,
        'Mid'  : bband_mid[-num_points:].values,
        'Lower': bband_low[-num_points:].values,
    } )
    
    # generate chart
    ch = alt.Chart( source ).mark_area( opacity=0.1, color='blue' ).encode(
        x  = alt.X ( 'Date'  ),
        y  = alt.Y ( 'Upper' ),
        y2 = alt.Y2( 'Lower' ),
    )
    mv = alt.Chart( source ).mark_line( strokeDash=[2,3], color='black', opacity=0.5 ).encode(
        x = alt.X( 'Date' ),
        y = alt.Y( 'Mid'  ),

    )
    return ch + mv

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
        color = alt.value( colorstr ),
        strokeWidth = alt.value( 1 ),
    )
    return ch

def get_rsi_chart( st_hist, ticker, num_points, params ):

    rsi_hist = ta.RSI( st_hist['close'][ ticker ] )
    source = pd.DataFrame( {
        'Date': rsi_hist.index[-num_points:],
        'RSI': rsi_hist[-num_points:].values
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        tooltip = [ 'Date', alt.Tooltip( 'RSI', format='.2f' ) ]
    ).properties( title = f'RSI(14): {rsi_hist[-1]:.2f}' )

    # draw guide lines
    ln_up = alt.Chart( pd.DataFrame( {'RSI': [params['RSI_H']] } ) )
    up = ln_up.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='RSI' )

    ln_dn = alt.Chart( pd.DataFrame( {'RSI': [params['RSI_L']] } ) )
    dn = ln_dn.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='RSI' )

    return ch+up+dn

def get_cci_chart( st_hist, ticker, num_points, params ):

    cci_hist = ta.CCI( st_hist['high'][ ticker ], st_hist['low'][ ticker ], st_hist['close'][ ticker ] )
    source = pd.DataFrame( {
        'Date': cci_hist.index[-num_points:],
        'CCI': cci_hist[-num_points:].values
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        tooltip = [ 'Date', alt.Tooltip( 'CCI', format='.2f' ) ]
    ).properties( title = f'CCI(14): {cci_hist[-1]:.2f}' )

    # draw guide lines
    ln_up = alt.Chart( pd.DataFrame( {'CCI': [params['CCI_H']] } ) )
    up = ln_up.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='CCI' )

    ln_dn = alt.Chart( pd.DataFrame( {'CCI': [params['CCI_L']] } ) )
    dn = ln_dn.mark_rule( strokeWidth=2, color='#FFAA00').encode( y='CCI' )

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
        tooltip = [ 'Metric', 'Date', alt.Tooltip( 'Value', format='.2f' ) ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    ).properties( title = 'MACD' )
    ch2 = alt.Chart( source3 ).mark_bar().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Hist' ),
        tooltip = [ 'Date', alt.Tooltip( 'Hist', format='.2f' ) ],
        color=alt.condition(
            alt.datum.Hist > 0,
            alt.value("green"),  # The positive color
            alt.value("red")  # The negative color
        )        
    )
    return ch1, ch2

def get_btest_source( po_hist, be_hist, num_points, params ):

    # get benchmark data
    _source = []    
    for ticker in params['bench']:

        elem = be_hist[ 'close' ][ ticker ].copy()
        elem /= elem[-num_points]
        elem -= 1
        elem *= 100

        _temp = pd.DataFrame( {
            'Metric': ticker,
            'Date'  : elem.index[-num_points:],
            'Gain' : elem[-num_points:].values
        } )
        _source.append( _temp )

    # get portfolio data
    total_alloc = 0
    for index, ticker in enumerate( params['port'] ):
        elem = po_hist[ 'close' ][ ticker ][-num_points:].copy()
        elem /= elem[-num_points]
        elem -= 1
        elem *= 100 * params['port'][ticker]
        if index == 0: port  = elem
        else:          port += elem
        total_alloc += params['port'][ticker]
    port /= total_alloc

    _temp = pd.DataFrame( {
        'Metric': 'Portfolio',
        'Date'  : port.index[-num_points:],
        'Gain' : port[-num_points:].values
    } )
    _source.append( _temp )

    # concat data
    source = pd.concat( _source )

    # get merged ticker list
    tickers = params['bench'] + [ 'Portfolio' ]

    # make dataframe
    info = pd.DataFrame( columns=[ 'Gain', 'Delta', 'Stdev', 'Best', 'Worst', 'MDD', 'Beta', 'Sharpe' ] )

    # consider first bench ticker as reference
    ref_data = source.loc[ source['Metric'] == params['bench'][0] ]['Gain']
    ref_gain = ref_data.iloc[-1]

    # for each ticker
    for ticker in tickers:
        
        # get column data
        data  = source.loc[ source['Metric'] == ticker ]['Gain']

        # make row
        entry = {}
        entry[ 'Gain'   ] = data.iloc[-1]
        entry[ 'Delta'  ] = entry[ 'Gain' ] - ref_gain
        entry[ 'Stdev'  ] = data.std()
        entry[ 'Best'   ] = data.max()
        entry[ 'Worst'  ] = data.min()
        entry[ 'MDD'    ] = compute_mdd( data )
        entry[ 'Beta'   ] = ta.BETA( ref_data+100, data+100 ).iloc[-1]
        
        dc = (data+100).pct_change(1).dropna()
        entry[ 'Sharpe' ] = dc.mean() / dc.std() * ( 252**0.5 )
        
        info.loc[ticker] = entry
        
    return source, info

def get_btest_chart( source ):

    # benchmark chart
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Gain', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', alt.Tooltip( 'Gain', format='.2f' ) ],
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
        tooltip = [ 'Signal', 'Date' ],
        color = alt.Color( 'Signal', legend=alt.Legend( orient="top-left" ), scale=alt.Scale(domain=domain, range=range_) )
    )

    return ch

def get_sector_chart( _se_info, _se_hist, num_points ):

    # prepare data
    se_tickers = list( _se_info[ 'price' ] )

    # check validity
    va_tickers = []
    for option in se_tickers:
        if len( _se_hist['close'][option] ) < num_points: continue
        va_tickers.append( option )

    last_price = [ _se_hist['close'][option][-1]          for option in va_tickers ]
    ref_price  = [ _se_hist['close'][option][-num_points] for option in va_tickers ]
    data_list  = [ round( (last_price[i]-ref_price[i])/ref_price[i]*100, 2 ) for i in range( len( va_tickers ) ) ]

    # sort by change
    comb_list = list( zip( data_list, va_tickers ) )
    comb_list.sort( reverse=True )
    sort_tick = [ b for (a,b) in comb_list ]
    sort_data = [ a for (a,b) in comb_list ]

    # prepare source
    source = pd.DataFrame( {
        'Name': [ get_display_name( key, _se_info )+f' ({key})' for key in sort_tick ],
        'Ticker': sort_tick,
        'Change(%)': sort_data,
        'LabelX': [ elem/2 for elem in sort_data ],
    } )

    # prepare bar chart
    ch = alt.Chart( source ).mark_bar().encode(
        x=alt.X( 'Change(%)' ),
        y=alt.Y( 'Name', sort=sort_tick, title='' ),
        color=alt.condition(
            alt.datum['Change(%)'] > 0,
            alt.value("green"),  # The positive color
            alt.value("red")  # The negative color
        ),
        tooltip = [ 'Name', 'Change(%)' ]
    )

    # prepare label
    label = ch.mark_text(
        align='center',
        baseline='middle',
        dx=0  # Nudges text to right so it doesn't appear on top of the bar
    ).encode(
        x=alt.X( 'LabelX', title='Change(%)' ),    
        text='Change(%)',
        color=alt.condition(
            abs( alt.datum['Change(%)'] ) > 0.3,
            alt.value("white"), 
            alt.value("black")  
        ),
    )

    return ch+label

def get_bond_chart( bond1_info, bond2_info, num_points ):

    # prepare source
    source1 = pd.DataFrame( {
        'Metric': bond1_info[0],
        'Date':   bond1_info[1].index[-num_points:],
        'Yield':  bond1_info[1]['Close'][-num_points:].values
    } )
    source2 = pd.DataFrame( {
        'Metric': bond2_info[0],
        'Date':   bond2_info[1].index[-num_points:],
        'Yield':  bond2_info[1]['Close'][-num_points:].values
    } )
    source = pd.concat( [ source1, source2 ] )

    # chart 1
    domain = [ bond1_info[0], bond2_info[0] ]
    t1 = bond1_info[1]['Close'][-1]
    t2 = bond2_info[1]['Close'][-1]
    d1 = t1 - bond1_info[1]['Close'][-2]
    d2 = t2 - bond2_info[1]['Close'][-2]
    ch1 = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Yield', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', alt.Tooltip( 'Yield', format='.3f' ) ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ), scale=alt.Scale(domain=domain) )
    ).properties( title = f'{bond1_info[0]}: {t1:.3f}% ({d1:.3f}%) & {bond2_info[0]}: {t2:.3f}% ({d2:.3f}%)' )

    # prepare delta
    source3 = pd.DataFrame( {
        'Metric': f'{bond1_info[0]} - {bond2_info[0]}',
        'Date':   bond1_info[1].index[-num_points:],
        'Yield':  bond1_info[1]['Close'][-num_points:].values-bond2_info[1]['Close'][-num_points:].values
    } )

    # chart 2
    t3 = t1 - t2
    d3 = d1 - d2
    ch2 = alt.Chart( source3 ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Yield', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', alt.Tooltip( 'Yield', format='.3f' ) ],
    ).properties( title = f'{bond1_info[0]} - {bond2_info[0]}: {t3:.3f}% ({d3:.3f}%)' )

    return ch1, ch2