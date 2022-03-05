#
# Chart functions for financial analysis
#

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import pandas   as pd
import altair   as alt
import talib    as ta
import datetime as dt
import numpy    as np
import requests

from bs4 import BeautifulSoup
from numpy import NaN
from io import BytesIO
from PIL import Image

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

abbr_list = { 
    '^IXIC':'NASDAQ Composite',
    '^GSPC':'S&P 500',
    '^DJI':'DOW Jones Average',    
    'NQ=F':'NASDAQ Futures',
    'ES=F':'S&P 500 Futures',
    'YM=F':'DOW Jones Futures',
    'KRW=X':'USD/KRW',
}

# -------------------------------------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------------------------------------

def compute_mdd( data ):

    mdd = ( data - data.cummax() ).min()
    return mdd

# -------------------------------------------------------------------------------------------------
# Chart Functions
# -------------------------------------------------------------------------------------------------

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

def get_rsi_chart( st_hist, ticker, num_points, params ):

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

def get_cci_chart( st_hist, ticker, num_points, params ):

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
        elem = po_hist[ 'close' ][ ticker ].copy()
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

def get_fear_grid_source():

    # local functions
    def clean_image_url( _url ):
        idx1 = _url.find ( "'" )
        idx2 = _url.rfind( "'" )
        return _url[idx1+1:idx2]

    def sep_fear_index( _str ):
        _temp1 = _str.split( ':' )
        _temp2 = _temp1[1].split( '(' )
        _temp  = [ _temp1[0], int(_temp2[0]), _temp2[1][:-1] ]
        return _temp

    # CNN money
    url = 'https://money.cnn.com/data/fear-and-greed/'

    # get data
    response = requests.get( url, verify=False )
    html     = response.text
    soup     = BeautifulSoup( html, 'html.parser' )

    # needle chart
    needle      = soup.select_one( '#needleChart' )
    needle_url  = clean_image_url( needle['style'] )
    needle_list = needle.select( 'li' )
    fear_list   = []
    for elem in needle_list:
        entry = sep_fear_index( elem.get_text() )
        fear_list.append( entry )

    # over time
    overtime = soup.select_one( '#feargreedOverTime' )
    overtime_url = clean_image_url( overtime['style'] )

    return needle_url, fear_list, overtime_url

def get_fear_grid_chart( fear_list ):

    # Data range
    e_day = dt.datetime.today()
    s_day = e_day - dt.timedelta( days=30 )

    # Make data source
    source_data = [
        {"Date": s_day, "Index": fear_list[2][1] },
        {"Date": e_day, "Index": fear_list[0][1] }
    ]

    source_area = [{
                "Start": 0,
                "End": 25,
                "Status": "Extreme Fear"
            },
            {
                "Start": 25,
                "End": 50,
                "Status": "Fear"
            },
            {
                "Start": 50,
                "End": 75,
                "Status": "Greed"
            },
            {
                "Start": 75,
                "End": 100,
                "Status": "Extreme Greed"
            },                        
    ]

    source_data = alt.pd.DataFrame(source_data)
    source_area = alt.pd.DataFrame(source_area)

    # Line chart
    w_change = ( fear_list[0][1] - fear_list[2][1] ) / fear_list[2][1] * 100.0
    line = alt.Chart( source_data ).mark_line( color='#FFFFFF' ).encode(
        x = alt.X( 'Date' ),
        y = alt.Y( 'Index', scale=alt.Scale( domain=[ 0,100 ] ), title='Index' ),
        strokeWidth = alt.value( 3 )
    ).properties( title = f'Fear & Greed Index Now: {fear_list[0][1]} ({w_change:.2f}%)' )

    # Area chart
    rect = alt.Chart( source_area ).mark_rect().encode(
        y  = alt.Y ( 'Start', title='' ),
        y2 = alt.Y2( 'End',   title='' ),
        color=alt.Color( 'Status', 
                         sort=[ 'Extreme Greed', 'Greed', 'Fear', 'Extreme Fear' ], 
                         scale=alt.Scale( range=[ '#31a348', '#8eba5c', '#d67558', '#c9252f' ] ) 
        ),
    )

    return rect + line

