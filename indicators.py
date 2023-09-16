from datetime import datetime
import numpy as np
import pandas as pd
from stockstats import StockDataFrame as Sdf
import statistics

import talib as ta

cps = [['HAMMER', 100, 1], ['MARUBOZU', 100, 1], ['INVERTEDHAMMER', 100, 1],
       ['PIERCING', 100, 2], ['ENGULFING', 100, 2], ['HARAMI', 100, 2], ['COUNTERATTACK', 100, 2], ['BELTHOLD', 100, 2],
       ['MORNINGSTAR', 100, 3], ['3WHITESOLDIERS', 100, 3], ['3INSIDE', 100, 3], ['3OUTSIDE', 100, 3],
       ['3STARSINSOUTH', 100, 3], ['TASUKIGAP', 100, 3], ['HIKKAKE', 100, 3],
       ['3LINESTRIKE', 100, 4], ['CONCEALBABYSWALL', 100, 4],
       ['RISEFALL3METHODS', 100, 5], ['BREAKAWAY', 100, 5], ['LADDERBOTTOM', 100, 5], ['MATHOLD', 100, 5],
       ['HANGINGMAN', -100, 1], ['MARUBOZU', -100, 1], ['SHOOTINGSTAR', -100, 1],
       ['DARKCLOUDCOVER', -100, 2], ['ENGULFING', -100, 2], ['HARAMI', -100, 2], ['ONNECK', -100, 2], ['COUNTERATTACK', -100, 2],
       ['2CROWS', -100, 2], ['BELTHOLD', -100, 2],
       ['EVENINGSTAR', -100, 3], ['EVENINGDOJISTAR', -100, 3], ['3BLACKCROWS', -100, 3], ['3INSIDE', -100, 3], ['3OUTSIDE', -100, 3],
       ['ADVANCEBLOCK', -100, 3], ['TASUKIGAP', -100, 3], ['HIKKAKE', -100, 3],
       ['3LINESTRIKE', -100, 4],
       ['RISEFALL3METHODS', -100, 5], ['BREAKAWAY', -100, 5], ['LADDERBOTTOM', -100, 5], ['MATHOLD', -100, 5]]

scps = [['HAMMER', 100, 'H'], ['HANGINGMAN', -100, 'h'],
        ['CLOSINGMARUBOZU', 100, 'M'], ['CLOSINGMARUBOZU', -100, 'm'],
        ['MARUBOZU', 100, 'M'], ['MARUBOZU', -100, 'm'],
        ['LONGLINE', 100, 'L'], ['LONGLINE', -100, 'l'],
        ['SHORTLINE', 100, 'S'], ['SHORTLINE', -100, 's'],
        ['SHOOTINGSTAR', -100, 't'],
        ['DOJISTAR', 100, 'J'], ['DOJISTAR', -100, 'j'],
        ['SPINNINGTOP', 100, 'P'], ['SPINNINGTOP', -100, 'P'],
        ['INVERTEDHAMMER', 100, 'I'], ['RICKSHAWMAN', 100, 'R'], ['TAKURI', 100, 'K'],
        ['DOJI', 100, 'D'], ['DRAGONFLYDOJI', 100, 'F'], ['GRAVESTONEDOJI', 100, 'G'],
        ['LONGLEGGEDDOJI', 100, 'O']]

def get_supported_cdl():
    cdl_methods = [m for m in dir(ta) if m.find('CDL') == 0]
    return cdl_methods


def add_multiple_labels(df, max_day=10):
    for i in range(max_day):
        df['close_after' + str(i + 1)] = df['close'].shift(-(i + 1))
        df['label' + str(i + 1)] = np.where(df['close_after' + str(i + 1)] > df['close'], 1, -1)


def add_days_labels(df, day_array):
    for i in day_array:
        df['close_after' + str(i + 1)] = df['close'].shift(-(i + 1))
        df['label' + str(i + 1)] = np.where(df['close_after' + str(i + 1)] > df['close'], 1, -1)


