from mt5 import mt_datasource
import indicators
from indicators import cps
from thefuzz import fuzz
import random
import pandas as pd


def get_validate_result(data, code, days):
    result = [code, 0, 0, 0]
    label_name = 'label' + str(days)
    for i, row in data.iterrows():
        model = str(row['candlestick_code'])[-len(code):]
        # grade = fuzz.ratio(code, model)
        if model == code:
            if row[label_name] == 1:
                result[3] += 1
                result[1] += 1
            elif row[label_name] == -1:
                result[3] += 1
                result[2] += 1

    return result


def stat_predefined_pattern(data, days=10):

    #indicators.add_price_change(data, days=days)

    result = []
    for i in range(len(cps)):
        cp = 'CDL' + cps[i][0]
        direction = cps[i][1]
        if direction != 100:
            continue

        indicators.add_candle_pattern(data, cp, direction=direction)
        #occurrence = len(data[data[cp] == direction])
        bullish_rows = data.loc[(data[cp] == 100) & (data['label'+str(days)] == 1)]
        bullish_count = len(bullish_rows)
        bearish_rows = data.loc[(data[cp] == 100) & (data['label' + str(days)] == -1)]
        bearish_count = len(bearish_rows)
        occurrence = bullish_count + bearish_count
        p_rate = 0
        if occurrence != 0:
            p_rate = bullish_count*100//occurrence
        result.append([cp, cps[i][2], bullish_count, bearish_count, occurrence, p_rate])

    return result