def get_fear_grid_trend_source():

    needle_url, fear_list, overtime_url = get_fear_grid_source()

    # get image and convert to grayscale
    response = requests.get( overtime_url, verify=False )
    img = Image.open( BytesIO( response.content ) ).convert( "L" )

    # convert to numpy array
    data = 255 - np.array(img).transpose()

    # remove outlier values
    data[ data != 102 ] = 0

    # vertical pixel range in image
    y_s = 10
    y_e = 255
    y_l = y_e - y_s

    # find point
    data_list   = []
    for elem in data:
        nz_pos = elem.nonzero()[0]
        if len( nz_pos ) > 1:
            nz_pos_pred = np.median( nz_pos )
            nz_pos_pred  = int( min( 100, max( 0, 100 - ( ( nz_pos_pred-y_s ) * 100 / y_l ) ) ) )
            data_list.append( nz_pos_pred )

   # start date
    t_n = dt.datetime.today()

    # build final results
    n = len( data_list )
    source = {}
    for idx, elem in enumerate( data_list ):
        delta = 365*3 - int( 365*3*idx/(n-1) )
        t_p = t_n - dt.timedelta( days=delta )
        source[ t_p ] = elem

    fg_hist = pd.Series( source )

    # insert true values
    fg_hist[t_n                       ] = fear_list[0][1]
    fg_hist[t_n-dt.timedelta(days=  1)] = fear_list[1][1]
    fg_hist[t_n-dt.timedelta(days=  7)] = fear_list[2][1]
    fg_hist[t_n-dt.timedelta(days= 30)] = fear_list[3][1]
    fg_hist[t_n-dt.timedelta(days=365)] = fear_list[4][1]

    # sort by idnx
    fg_hist.sort_index( inplace=True )

    return needle_url, fear_list, overtime_url, fg_hist

def get_fear_grid_trend_chart( fear_list, fg_hist, num_points ):

    # line data
    source_data = pd.DataFrame( {
        'Date':  fg_hist.index[-num_points:],
        'Index': fg_hist[-num_points:].values
    } )

    # Area data
    source_area = [{
                "Start": 0,
                "End": 25,
                "Status": "Extreme Fear"
            },
            {
                "Start": 25,
                "End": 50,
                "Status": "Fear"
            },
            {
                "Start": 50,
                "End": 75,
                "Status": "Greed"
            },
            {
                "Start": 75,
                "End": 100,
                "Status": "Extreme Greed"
            },                        
    ]

    source_area = alt.pd.DataFrame(source_area)

    # Line chart
    w_change = ( fg_hist[-1] - fg_hist[-num_points] ) / fg_hist[-num_points] * 100.0
    line = alt.Chart( source_data ).mark_line( color='#FFFFFF' ).encode(
        x = alt.X( 'Date' ),
        y = alt.Y( 'Index', scale=alt.Scale( domain=[ 0,100 ] ), title='Index' ),
        strokeWidth = alt.value( 2 ),
        tooltip = [ 'Date', 'Index' ],
    ).properties( title = f'Fear & Greed Index Now: {fear_list[0][1]} ({w_change:.2f}%)' )

    # Area chart
    rect = alt.Chart( source_area ).mark_rect().encode(
        y  = alt.Y ( 'Start', title='' ),
        y2 = alt.Y2( 'End',   title='' ),
        color=alt.Color( 'Status', 
                         sort=[ 'Extreme Greed', 'Greed', 'Fear', 'Extreme Fear' ], 
                         scale=alt.Scale( range=[ '#31a348', '#8eba5c', '#d67558', '#c9252f' ] ) 
        ),
    )

    return rect + line