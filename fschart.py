#
# Chart functions for financial analysis
#

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import pandas as pd
import altair as alt
import talib  as ta

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
# Functions
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

def get_btest_chart( po_hist, be_hist, num_points, params ):

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
    for index, ticker in enumerate( params['port'] ):
        elem = po_hist[ 'close' ][ ticker ].copy()
        elem /= elem[-num_points]
        elem -= 1
        elem *= 100
        if index == 0: sum  = elem
        else:          sum += elem
    sum /= len( params['port'] )

    _temp = pd.DataFrame( {
        'Metric': 'Portfolio',
        'Date'  : sum.index[-num_points:],
        'Gain' : sum[-num_points:].values
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