class CodeExplorer:
    def __init__(self, log_callback):
        self.explore_symbol = None
        self.datasource = mt_datasource()
        self.log_callback = log_callback

    def log(self, msg, stress):
        self.log_callback(msg, stress)

    def start_exploring(self, symbol, timeframe, start_date, end_date):
        # self.explore_symbol = self.get_random_symbol()
        self.log('start exploring from %s, timeframe %s' % (symbol, timeframe), False)
        data = self.datasource.get_df_for_display(symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        self.log('add_indicators', False)
        indicators.add_indicators(data)
        self.log('add_candlestick_code', False)
        std_length = 1000
        indicators.add_candlestick_code(data, std_length=std_length)
        #self.log('add_labels', False)
        #indicators.add_multiple_labels(data, max_day=30)
        self.log('get code from %s, timeframe %s' % (symbol, timeframe), False)
        training_set = data[std_length:]

        data_length = len(data)
        self.log('data_length= ' + str(data_length), False)
        #training_length, validate_length, test_length = int(data_length * 0.6), int(data_length * 0.2), int(
        #    data_length * 0.2)
        #training_set = data[0: training_length]
        #validate_set = data[training_length: training_length + validate_length]
        #test_set = data[-test_length:]

        for days in [1]:
            stat_result = stat_predefined_pattern(training_set, days=days)
            self.log('start days ' + str(days), False)
            export_df = pd.DataFrame(stat_result, columns=['Name', 'length', 'increase', 'decrease', 'occurrence', 'rate'])
            export_df.to_csv('outcome1/result-all.csv')
            '''for threshold in range(60, 70, 10):
                self.log('start threshold ' + str(threshold), False)
                for code_len in range(4, 10):
                    self.log('start code length ' + str(code_len), False)
                    if code_len <= 7:
                        occurrence_check = 10
                    else:
                        occurrence_check = 10
                    single_result = stat_result.copy()
                    stat_data = self.get_codes_by_labels(training_set, code_len, days)
                    print(stat_data)
                    sum_data = ['sum', 0, 0, 0, 0]
                    for i in range(len(stat_data)):
                        p_rate = stat_data[i][2] * 100 // stat_data[i][1]
                        if p_rate > threshold and stat_data[i][1] > occurrence_check:
                        #if p_rate > threshold:
                            code = stat_data[i][0]
                            self.log('find code %s, increase=%s, decrease=%s, rate=%s' % (code, str(stat_data[i][2])
                                                                                          , str(stat_data[i][3]), str(p_rate))
                                     , False)
                            if self.validate_code(validate_set, code, threshold, days):
                                test_result = self.test_code(test_set, code, days)
                                single_result.append(test_result)
                                sum_data[1] = sum_data[1] + test_result[1]
                                sum_data[2] = sum_data[2] + test_result[2]
                                sum_data[3] = sum_data[3] + test_result[3]

                    sum_data[4] = 0 if sum_data[3] == 0 else sum_data[1] * 100 // sum_data[3]
                    single_result.append(sum_data)

                    export_df = pd.DataFrame(single_result, columns=['Name', 'increase', 'decrease', 'occurrence', 'rate'])
                    export_df.to_csv('outcome1/result-'+str(days)+'-'+str(threshold)+'-'+str(code_len)+'.csv')
                    self.log('export code length ' + str(code_len), False)'''

    def test_code(self, data, code, days):
        self.log('test code %s' % code, False)

        result = get_validate_result(data, code, days)
        if result[3] == 0:
            p_rate = 0
        else:
            p_rate = result[1] * 100 // result[3]

        self.log(
            'test result increase=%s, decrease=%s, rate=%s' % (str(result[1]), str(result[2])
                                                               , str(p_rate)), False)
        result.append(p_rate)
        return result

    def validate_code(self, data, code, threshold, days):
        self.log('validate code %s' % code, False)

        result = get_validate_result(data, code, days)
        if result[3] > 0:
            p_rate = result[1] * 100 / result[3]
            self.log(
                'validate result increase=%s, decrease=%s, rate=%s' % (str(result[1]), str(result[2])
                                                                   , str(p_rate)), False)
            if p_rate > threshold:
                return True
            else:
                return False
        else:
            self.log('failed to find code in validate set', False)
            return False

    def get_random_symbol(self):
        pass
        #return self.symbols[random.randint(0, len(self.symbols) - 1)]

    def validate_code_in_all(self, code):
        for i in range(len(self.symbols)):
            symbol = self.symbols[i]
            if symbol != self.explore_symbol:
                self.validate_code_in_one(code, symbol)

    def validate_code_in_one(self, code, symbol):
        self.log('validate in symbol %s' % symbol)
        data = self.datasource.get_df_for_display(symbol, timeframe=self.timeframe)
        indicators.add_candlestick_code(data)
        indicators.add_labels(data, days=5)
        result = [0, 0, 0]
        for i, row in data.iterrows():
            model = str(row['candlestick_code'])[-len(code):]
            # grade = fuzz.ratio(code, model)
            if model == code:
                if row['change_10'] > 0:
                    result[0] += 1
                else:
                    result[1] += 1
                result[2] += 1
        if result[2] > 0:
            p_rate = result[0] * 100 / result[2]
            self.log(
                'validate in symbol %s, increase=%s, decrease=%s, rate=%s' % (symbol, str(result[0]), str(result[1])
                                                                              , str(p_rate)))

    def get_codes_by_labels(self, data, ref_length, days):
        models = {}
        stat_data = []
        label_name = 'label' + str(days)

        for i, row in data.iterrows():
            model = str(row['candlestick_code'])[-ref_length:]
            if models.get(model) is None:
                if row[label_name] == 1:
                    #models[model] = [1, 1, 0, row['max'], row['min'], row['avg']]
                    models[model] = [1, 1, 0]
                elif row[label_name] == -1:
                    #models[model] = [1, 0, 1, row['max'], row['min'], row['avg']]
                    models[model] = [1, 0, 1]
                else:
                    #models[model] = [1, 0, 0, row['max'], row['min'], row['avg']]
                    models[model] = [0, 0, 0]
            else:


                #if row['max'] > models[model][3]:
                #    models[model][3] = row['max']

                #if row['min'] < models[model][4]:
                #    models[model][4] = row['min']

                #models[model][5] = row['avg']

                if row[label_name] == 1:
                    models[model][0] += 1
                    models[model][1] += 1
                elif row[label_name] == -1:
                    models[model][0] += 1
                    models[model][2] += 1
                #else:
                #    models[model][3] += 1

        for key in models:
            if models[key][0] > 2:
                stat_data.append([key, models[key][0], models[key][1], models[key][2]])
        return stat_data


    def get_codes(self, data, ref_length):
        models = {}
        stat_data = []

        for i, row in data.iterrows():
            model = str(row['candlestick_code'])[-ref_length:]
            if models.get(model) is None:
                if row['label'] == 1:
                    models[model] = [1, 1, 0, row['max'], row['min'], row['avg']]
                elif row['label'] == -1:
                    models[model] = [1, 0, 1, row['max'], row['min'], row['avg']]
                else:
                    models[model] = [1, 0, 0, row['max'], row['min'], row['avg']]
            else:
                models[model][0] += 1

                if row['max'] > models[model][3]:
                    models[model][3] = row['max']

                if row['min'] < models[model][4]:
                    models[model][4] = row['min']

                models[model][5] = row['avg']

                if row['label'] == 1:
                    models[model][1] += 1
                elif row['label'] == -1:
                    models[model][2] += 1
                else:
                    models[model][3] += 1

        for key in models:
            if models[key][0] > 2:
                stat_data.append([key, models[key][0], models[key][1], models[key][2],
                                  str(models[key][1] * 100 // models[key][0]) + '%',
                                  str(models[key][2] * 100 // models[key][0]) + '%',
                                  '%.2f' % (models[key][3] * 100) + '%',
                                  '%.2f' % (models[key][4] * 100) + '%',
                                  models[key][5] // models[key][0]])
        return stat_data