def add_price_change(df, days=5):
    df['close_after'] = df['close'].shift(-days)
    df['close_before'] = df['close'].shift(days)
    df['change_after'] = df['close_after'] - df['close']
    df['change_before'] = df['close'] - df['close_before']
    df['change_continue'] = df['change_after'] * df['change_before']


def add_candle_pattern(df, pattern_name, direction=100):
    df[pattern_name] = getattr(ta, pattern_name)(df['open'], df['high'], df['low'], df['close'])
    df[pattern_name + '_marker'] = np.where(df[pattern_name] == 100, df['high'] * 1.0001, np.NAN)
    df[pattern_name + '_marker_bear'] = np.where(df[pattern_name] == -100, df['low'] * 0.9999, np.NAN)


def add_all_candle_patterns(df):
    cdl_methods = get_supported_cdl()
    print(cdl_methods)
    for mtd in cdl_methods:
        df[mtd[3:]] = getattr(ta, mtd)(df['open'], df['high'], df['low'], df['close'])


def get_all_candle_features(df, remove_zero_days=False):
    cdl_methods = get_supported_cdl()
    print(cdl_methods)
    df_cdl = pd.DataFrame(index=df.index)
    for mtd in cdl_methods:
        df_cdl[mtd] = getattr(ta, mtd)(df['open'], df['high'], df['low'], df['close'])
    # tgt = df[target]
    df_cdl['high'] = df['high']

    if remove_zero_days:
        non_zero = df_cdl.sum(axis=1) > 0
        # tgt = tgt[non_zero]
        df_cdl = df_cdl[non_zero]

    return df_cdl


def get_swing(row):
    if row['high'] > row['high_one_day_before'] and row['high'] > row['high_two_days_before'] \
            and row['high'] > row['high_one_day_after'] and row['high'] > row['high_two_days_after']:
        return -1
    elif row['low'] < row['low_one_day_before'] and row['low'] < row['low_two_days_before'] \
            and row['low'] < row['low_one_day_after'] and row['low'] < row['low_two_days_after']:
        return 1
    else:
        return 0


def get_marker(df, column_name):
    df[column_name + '_marker'] = np.where(df[column_name] == 1, df['high'] * 1.01, np.NAN)
    return df[column_name + '_marker']


def add_indicator(df, ta_name):
    df[ta_name] = getattr(ta, ta_name)(df['close'])


def add_indicators(df):
    # ticks_frame = Sdf.retype(df)
    ticks_frame = df
    ticks_frame['high_one_day_before'] = ticks_frame['high'].shift(1)
    ticks_frame['high_two_days_before'] = ticks_frame['high'].shift(2)
    # ticks_frame['close_three_days_before'] = ticks_frame['close'].shift(3)
    ticks_frame['high_one_day_after'] = ticks_frame['high'].shift(-1)
    ticks_frame['high_two_days_after'] = ticks_frame['high'].shift(-2)
    # ticks_frame['close_three_days_after'] = ticks_frame['close'].shift(-3)

    ticks_frame['low_one_day_before'] = ticks_frame['low'].shift(1)
    ticks_frame['low_two_days_before'] = ticks_frame['low'].shift(2)
    ticks_frame['low_one_day_after'] = ticks_frame['low'].shift(-1)
    ticks_frame['low_two_days_after'] = ticks_frame['low'].shift(-2)
    ticks_frame['swing'] = ticks_frame.apply(
        get_swing, axis=1)
    ticks_frame['swing_high'] = np.where(ticks_frame['swing'] == -1, ticks_frame['high'], np.NAN)
    ticks_frame['swing_low'] = np.where(ticks_frame['swing'] == 1, ticks_frame['low'], np.NAN)

    return ticks_frame


def add_one_day_label(df):
    total_avg = np.abs((df['close']-df['open'])/df['close']).mean()
    print(total_avg)
    df['close_after1'] = df['close'].shift(-1)
    df['change1'] = (df['close_after1'] - df['close']) / df['close']
    df['label_big_up'] = np.where(df['change1'] > total_avg*2, 1, 0)
    df['label_big_down'] = np.where(df['change1'] < total_avg * -2, 1, 0)

    df['big_up_marker'] = np.where(df['label_big_up'] == 1, df['high'] * 1.0001, np.NAN)
    df['big_down_marker'] = np.where(df['label_big_down'] == 1, df['low'] * 0.9999, np.NAN)


