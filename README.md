# financial-stream
Simple financial dashboard using streamlit

```bash
streamlit run fstream.py
```

Consists of four menus: Market, Portfolio, Stock and Pattern

#### Market menu
* Show various market charts for relatively short term (max 5D)
* "market" and "future" sections of param.json specify the tickers
* When market is open, "market" section is used. Otherwise, "future" section is used

#### Portfolio menu
* Show various numeric information, such as daily change, last price, 52W high and low prices, RSI and CCI
* Ticker list is editable
* Show performance chart of portfolio compared to benchmark which is specified in "bench" section of param.json
* Given editable RSI and CCI range, show oversold and overbought tickers

#### Stock menu
* Show various charts for single ticker
* Candle chart, RSI chart, CCI chart and MACD chart
* For candle chart, you can optionally include Bollinger band, MA20, MA60 and MA120

#### Pattern menu
* Detect bullish and bearish patterns for recent 1 month
* For each selected ticker, show candle chart with detected marks
* Total 12 detection methods of TA-LIB are supported as:

```python
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
```

#### Example screenshot of pattern menu

<img src="/images/pattern.png" width="100%">
