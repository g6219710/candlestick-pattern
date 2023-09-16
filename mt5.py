import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import indicators

register_matplotlib_converters()
import MetaTrader5 as mt5


class mt_datasource:
    def __init__(self):
        if not mt5.initialize():
            print("initialize() failed")
            mt5.shutdown()
        self.timeframe = mt5.TIMEFRAME_M1

    def shutdown(self):
        mt5.shutdown()

    def get_symbols(self):
        return mt5.symbols_get()


    def get_period_by_timeframe(self, timeframe):
        if timeframe <= mt5.TIMEFRAME_M5:
            return 60
        elif timeframe <= mt5.TIMEFRAME_H1:
            return 200
        elif timeframe <= mt5.TIMEFRAME_H4:
            return 900
        elif timeframe <= mt5.TIMEFRAME_D1:
            return 3600
        else:
            return 7200

    def get_timedelta(self):
        if self.timeframe < mt5.TIMEFRAME_H1:
            return timedelta(minutes=self.timeframe)
        elif self.timeframe == mt5.TIMEFRAME_H1:
            return timedelta(hours=1)
        elif self.timeframe == mt5.TIMEFRAME_H4:
            return timedelta(hours=4)
        elif self.timeframe == mt5.TIMEFRAME_D1:
            return timedelta(day1=1)
        else:
            return timedelta(hours=1)

    def get_df_for_display(self, symbol, timeframe=mt5.TIMEFRAME_M1, start_date=None, end_date=None):
        if timeframe is not None:
            self.timeframe = timeframe
        if end_date is None:
            end_date = datetime.now()
            end_date = end_date + timedelta(days=1)
        if start_date is None:
            period = self.get_period_by_timeframe(self.timeframe)
            start_date = end_date - timedelta(days=period)

        print(start_date, end_date)
        print(type(start_date))

        df = mt5.copy_rates_range(symbol, self.timeframe, start_date, end_date)
        print(df)

        ticks_frame = pd.DataFrame(df)
        ticks_frame['time'] = pd.to_datetime(ticks_frame['time'], unit='s')
        ticks_frame = indicators.add_indicators(ticks_frame)
        ticks_frame.index = pd.DatetimeIndex(ticks_frame['time'])
        return ticks_frame

    def update_candle(self, symbol, df):
        timeframe = self.timeframe
        while True:
            if timeframe != self.timeframe:
                break

            mt_time = datetime.utcnow() + timedelta(hours=3)
            if mt_time.weekday() > 4:
                time.sleep(60)

            last_index = df.index[-1]
            bid = mt5.symbol_info_tick(symbol).bid
            if mt_time - last_index < self.get_timedelta():
                df.loc[last_index, 'close'] = bid
                if bid > df.loc[last_index, 'high']:
                    df.loc[last_index, 'high'] = bid
                if bid < df.loc[last_index, 'low']:
                    df.loc[last_index, 'low'] = bid
            else:
                row_data = [last_index + self.get_timedelta(), bid, bid, bid, bid]
                for i in range(len(df.columns) - 5):
                    row_data.append(np.NAN)
                df.loc[last_index + self.get_timedelta()] = row_data
            indicators.add_indicator(df, 'RSI')
            time.sleep(2)