def add_labels(df, days=5):
    total_avg = np.abs((df['close']-df['open'])/df['close']).mean()
    print(total_avg)
    for day in range(days):
        df['close_after' + str(day)] = df['close'].shift(-day)
    df['label'] = 0
    df['max'] = 0.0
    df['min'] = 0.0
    df['avg'] = 0.0
    df['label_big_move'] = 0
    for i, row in df.iterrows():
        change = 0
        avg = 0
        for day in range(days):
            change = (row['close_after' + str(day)] - row['close']) / row['close']
            if change > row['max']:
                df.loc[i, 'max'] = change
            if change < row['min']:
                df.loc[i, 'min'] = change
            avg += change
        avg = avg / days
        df.loc[i, 'avg'] = avg

        '''for day in range(days):
            if (row['close_after' + str(day)] - row['close']) / row['close'] < -avg * 1:
                if label == 1:
                    label = 0
                else:
                    label = -1
                break'''

        df.loc[i, 'label'] = 1 if change > 0 else -1


def add_single_candlestick_pattern(df):
    for scp in scps:
        df[scp[0]] = getattr(ta, 'CDL'+scp[0])(df['open'], df['high'], df['low'], df['close'])


def get_single_candlestick_code(row, avg, low_band, mode=0):
    if mode == 0:
        for scp in scps:
            if row[scp[0]] == scp[1]:
                return scp[2]
        if row['body'] > avg:
            return 'B'
        elif row['body'] > 0:
            return 'N'
        elif row['body'] > -avg:
            return 'n'
        else:
            return 'b'
        return 'U'
    else:
        if row['body'] > avg:
            return 'B'
        elif row['body'] > low_band:
            return 'N'
        elif row['body'] > -low_band:
            return 'D'
        elif row['body'] > -avg:
            return 'n'
        else:
            return 'b'


def add_candlestick_code(df, std_length=10, mode=0, days=1):
    add_single_candlestick_pattern(df)
    add_all_candle_patterns(df)

    df['body'] = df['close'] - df['open']
    df['range'] = df['high'] - df['low']
    '''df['upper_shadow'] = np.where(df['open'] > df['close'], (df['high'] - df['open']) / df['open'],
                                  (df['high'] - df['close']) / df['close'])
    df['lower_shadow'] = np.where(df['open'] > df['close'], (df['close'] - df['low']) / df['low'],
                                  (df['open'] - df['low']) / df['low'])'''

    df['close_after'] = df['close'].shift(-days)
    df['label_increase'] = 0
    df['label_decrease'] = 0

    code_array = []
    index_number = -1
    df['candlestick_code'] = ''
    #df['pattern_name'] = ''
    for i, row in df.iterrows():
        index_number += 1
        if index_number < std_length:
            continue
        avg = np.abs(df[index_number - std_length:index_number]['body']).mean()
        avg_range = df[index_number - std_length:index_number]['range'].mean()

        low_band = avg_range / 10

        code = get_single_candlestick_code(row, avg, low_band, mode=mode)

        if len(code_array) >= 10:
            code_array.pop(0)
        code_array.append(code)
        code_string = ''.join(code_array)
        df.loc[i, 'candlestick_code'] = code_string
        df.loc[i, 'candlestick_code1'] = code_string[-1:]
        df.loc[i, 'candlestick_code2'] = code_string[-2:]
        df.loc[i, 'candlestick_code3'] = code_string[-3:]
        df.loc[i, 'candlestick_code4'] = code_string[-4:]
        df.loc[i, 'candlestick_code5'] = code_string[-5:]
        df.loc[i, 'candlestick_code6'] = code_string[-6:]
        df.loc[i, 'candlestick_code7'] = code_string[-7:]
        df.loc[i, 'candlestick_code8'] = code_string[-8:]
        df.loc[i, 'candlestick_code9'] = code_string[-9:]

        change = row['close_after'] - row['close']
        if change >= low_band:
            df.loc[i, 'label_increase'] = 1
        elif change <= -low_band:
            df.loc[i, 'label_decrease'] = 1

        '''for cp in cps:
            if row[cp[0]] == cp[1]:
                if cp[1] == 100:
                    df.loc[i, 'pattern_name'] = cp[0] + '_bull'
                else:
                    df.loc[i, 'pattern_name'] = cp[0] + '_bear'''


