from mt5 import mt_datasource
import indicators
import pandas as pd
from indicators import cps


def get_validate_result(data, code, days):
    result = [code, 0, 0, 0]
    label_name = 'label' + str(days)
    for i, row in data.iterrows():
        model = str(row['candlestick_code'])[-len(code):]
        # grade = fuzz.ratio(code, model)
        if model == code:
            if row[label_name] == 1:
                result[1] += 1
            else:
                result[2] += 1
            result[3] += 1
    return result


def in_patterns(code_array, code):
    for i in range(len(code_array)):
        if code[:-len(code_array[i])] == code_array[i]:
            return True
    return False


class CodeTest:
    def __init__(self, log_callback):
        self.explore_symbol = None
        self.datasource = mt_datasource()
        self.log_callback = log_callback

    def log(self, msg, stress):
        self.log_callback(msg, stress)

    def get_data(self, symbol, timeframe, start_date, end_date):
        self.log('start testing from %s, timeframe %s' % (symbol, timeframe), False)
        data = self.datasource.get_df_for_display(symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        self.log('add_indicators', False)
        indicators.add_indicators(data)
        self.log('add_candlestick_code', False)
        std_length = 1000
        indicators.add_candlestick_code(data, std_length=std_length)
        for i in range(len(cps)):
            cp = cps[i][0]
            indicators.add_candle_pattern(data, cp)
        self.log('add_labels', False)
        indicators.add_multiple_labels(data, max_day=30)
        self.log('get code from %s, timeframe %s' % (symbol, timeframe), False)
        return data

    def get_backtest(self, symbol, timeframe, start_date, end_date):
        df = self.get_data(symbol, timeframe, start_date, end_date)
        code_array = []
        for code_len in range(4, 10):
            self.log('start code length ' + str(code_len), False)
            test_df = pd.read_csv('outcome/result-1-60-' + str(code_len) + '.csv')
            for i, test_row in test_df.iterrows():
                if i < 12 or test_row['rate'] >= 60:
                    code_array.append(test_row['Name'])

        df['strategy1'] = 0.0
        df['strategy2'] = 0.0

        strategy1 = 0.0
        strategy2 = 0.0
        for i, row in df.iterrows():
            if row['close_after1'] is not None:
                strategy1 += row['close_after1'] - row['close']
                df.loc[i, 'strategy1'] = strategy1
                if in_patterns(code_array, row['candlestick_code']):
                    strategy2 += row['close_after1'] - row['close']
                df.loc[i, 'strategy2'] = strategy2
        print(df)
        return df

    def start_test(self, symbol, timeframe, start_date, end_date):
        # self.explore_symbol = self.get_random_symbol()
        '''self.log('start testing from %s, timeframe %s' % (symbol, timeframe), False)
        data = self.datasource.get_df_for_display(symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        self.log('add_indicators', False)
        indicators.add_indicators(data)
        self.log('add_candlestick_code', False)
        std_length = 1000
        indicators.add_candlestick_code(data, std_length=std_length)
        for i in range(len(cps)):
            cp = cps[i][0]
            indicators.add_candle_pattern(data, cp)
        self.log('add_labels', False)
        indicators.add_multiple_labels(data, max_day=30)
        self.log('get code from %s, timeframe %s' % (symbol, timeframe), False)'''
        data = self.get_data(symbol, timeframe, start_date, end_date)

        for days in [1, 10, 20, 30]:
            self.log('start days ' + str(days), False)
            for threshold in range(60, 80, 10):
                self.log('start threshold ' + str(threshold), False)
                for code_len in range(4, 11):
                    self.log('start code length ' + str(code_len), False)
                    test_df = pd.read_csv(
                        'outcome/result-' + str(days) + '-' + str(threshold) + '-' + str(code_len) + '.csv')
                    # test_pattern_name_array = test_df['Name'].tolist()
                    test_pattern_name_array = []

                    result_dict = {}
                    for i, test_row in test_df.iterrows():
                        if i < 12 or test_row['rate'] > 60:
                            test_pattern_name_array.append(test_row['Name'])
                            result_dict.setdefault(test_row['Name'], {'profit': 0.0, 'occurrence': 0})
                    test_pattern_name_array.append('sum')
                    result_dict.setdefault('sum', {'profit': 0.0, 'occurrence': 0})

                    for i, row in data.iterrows():
                        for pattern_name in test_pattern_name_array[:11]:
                            if row[pattern_name] == 100:
                                if row['close_after' + str(days)] is not None:
                                    result_dict[pattern_name]['profit'] += row['close_after' + str(days)] - row['close']
                                    result_dict[pattern_name]['occurrence'] += 1

                        for pattern_name in test_pattern_name_array[12:-1]:
                            if row['candlestick_code'][-len(pattern_name):] == pattern_name:
                                result_dict[pattern_name]['profit'] += row['close_after' + str(days)] - row['close']
                                result_dict[pattern_name]['occurrence'] += 1

                    result_array = []
                    total_profit, total_occurrence = 0, 0
                    for k, v in result_dict.items():
                        if k in test_pattern_name_array[12:-1]:
                            total_profit += v['profit']
                            total_occurrence += v['occurrence']
                        if k == 'sum':
                            item = [k, total_profit, total_occurrence]
                        else:
                            item = [k, v['profit'], v['occurrence']]
                        result_array.append(item)
                    export_df = pd.DataFrame(result_array,
                                             columns=['Name', 'profit', 'occurrence'])
                    export_df.to_csv(
                        'outcome/test-' + str(days) + '-' + str(threshold) + '-' + str(code_len) + '.csv')