def add_candlestick_code1(df, std_length=1000):
    df['body'] = (df['close'] - df['open']) / df['open']
    df['upper_shadow'] = np.where(df['open'] > df['close'], (df['high'] - df['open']) / df['open'],
                                  (df['high'] - df['close']) / df['close'])
    df['lower_shadow'] = np.where(df['open'] > df['close'], (df['close'] - df['low']) / df['low'],
                                  (df['open'] - df['low']) / df['low'])
    #df['close_after_10'] = df['close'].shift(-10)
    #df['change_10'] = (df['close_after_10'] - df['close']) / df['close']
    #avg = np.abs(df['body']).mean()
    #print(avg)

    # df['big_up'] = np.where(df['change_10'] > std * 3, 1, 0)
    # df['big_down'] = np.where(df['change_10'] < -std * 3, 1, 0)

    df['close_after1'] = df['close'].shift(-1)
    df['label1'] = 0

    desired_code_array = []
    counterexample = []
    code_array = []
    index_number = -1
    df['candlestick_code'] = ''
    for i, row in df.iterrows():
        index_number += 1
        if index_number < std_length:
            continue

        #std = statistics.stdev(df[index_number - std_length:index_number]['body'])
        #print('std =' + str(std))
        avg = np.abs(df[index_number - std_length:index_number]['body']).mean()
        #print('avg = %f' % avg)
        low_band = avg / 4
        high_band = avg * 1
        huge_band = avg * 2

        code = ''
        '''if row['upper_shadow'] > high_band:
            code += 'LS'
        elif row['upper_shadow'] > low_band:
            code += 'ls'''''

        if row['body'] > huge_band:
            code = 'H'
        elif row['body'] > high_band:
            code = 'B'
        elif row['body'] > low_band:
            code = 'S'
        # elif row['body'] > 0:
        #    code += 'd'
        elif row['body'] > -low_band:
            code = 'd'
        elif row['body'] > -high_band:
            code = 's'
        elif row['body'] > -huge_band:
            code = 'b'
        else:
            code = 'h'

        '''if row['lower_shadow'] < -high_band:
            code += 'SL'
        elif row['lower_shadow'] < -low_band:
            code += 'sl'''''

        if len(code_array) >= 10:
            code_array.pop(0)
        code_array.append(code)
        df.loc[i, 'candlestick_code'] = ''.join(code_array)

        change = (row['close_after1'] - row['close'])/row['close']
        if change >= low_band:
            df.loc[i, 'label1'] = 1
        elif change <= -low_band:
            df.loc[i, 'label1'] = -1

        #df.loc[i, 'candlestick_code'] = ''.join(code_array)
        #if df.loc[i, 'label_big_up'] == 1:
        #    desired_code_array.append(''.join(code_array))
        #if df.loc[i, 'label_big_down'] == 1:
        #    counterexample.append(''.join(code_array))
    #print(len(desired_code_array))
    #a = dict.fromkeys(desired_code_array)
    #b = dict.fromkeys(counterexample)
    #return set(a.keys()), set(b.keys())
    '''for i, row in df.iterrows():
        code = ''
        if row['upper_shadow'] > high_band:
            code += '61'
        elif row['upper_shadow'] > low_band:
            code += '52'

        if row['body'] > high_band:
            code += '6'
        elif row['body'] > low_band:
            code += '5'
        elif row['body'] > 0:
            code += '4'
        elif row['body'] > -low_band:
            code += '3'
        elif row['body'] > -high_band:
            code += '2'
        else:
            code += '1'

        if row['lower_shadow'] < -high_band:
            code += '16'
        elif row['lower_shadow'] < -low_band:
            code += '25'

        if len(code_array) >= 10:
            code_array.pop(0)
        code_array.append(code)
        df.loc[i, 'candlestick_code'] = ''.join(code_array)'''
