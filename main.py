import datetime
import time
import threading

import MetaTrader5
import matplotlib.pyplot as plt
import wx
import wx.grid
import wx.adv
import wx.lib.agw.aui as aui
import wx.lib.mixins.inspection as wit

import mplfinance as mpf
from matplotlib import animation
from matplotlib.backends.backend_wxagg import (
    FigureCanvasWxAgg as FigureCanvas,
    NavigationToolbar2WxAgg as NavigationToolbar)

import indicators
from code_explore import CodeExplorer
from code_test import CodeTest
from indicators import get_supported_cdl
from indicators import cps
from mt5 import mt_datasource
from trend import Trend
import pandas as pd
import numpy as np
from thefuzz import fuzz

SUPPORTED_TIMEFRAME = [MetaTrader5.TIMEFRAME_M1, MetaTrader5.TIMEFRAME_M5, MetaTrader5.TIMEFRAME_H1,
                       MetaTrader5.TIMEFRAME_H4, MetaTrader5.TIMEFRAME_D1]

SYMBOLS = []


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args, **kwargs)

        self.codeCtrl = None
        self.plotter = None
        self.cpItems = {}
        self.init_ui()

        self.timeframe = MetaTrader5.TIMEFRAME_M1

    def init_ui(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileItem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        menubar.Append(fileMenu, '&File')

        indicatorMenu = wx.Menu()
        menubar.Append(indicatorMenu, '&Indicators')
        candleStickMenu = wx.Menu()
        cpItemNames = get_supported_cdl()
        # cpItemNames = ['HAMMER', 'PIERCING', 'ENGULFING', 'MORNINGSTAR', '3WHITESOLDIERS', 'MARUBOZU', '3INSIDE'
        #               , 'HARAMI', '3OUTSIDE', 'ONNECK', 'COUNTERATTACK', '-', 'HANGINGMAN', 'DARKCLOUDCOVER', 'EVENINGSTAR'
        #               , '3BLACKCROWS']
        for cpItemName in cpItemNames:
            if cpItemName == '-':
                candleStickMenu.AppendSeparator()
            else:
                cpId = wx.NewId()
                cpItem = candleStickMenu.Append(cpId, cpItemName)
                self.cpItems[cpId] = cpItem
                self.Bind(wx.EVT_MENU, self.OnCpSelected, cpItem)

        indicatorMenu.Append(wx.ID_ANY, 'CandleStick Pattern', candleStickMenu)

        timeframe_menu = wx.Menu()
        m1_item = timeframe_menu.Append(wx.ID_ANY, 'M1')
        self.Bind(wx.EVT_MENU, self.OnM1Selected, m1_item)
        m5_item = timeframe_menu.Append(wx.ID_ANY, 'M5')
        self.Bind(wx.EVT_MENU, self.OnM5Selected, m5_item)
        h1_item = timeframe_menu.Append(wx.ID_ANY, 'H1')
        self.Bind(wx.EVT_MENU, self.OnH1Selected, h1_item)
        h4_item = timeframe_menu.Append(wx.ID_ANY, 'H4')
        self.Bind(wx.EVT_MENU, self.OnH4Selected, h4_item)
        d1_item = timeframe_menu.Append(wx.ID_ANY, 'D1')
        self.Bind(wx.EVT_MENU, self.OnD1Selected, d1_item)
        menubar.Append(timeframe_menu, '&Timeframe')

        statistics_menu = wx.Menu()
        candle_stick_item = statistics_menu.Append(wx.ID_ANY, 'Candlestick pattern')
        self.Bind(wx.EVT_MENU, self.OnCandlestickStatistics, candle_stick_item)
        candle_code_item = statistics_menu.Append(wx.ID_ANY, 'Candle code')
        self.Bind(wx.EVT_MENU, self.OnCandleCodeStatistics, candle_code_item)
        candle_match_item = statistics_menu.Append(wx.ID_ANY, 'Candle matching')
        self.Bind(wx.EVT_MENU, self.OnCandleMatchStatistics, candle_match_item)
        candle_test_item = statistics_menu.Append(wx.ID_ANY, 'Candle testing')
        self.Bind(wx.EVT_MENU, self.OnCandleTestStatistics, candle_test_item)
        candle_search_item = statistics_menu.Append(wx.ID_ANY, 'Candle searching')
        self.Bind(wx.EVT_MENU, self.OnCandleSearchStatistics, candle_search_item)
        menubar.Append(statistics_menu, '&Statistics')

        automaton_menu = wx.Menu()
        genetic_item = automaton_menu.Append(wx.ID_ANY, 'genetic')
        self.Bind(wx.EVT_MENU, self.OnGeneticAutomaton, genetic_item)
        menubar.Append(automaton_menu, '&Automaton')

        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.OnQuit, fileItem)

        toolbar = self.CreateToolBar()
        start_tool = toolbar.AddTool(wx.ID_ANY, 'Start', wx.Bitmap('img/start.png'))
        stop_tool = toolbar.AddTool(wx.ID_ANY, 'Stop', wx.Bitmap('img/stop.png'))
        self.codeCtrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(50, -1))
        toolbar.AddControl(self.codeCtrl)
        next_tool = toolbar.AddTool(wx.ID_ANY, 'Next', wx.Bitmap('img/right.png'))
        toolbar.Realize()
        self.Bind(wx.EVT_TOOL, self.OnResume, start_tool)
        self.Bind(wx.EVT_TOOL, self.OnPause, stop_tool)
        self.Bind(wx.EVT_TOOL, self.OnSearchNext, next_tool)

        self.SetSize(wx.DisplaySize())

        self.plotter = PlotNotebook(self)
        self.plotter.add()

    def OnQuit(self, e):
        self.Close()

    def OnM1Selected(self, e):
        self.timeframe = MetaTrader5.TIMEFRAME_M1
        self.plotter.current_plot.reload(timeframe=MetaTrader5.TIMEFRAME_M1)

    def OnM5Selected(self, e):
        self.timeframe = MetaTrader5.TIMEFRAME_M5
        self.plotter.current_plot.reload(timeframe=MetaTrader5.TIMEFRAME_M5)

    def OnH1Selected(self, e):
        self.timeframe = MetaTrader5.TIMEFRAME_H1
        self.plotter.current_plot.reload(timeframe=MetaTrader5.TIMEFRAME_H1)

    def OnH4Selected(self, e):
        self.timeframe = MetaTrader5.TIMEFRAME_H4
        self.plotter.current_plot.reload(timeframe=MetaTrader5.TIMEFRAME_H4)

    def OnD1Selected(self, e):
        self.timeframe = MetaTrader5.TIMEFRAME_D1
        self.plotter.current_plot.reload(timeframe=MetaTrader5.TIMEFRAME_D1)

    def OnCpSelected(self, e):
        self.plotter.current_plot.reload(cp=self.cpItems[e.GetId()].ItemLabelText)

    def OnCandlestickStatistics(self, e):
        cpStatFrame = CpStatFrame()

    def OnGeneticAutomaton(self, e):
        GeneticAutomatonFrame(self.plotter.current_plot)

    def OnCandleCodeStatistics(self, e):
        CodeStatFrame(self.plotter.current_plot)

    def OnCandleMatchStatistics(self, e):
        CodeMatchFrame(self.plotter.current_plot)

    def OnCandleTestStatistics(self, e):
        CodeTestFrame()

    def OnCandleSearchStatistics(self, e):
        CodeSearchFrame()

    def OnResume(self, e):
        self.plotter.current_plot.resume()

    def OnPause(self, e):
        self.plotter.current_plot.pause()

    def OnSearchNext(self, e):
        code = str(self.codeCtrl.GetValue())
        self.plotter.current_plot.code = code
        self.plotter.current_plot.search_next()


class Plot(wx.Panel):
    def __init__(self, parent, symbol=None, id=-1, dpi=None, **kwargs):
        super().__init__(parent, id=id, **kwargs)
        self.code = None
        self.trend = None
        self.tick_thread = None
        self.ta = None
        self.candle_extra_ax = None
        self.axes = None
        self.timeframe = None
        self.datasource = mt_datasource()
        self.cp = None
        self.data = None
        self.code_set = None
        self.counter_set = None
        self.ani = None
        self.toolbar = None
        self.figure = None
        self.canvas = None
        self.symbol = symbol
        self.search_start = 0
        self.show_start, self.show_end = -200, 0
        print('start loading data %d' % time.time())
        self.load_data()
        print('start rendering data %d' % time.time())
        self.render()
        print('end loading data %d' % time.time())

    def render(self):
        data = self.data[-200:]

        apds = [

        ]
        if self.ta is not None:
            apds.append(mpf.make_addplot(data[[self.ta]], panel=1))

        self.figure, self.axes = mpf.plot(
            data,
            addplot=apds,
            type="candle",
            # mav=(10, 30, 60),
            style="yahoo",
            returnfig=True,
            closefig=True
        )

        self.candle_extra_ax = self.axes[0].twinx()
        self.candle_extra_ax.sharey(self.axes[0])
        self.set_animation()

        if self.canvas is not None:
            self.canvas.Destroy()
        # self.figure = mpf.figure(dpi=dpi, figsize=(2, 2))
        self.canvas = FigureCanvas(self, -1, self.figure)
        if self.toolbar is not None:
            self.toolbar.Destroy()
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND | wx.BOTTOM)
        self.SetSizer(sizer)
        # sizer.GetContainingWindow().Layout()

    def set_animation(self):

        def animate(ival):
            self.axes[0].clear()
            self.candle_extra_ax.clear()
            if self.ta is not None:
                self.axes[2].clear()
            if self.show_start < 0:
                data = self.data[self.show_start:]
            else:
                data = self.data[self.show_start:self.show_end]
            aps = []
            if self.ta is not None:
                aps.append(mpf.make_addplot(data[[self.ta]], ax=self.axes[2], panel=1))
            # mpf.make_addplot(data[['wave']], ax=self.candle_extra_ax, type='scatter', markersize=100,
            #                        marker='.'),
            # mpf.make_addplot(data[['wave1']], ax=self.candle_extra_ax, type='scatter', markersize=100,
            #                        marker='1'),
            # mpf.make_addplot(data[['swing_high']], ax=self.candle_extra_ax, type='scatter', markersize=100,
            #                        marker='.'),
            # mpf.make_addplot(data[['label_big_move']], ax=self.candle_extra_ax, type='scatter', markersize=100,marker='.')
            # aps.append(mpf.make_addplot(data[['big_up_marker']], ax=self.candle_extra_ax, type='scatter', markersize=100,
            #                            marker='.'))
            if self.cp is not None:
                if len(data[data[self.cp] == 100]) > 0:
                    aps.append(
                        mpf.make_addplot(data[self.cp + '_marker'], ax=self.candle_extra_ax, type='scatter',
                                         markersize=100,
                                         marker='.'))
                if len(data[data[self.cp] == -100]) > 0:
                    aps.append(
                        mpf.make_addplot(data[self.cp + '_marker_bear'], ax=self.candle_extra_ax, type='scatter',
                                         markersize=100,
                                         marker='.'))
            if self.code is not None:
                aps.append(
                    mpf.make_addplot(data['search'], ax=self.candle_extra_ax, type='scatter',
                                     markersize=100,
                                     marker='.'))
            mpf.plot(
                data,
                ax=self.axes[0],
                type="candle",
                addplot=aps,
                # mav=(10, 30, 60),
                style="yahoo",
                returnfig=True,
                closefig=True
            )

        self.ani = animation.FuncAnimation(self.figure, animate, interval=2000, repeat=True)

    def search_by_code(self, code):
        self.code = code
        for i in range(self.search_start, len(self.data)):
            index = self.data.index.values[i]
            if str(self.data.loc[index, 'candlestick_code']).endswith(str(code)):
                self.search_start = i + 1
                self.data.loc[index, 'search'] = self.data.loc[index, 'high'] * 1.001
                if i < 100:
                    self.show_start = 0
                else:
                    self.show_start = i - 100
                self.show_end = i + 100
                return
        self.search_start = 0

    def search_next(self):
        if self.code is not None:
            self.search_by_code(self.code)

    def load_data(self, timeframe=None):
        self.timeframe = timeframe
        self.data = self.datasource.get_df_for_display(self.symbol, timeframe=self.timeframe)
        print('generate trend data %d' % time.time())
        self.trend = Trend(self.data)

        if self.cp is not None:
            indicators.add_candle_pattern(self.data, self.cp)
            increase_count = len(self.data[self.data[self.cp + '_after'] >= 0])
            decrease_count = len(self.data[self.data[self.cp + '_after'] < 0])
            continue_count = len(self.data[self.data[self.cp + '_continue'] < 0])
            wx.MessageBox(self.cp + ': increase_count:' + increase_count, 'candlestick statistics', wx.OK)

        print('generate indicator data %d' % time.time())
        if self.ta is not None:
            indicators.add_indicator(self.data, self.ta)
        print('generate indicators data %d' % time.time())
        indicators.add_indicators(self.data)
        print('generate candlestick data %d' % time.time())
        indicators.add_one_day_label(self.data)
        # self.code_set, self.counter_set = indicators.add_candlestick_code(self.data)
        indicators.add_candlestick_code(self.data)
        print('generate label data %d' % time.time())
        # indicators.add_labels(self.data, days=5)
        print('finish label data %d' % time.time())
        self.data['search'] = np.NAN

        self.tick_thread = threading.Thread(target=self.datasource.update_candle,
                                            args=(self.symbol, self.data))
        self.tick_thread.start()

    def reload(self, cp=None, timeframe=None, ta=None):
        if timeframe is not None:
            self.timeframe = timeframe
            self.data = self.datasource.get_df_for_display(self.symbol, timeframe=self.timeframe)
            indicators.add_candlestick_code(self.data)
            indicators.add_labels(self.data, days=5)
            # self.trend = Trend(self.data)

            self.tick_thread = threading.Thread(target=self.datasource.update_candle,
                                                args=(self.symbol, self.data))
            self.tick_thread.start()

        if cp is not None:
            self.cp = cp
            indicators.add_candle_pattern(self.data, self.cp)
            '''total_count = len(self.data[self.data[self.cp] == 100])
            increase_count = len(self.data[self.data[self.cp + '_after'] >= 0])
            decrease_count = len(self.data[self.data[self.cp + '_after'] < 0])
            continue_count = len(self.data[self.data[self.cp + '_continue'] < 0])
            message = self.cp + '-- increase_count:' + str(increase_count) \
                      + ', decrease_count:' + str(decrease_count) \
                      + ', continue_count:' + str(continue_count) \
                      + ', total_count:' + str(total_count)
            wx.MessageBox(message, 'candlestick statistics', wx.OK)'''
        else:
            if self.cp is not None:
                indicators.add_candle_pattern(self.data, self.cp)

        if ta is not None:
            self.ta = ta
            indicators.add_indicator(self.data, self.ta)
        else:
            if self.ta is not None:
                indicators.add_indicator(self.data, self.ta)

    def pause(self):
        self.ani.pause()

    def resume(self):
        # self.load_data()
        self.ani.resume()


class CodeSearchFrame(wx.Frame):
    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent=parent, title='candle code searching', pos=(50, 60), size=(250, 250))
        self.search_thread = None
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        toolbar = self.CreateToolBar()
        self.symbol_choice = wx.Choice(toolbar, choices=SYMBOLS)
        self.start_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.end_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.timeframe_ctrl = wx.Choice(toolbar, choices=['M1', 'M5', 'H1', 'H4', 'D1'])
        self.period_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(50, -1))
        self.period_ctrl.SetValue('5')
        btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='stat')
        self.Bind(wx.EVT_BUTTON, self.search, btn_ctrl)
        btn_test_ctrl = wx.Button(toolbar, wx.ID_ANY, label='test')
        self.Bind(wx.EVT_BUTTON, self.test, btn_test_ctrl)
        btn_plot = wx.Button(toolbar, wx.ID_ANY, label='plot')
        self.Bind(wx.EVT_BUTTON, self.plot, btn_plot)
        toolbar.AddControl(self.symbol_choice)
        toolbar.AddControl(self.start_date_ctrl)
        toolbar.AddControl(self.end_date_ctrl)
        toolbar.AddControl(self.timeframe_ctrl)
        toolbar.AddControl(self.period_ctrl)
        toolbar.AddControl(btn_ctrl)
        toolbar.AddControl(btn_test_ctrl)
        toolbar.AddControl(btn_plot)
        toolbar.Realize()

        # assign the DataFrame to df

        # declare the grid and assign data
        self.log_ctrl = wx.TextCtrl(self, wx.ID_ANY, size=(1000, 500), style=wx.TE_MULTILINE)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.log_ctrl, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        self.Bind(wx.EVT_CLOSE, self.exit)

    def exit(self, event):
        self.Destroy()

    def search(self, event):
        symbol = SYMBOLS[self.symbol_choice.GetCurrentSelection()]
        start_date = self.start_date_ctrl.GetValue()
        end_date = self.end_date_ctrl.GetValue()
        start_date = start_date.Format('%d/%m/%y %H:%M:%S')
        start_date = datetime.datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
        end_date = end_date.Format('%d/%m/%y %H:%M:%S')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%y %H:%M:%S')
        timeframe = SUPPORTED_TIMEFRAME[self.timeframe_ctrl.GetCurrentSelection()]
        # period = int(self.period_ctrl.GetValue())
        code_explorer = CodeExplorer(lambda msg, stress: self.add_log(msg, stress))
        self.search_thread = threading.Thread(target=code_explorer.start_exploring,
                                              args=(symbol, timeframe, start_date, end_date))
        self.search_thread.start()

    def test(self, event):
        symbol = SYMBOLS[self.symbol_choice.GetCurrentSelection()]
        start_date = self.start_date_ctrl.GetValue()
        end_date = self.end_date_ctrl.GetValue()
        start_date = start_date.Format('%d/%m/%y %H:%M:%S')
        start_date = datetime.datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
        end_date = end_date.Format('%d/%m/%y %H:%M:%S')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%y %H:%M:%S')
        timeframe = SUPPORTED_TIMEFRAME[self.timeframe_ctrl.GetCurrentSelection()]
        # period = int(self.period_ctrl.GetValue())
        code_test = CodeTest(lambda msg, stress: self.add_log(msg, stress))
        self.search_thread = threading.Thread(target=code_test.start_test,
                                              args=(symbol, timeframe, start_date, end_date))
        self.search_thread.start()

    def plot(self, event):
        symbol = SYMBOLS[self.symbol_choice.GetCurrentSelection()]
        start_date = self.start_date_ctrl.GetValue()
        end_date = self.end_date_ctrl.GetValue()
        start_date = start_date.Format('%d/%m/%y %H:%M:%S')
        start_date = datetime.datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
        end_date = end_date.Format('%d/%m/%y %H:%M:%S')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%y %H:%M:%S')
        timeframe = SUPPORTED_TIMEFRAME[self.timeframe_ctrl.GetCurrentSelection()]
        code_test = CodeTest(lambda msg, stress: self.add_log(msg, stress))
        data = code_test.get_backtest(symbol, timeframe, start_date, end_date)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(data.index, data['strategy1'], label='strategy1')
        ax.plot(data.index, data['strategy2'], label='strategy2')
        ax.legend()
        plt.show()

    def add_log(self, msg, stress):
        self.log_ctrl.AppendText('\n')
        if stress:
            self.log_ctrl.SetDefaultStyle(wx.TextAttr(wx.RED))
            self.log_ctrl.AppendText(msg)
        else:
            self.log_ctrl.SetDefaultStyle(wx.TextAttr(wx.BLACK))
            self.log_ctrl.AppendText(msg)


class CodeStatFrame(wx.Frame):
    def __init__(self, plot, parent=None):
        wx.Frame.__init__(self, parent=parent, title='candle code statistics', pos=(50, 60), size=(250, 250))
        self.plot = plot
        self.df = plot.data
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        self.grid = wx.grid.Grid(self, -1)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.grid, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        '''top_codes, bottom_codes = [], []
        for i, row in self.df.iterrows():
            if row['swing'] == 1:
                top_codes.append(row['candlestick_code'])
            elif row['swing'] == -1:
                bottom_codes.append(row['candlestick_code'])'''

        top_stat = self.stat(10)

        self.stat_df = pd.DataFrame(top_stat,
                                    columns=['code', 'total', 'bull', 'bear', 'bull_p', 'bear_p', 'max', 'min', 'avg'])
        # self.stat_df['percentage'] = self.stat_df['increase'] * 100 / self.stat_df['total']
        self.stat_df.sort_values('total', ascending=False, inplace=True)
        table = DataTable(self.stat_df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnSelect, self.grid)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnSort, self.grid)

    def stat(self, ref_length):
        models = {}
        stat_data = []

        # indicators.add_price_change(self.df, days=5)

        for i, row in self.df.iterrows():
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

    def OnSelect(self, e):
        code = self.stat_df.iloc[e.GetRow(), 0]
        print(code)
        self.plot.search_by_code(code)

    def OnSort(self, e):
        print(e.GetCol())


class CodeMatchFrame(wx.Frame):
    def __init__(self, plot, parent=None):
        wx.Frame.__init__(self, parent=parent, title='candle code matching', pos=(50, 60), size=(250, 250))
        self.plot = plot
        self.df = plot.data
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        self.grid = wx.grid.Grid(self, -1)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.grid, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        '''top_codes, bottom_codes = [], []
        for i, row in self.df.iterrows():
            if row['swing'] == 1:
                top_codes.append(row['candlestick_code'])
            elif row['swing'] == -1:
                bottom_codes.append(row['candlestick_code'])'''

        # top_stat = self.stat(10)
        # indicators.add_candlestick_code(self.df)
        # indicators.add_labels(data, days=days)
        # print(self.df)

        group_df = self.df[['candlestick_code3', 'label_increase', 'label_decrease']] \
            .groupby('candlestick_code3').agg({'label_increase': 'sum', 'label_decrease': 'sum'})
        print(group_df)
        group_df['occurrence'] = group_df['label_increase'] + group_df['label_decrease']
        group_df['percentage'] = group_df['label_increase'] / group_df['occurrence']

        # self.stat_df = pd.DataFrame(top_stat, columns=['code', 'occurrence', 'i', 'd', 's'])
        # self.stat_df['percentage'] = self.stat_df['increase'] * 100 / self.stat_df['total']
        self.stat_df = group_df
        self.stat_df.sort_values('percentage', ascending=False, inplace=True)
        table = DataTable(self.stat_df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnSelect, self.grid)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnSort, self.grid)

    def stat(self, ref_length):
        models = {}
        stat_data = []
        bull_codes = {}
        bear_codes = {}

        # indicators.add_price_change(self.df, days=5)

        for i, row in self.df.iterrows():
            model = str(row['candlestick_code'])[-ref_length:]
            if row['swing'] == 1 and row['big_up'] == 1:
                if bull_codes.get(model) is None:
                    bull_codes[model] = 1
                else:
                    bull_codes[model] += 1

            # if row['swing'] == -1 and row['big_down'] == 1:
            if row['swing'] == -1:
                if bear_codes.get(model) is None:
                    bear_codes[model] = 1
                else:
                    bear_codes[model] += 1
        print(bull_codes)

        bull_result = []
        for key in bull_codes:
            found = False
            for result in bull_result:
                grade = fuzz.ratio(result[0], key)
                if grade >= 80:
                    if result[1] < bull_codes.get(key):
                        result[0] = key
                        result[1] = bull_codes.get(key)
                    result[2] += bull_codes.get(key)
                    result[3].append([key, bull_codes.get(key), grade])
                    found = True
                    break
            if not found:
                bull_result.append([key, bull_codes.get(key), bull_codes.get(key), [], 0, 0])
        print(bull_result)
        print(len(bull_result))

        for j in range(len(bull_result)):
            bull_result_item = bull_result[j]
            print(bull_result_item[0])
            if bull_result_item[2] < 10:
                continue
            for i, row in self.df.iterrows():
                model = str(row['candlestick_code'])[-ref_length:]
                grade = fuzz.ratio(bull_result_item[0], model)
                if grade >= 90:
                    if row['change_10'] > 0:
                        bull_result_item[4] += 1
                    else:
                        bull_result_item[5] += 1

        final_result = []
        total_in, total_de = 0, 0
        for bull_result_item in bull_result:
            if bull_result_item[2] >= 10:
                final_result.append([bull_result_item[0], bull_result_item[2], bull_result_item[4],
                                     bull_result_item[5], bull_result_item[3]])
                total_in += bull_result_item[4]
                total_de += bull_result_item[5]
        final_result.append(['sum', 0, total_in, total_de, ''])
        return final_result

    def OnSelect(self, e):
        code = self.stat_df.index[e.GetRow()]
        print(code)
        self.plot.search_by_code(code)

    def OnSort(self, e):
        print(e.GetCol())


class CodeTestFrame(wx.Frame):
    """
    Class used for creating frames other than the main one
    """

    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent=parent, title='code testing', pos=(50, 60), size=(250, 250))
        self.result_df = None
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        toolbar = self.CreateToolBar()
        self.symbol_choice = wx.Choice(toolbar, choices=SYMBOLS)
        self.start_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.end_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.timeframe_ctrl = wx.Choice(toolbar, choices=['M1', 'M5', 'H1', 'H4', 'D1'])
        self.period_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(50, -1))
        self.period_ctrl.SetValue('1')
        self.mode_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(50, -1))
        self.mode_ctrl.SetValue('0')
        self.code_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(100, -1))
        self.occurrence_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(100, -1))
        self.percentage_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(100, -1))
        self.direction_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(100, -1))
        self.direction_ctrl.SetValue('0')
        btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='stat')
        export_btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='export')
        test_btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='test')
        self.Bind(wx.EVT_BUTTON, self.stat, btn_ctrl)
        self.Bind(wx.EVT_BUTTON, self.export, export_btn_ctrl)
        self.Bind(wx.EVT_BUTTON, self.test, test_btn_ctrl)
        toolbar.AddControl(self.symbol_choice)
        toolbar.AddControl(self.start_date_ctrl)
        toolbar.AddControl(self.end_date_ctrl)
        toolbar.AddControl(self.timeframe_ctrl)
        toolbar.AddControl(self.period_ctrl)
        toolbar.AddControl(self.mode_ctrl)
        toolbar.AddControl(self.code_ctrl)
        toolbar.AddControl(btn_ctrl)
        toolbar.AddControl(export_btn_ctrl)
        toolbar.AddControl(self.occurrence_ctrl)
        toolbar.AddControl(self.percentage_ctrl)
        toolbar.AddControl(self.direction_ctrl)
        toolbar.AddControl(test_btn_ctrl)
        toolbar.Realize()

        # assign the DataFrame to df

        # declare the grid and assign data
        self.grid = wx.grid.Grid(self, -1)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.grid, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        self.Bind(wx.EVT_CLOSE, self.exit)

    def exit(self, event):
        self.Destroy()

    def stat(self, event):
        self.load_data()

    def load_data(self):
        symbol = SYMBOLS[self.symbol_choice.GetCurrentSelection()]
        start_date = self.start_date_ctrl.GetValue()
        end_date = self.end_date_ctrl.GetValue()
        start_date = start_date.Format('%d/%m/%y %H:%M:%S')
        start_date = datetime.datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
        end_date = end_date.Format('%d/%m/%y %H:%M:%S')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%y %H:%M:%S')
        timeframe = SUPPORTED_TIMEFRAME[self.timeframe_ctrl.GetCurrentSelection()]
        period = int(self.period_ctrl.GetValue())
        mode = int(self.mode_ctrl.GetValue())
        code = self.code_ctrl.GetValue()
        # print(timeframe)
        datasource = mt_datasource()
        for j in range(5):
            year = start_date.strftime('%Y')
            print(year)
            end_date = start_date.replace(year=start_date.year+1)
            data = datasource.get_df_for_display(symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
            data = data[:-1]
            indicators.add_candlestick_code(data, mode=mode, days=period)
            for i in [0, 3, 4, 5]:
                self.result_df = self.stat_code(data, mode, i)
                self.result_df.to_csv('outcome1/result-s-' + str(i) + '-' + year + '-' + str(mode) + '.csv')
            start_date = end_date
        # print(len(df))
        table = DataTable(self.result_df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

    def stat_code(self, data, mode, code):


        print(mode)
        if str(code) == '0':
            result_array = []
            for cp in cps:
                increase_count = len(data.loc[(data[cp[0]] == cp[1]) & (data['label_increase'] == 1)])
                decrease_count = len(data.loc[(data[cp[0]] == cp[1]) & (data['label_decrease'] == 1)])
                occurrence = increase_count + decrease_count
                direction = 'bullish' if cp[1] == 100 else 'bearish'

                if occurrence > 0:
                    cp_data = data.loc[(data[cp[0]] == cp[1])]
                    if len(cp_data) > 1:
                        candlestick_code = cp_data.iloc[1]['candlestick_code'][-cp[2]:]
                    else:
                        candlestick_code = cp_data.iloc[0]['candlestick_code'][-cp[2]:]
                    result_array.append(
                        [cp[0], cp[2], direction, increase_count, decrease_count, occurrence,
                         round(increase_count / occurrence, 2), candlestick_code])

            return pd.DataFrame(result_array,
                                columns=['Name', 'length', 'direction', 'label_increase', 'label_decrease',
                                         'occurrence', 'percentage', 'code'])
        else:
            group_by = 'candlestick_code' + str(code)

            group_df = data[[group_by, 'label_increase', 'label_decrease']] \
                .groupby(group_by).agg({'label_increase': 'sum', 'label_decrease': 'sum'})
            group_df['occurrence'] = group_df['label_increase'] + group_df['label_decrease']
            group_df['percentage'] = np.round(group_df['label_increase'] / group_df['occurrence'], 2)
            return group_df

    def export(self, event):
        start_date = self.start_date_ctrl.GetValue()
        year = start_date.Format('%y')
        length = str(self.code_ctrl.GetValue())
        mode = str(self.mode_ctrl.GetValue())
        self.result_df.to_csv('outcome1/result-f-' + length + '-' + year + '-' + mode + '.csv')

    def test(self, event):
        year1 = '13'
        year2 = '18'
        length = str(self.code_ctrl.GetValue())
        mode = str(self.mode_ctrl.GetValue())
        occurrence = int(self.occurrence_ctrl.GetValue())
        percentage = float(self.percentage_ctrl.GetValue())
        direction = int(self.direction_ctrl.GetValue())
        df1 = pd.read_csv('outcome1/result-' + length + '-' + year1 + '-' + mode + '.csv')
        #df2 = pd.read_csv('outcome1/result-' + length + '-' + year2 + '-' + mode + '.csv', index_col='candlestick_code'+length)

        if length == '0':
            main_column_name = 'Name'
        else:
            main_column_name = 'candlestick_code'+length

        test_df_array = []
        column_names = ['Name', 'up', 'down', 'train_per', 'train_occ']
        for i in range(2018, 2023):
            test_df = pd.read_csv('outcome1/result-s-' + length + '-' + str(i) + '-' + mode + '.csv', index_col=main_column_name)
            test_df_array.append(test_df)
            column_names.append(str(i)+'_per')
            column_names.append(str(i) + '_occ')
        column_names.append('test_per')
        column_names.append('test_occ')

        result_array = []
        if direction == 0:
            result_df1 = df1.loc[(df1['occurrence'] > occurrence) & (df1['percentage'] >= percentage)]
        else:
            df1['accuracy'] = 1 - df1['percentage']
            result_df1 = df1.loc[(df1['occurrence'] > occurrence) & (df1['accuracy'] >= percentage)]
        for i, row in result_df1.iterrows():
            code = row[main_column_name]
            if direction == 0:
                row_data = [code, row['label_increase'], row['label_decrease'], row['percentage'], row['occurrence']]
            else:
                row_data = [code, row['label_increase'], row['label_decrease'], 1 - row['percentage'], row['occurrence']]
            increase_number = 0
            decrease_number = 0
            for test_df in test_df_array:
                if code in test_df.index:
                    increase_number += test_df.loc[code, 'label_increase']
                    decrease_number += test_df.loc[code, 'label_decrease']
                    if direction == 0:
                        row_data.append(test_df.loc[code, 'percentage'])
                    else:
                        row_data.append(1 - test_df.loc[code, 'percentage'])
                    row_data.append(test_df.loc[code, 'occurrence'])
                else:
                    row_data.append(0)
                    row_data.append(0)
            occurrence = increase_number + decrease_number
            if occurrence == 0:
                row_data.append(0)
                row_data.append(0)
            else:
                if direction == 0:
                    row_data.append(increase_number/occurrence)
                else:
                    row_data.append(decrease_number / occurrence)
                row_data.append(occurrence)
            result_array.append(row_data)
            #if code in df2.index:
            #    result_array.append([code, row['percentage'], row['occurrence'], df2.loc[code, 'percentage'], df2.loc[code, 'occurrence']])
        result_df = pd.DataFrame(result_array, columns=column_names)
        threshold = percentage
        self.result_df = result_df.loc[
            (result_df['2018_per'] >= threshold) & (result_df['2019_per'] >= threshold) & (
                    result_df['2020_per'] >= threshold) & (result_df['2021_per'] >= threshold) & (
                    result_df['2022_per'] >= threshold)]
        table = DataTable(self.result_df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()


class CpStatFrame(wx.Frame):
    """
    Class used for creating frames other than the main one
    """

    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent=parent, title='candle pattern statistics', pos=(50, 60), size=(250, 250))
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        toolbar = self.CreateToolBar()
        self.symbol_choice = wx.Choice(toolbar, choices=SYMBOLS)
        self.start_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.end_date_ctrl = wx.adv.DatePickerCtrl(toolbar, wx.ID_ANY, size=(120, -1))
        self.timeframe_ctrl = wx.Choice(toolbar, choices=['M1', 'M5', 'H1', 'H4', 'D1'])
        self.period_ctrl = wx.TextCtrl(toolbar, wx.ID_ANY, size=(50, -1))
        self.period_ctrl.SetValue('5')
        btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='stat')
        self.Bind(wx.EVT_BUTTON, self.stat, btn_ctrl)
        toolbar.AddControl(self.symbol_choice)
        toolbar.AddControl(self.start_date_ctrl)
        toolbar.AddControl(self.end_date_ctrl)
        toolbar.AddControl(self.timeframe_ctrl)
        toolbar.AddControl(self.period_ctrl)
        toolbar.AddControl(btn_ctrl)
        toolbar.Realize()

        # assign the DataFrame to df

        # declare the grid and assign data
        self.grid = wx.grid.Grid(self, -1)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.grid, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        self.Bind(wx.EVT_CLOSE, self.exit)

    def exit(self, event):
        self.Destroy()

    def stat(self, event):
        self.load_data()

    def load_data(self):
        symbol = SYMBOLS[self.symbol_choice.GetCurrentSelection()]
        start_date = self.start_date_ctrl.GetValue()
        end_date = self.end_date_ctrl.GetValue()
        start_date = start_date.Format('%d/%m/%y %H:%M:%S')
        start_date = datetime.datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
        end_date = end_date.Format('%d/%m/%y %H:%M:%S')
        end_date = datetime.datetime.strptime(end_date, '%d/%m/%y %H:%M:%S')
        timeframe = SUPPORTED_TIMEFRAME[self.timeframe_ctrl.GetCurrentSelection()]
        period = int(self.period_ctrl.GetValue())
        # print(timeframe)
        df = self.stat_cp_pattern(symbol, timeframe, start_date, end_date, period)
        # print(len(df))
        table = DataTable(df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

    def stat_cp_pattern(self, symbol, timeframe, start_date, end_date, days):
        datasource = mt_datasource()
        data = datasource.get_df_for_display(symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        indicators.add_price_change(data, days=days)
        # data.dropna(inplace=True)
        sample_size = len(data)
        stat_dat = []
        data['bullish_positive'] = 0
        data['bullish_true_positive'] = 0
        data['bearish_positive'] = 0
        data['bearish_true_positive'] = 0
        data['continuation_positive'] = 0
        data['continuation_true_positive'] = 0
        first_direction = 100
        sum_positive_count, sum_tp = 0, 0
        for i in range(len(cps)):
            cp = 'CDL' + cps[i][0]
            direction = cps[i][1]

            indicators.add_candle_pattern(data, cp, direction=direction)
            if direction == 0:
                positive_count = len(data[np.abs(data[cp]) == 100])
            else:
                positive_count = len(data[data[cp] == direction])
            negative_count = sample_size - positive_count
            if positive_count == 0:
                tp, fp, tn, fn = 0, 0, 0, 0
                precision, npv, accuracy = 0, 0, 0
            elif direction == 0:
                continuation_rows = data.loc[(np.abs(data[cp]) == 100) & (data['change_continue'] >= 0)]
                data['continuation_positive'] = np.where(
                    (np.abs(data[cp]) == 100) | (data['continuation_positive'] == 1), 1, 0)
                data['continuation_true_positive'] = np.where(
                    ((np.abs(data[cp]) == 100) & (data['change_continue'] >= 0)) | (
                            data['continuation_true_positive'] == 1), 1, 0)
                tp = len(continuation_rows)
                fp = positive_count - tp
                precision = tp * 100 // positive_count
                tn = len(data.loc[(data[cp] == 0) & (data['change_continue'] < 0)])
                fn = negative_count - tn
                npv = tn * 100 // negative_count
            elif direction == 100:
                data['bullish_positive'] = np.where(
                    (data[cp] == 100) | (data['bullish_positive'] == 1), 1, 0)
                data['bullish_true_positive'] = np.where(
                    ((data[cp] == 100) & (data['change_continue'] >= 0)) | (
                            data['bullish_true_positive'] == 1), 1, 0)
                bullish_rows = data.loc[(data[cp] == 100) & (data['change_after'] >= 0)]
                tp = len(bullish_rows)
                fp = positive_count - tp
                precision = tp * 100 // positive_count
                tn = len(data.loc[(data[cp] == 0) & (data['change_after'] < 0)])
                fn = negative_count - tn
                npv = tn * 100 // negative_count
            else:
                data['bearish_positive'] = np.where(
                    (data[cp] == -100) | (data['bearish_positive'] == 1), 1, 0)
                data['bearish_true_positive'] = np.where(
                    ((data[cp] == -100) & (data['change_continue'] >= 0)) | (
                            data['bearish_true_positive'] == 1), 1, 0)
                bearish_rows = data.loc[(data[cp] == -100) & (data['change_after'] < 0)]
                tp = len(bearish_rows)
                fp = positive_count - tp
                precision = tp * 100 // positive_count
                tn = len(data.loc[(data[cp] == 0) & (data['change_after'] >= 0)])
                fn = negative_count - tn
                npv = tn * 100 // negative_count

            if first_direction != direction:
                if direction == -100:
                    sum_positive_count = len(data.loc[(data['bullish_positive'] == 1)])
                    sum_tp = len(data.loc[(data['bullish_true_positive'] == 1)])
                    sum_negative_count = sample_size - sum_positive_count
                    sum_tn = len(data.loc[(data['bullish_positive'] == 0) & (data['change_continue'] < 0)])
                    sum_fn = sum_negative_count - sum_tn
                    stat_dat.append(
                        ['sum', 'bullish', sample_size, sum_positive_count, sum_tp, sum_positive_count - sum_tp,
                         str(sum_tp * 100 // sum_positive_count) + '%', sum_negative_count, sum_tn, sum_fn,
                         str(sum_tn * 100 // sum_negative_count) + '%',
                         str((sum_tp + sum_tn) * 100 // sample_size) + '%'])
                else:
                    sum_positive_count = len(data.loc[(data['bearish_positive'] == 1)])
                    sum_tp = len(data.loc[(data['bearish_true_positive'] == 1)])
                    sum_negative_count = sample_size - sum_positive_count
                    sum_tn = len(data.loc[(data['bearish_positive'] == 0) & (data['change_continue'] < 0)])
                    sum_fn = sum_negative_count - sum_tn
                    stat_dat.append(
                        ['sum', 'bearish', sample_size, sum_positive_count, sum_tp, sum_positive_count - sum_tp,
                         str(sum_tp * 100 // sum_positive_count) + '%', sum_negative_count, sum_tn, sum_fn,
                         str(sum_tn * 100 // sum_negative_count) + '%',
                         str((sum_tp + sum_tn) * 100 // sample_size) + '%'])

                first_direction = direction

            precision = str(precision) + '%'
            npv = str(npv) + '%'
            accuracy = str((tp + tn) * 100 // sample_size) + '%'
            stat_dat.append(
                [cp, 'continuation' if direction == 0 else ('bullish' if direction == 100 else 'bearish'),
                 sample_size, positive_count, tp, fp, precision, negative_count, tn, fn, npv, accuracy])

        sum_positive_count = len(data.loc[(data['continuation_positive'] == 1)])
        sum_tp = len(data.loc[(data['continuation_true_positive'] == 1)])
        sum_negative_count = sample_size - sum_positive_count
        sum_tn = len(data.loc[(data['continuation_positive'] == 0) & (data['change_continue'] < 0)])
        sum_fn = sum_negative_count - sum_tn
        stat_dat.append(['sum', 'continuation', sample_size, sum_positive_count, sum_tp, sum_positive_count - sum_tp,
                         str(sum_tp * 100 // sum_positive_count) + '%', sum_negative_count, sum_tn, sum_fn,
                         str(sum_tn * 100 // sum_negative_count) + '%',
                         str((sum_tp + sum_tn) * 100 // sample_size) + '%'])

        return pd.DataFrame(stat_dat, columns=['Name', 'direction', 'sample_size', 'positive_count',
                                               'true p', 'false p', 'precision', 'negative_count', 'true n', 'false n',
                                               'specificity', 'accuracy'])


class GeneticAutomatonFrame(wx.Frame):
    """
    Class used for creating frames other than the main one
    """

    def __init__(self, plot, parent=None):
        self.plot = plot
        wx.Frame.__init__(self, parent=parent, title='Genetic Automaton', pos=(50, 60), size=(250, 250))
        self._init_gui()
        self.Layout()
        self.Show()

    def _init_gui(self):
        toolbar = self.CreateToolBar()
        btn_ctrl = wx.Button(toolbar, wx.ID_ANY, label='stat')
        self.Bind(wx.EVT_BUTTON, self.stat, btn_ctrl)
        toolbar.AddControl(btn_ctrl)
        toolbar.Realize()

        # assign the DataFrame to df

        # declare the grid and assign data
        self.grid = wx.grid.Grid(self, -1)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.grid, 0, wx.EXPAND)

        mainSizer.Add(sizer, 0, wx.ALL, 5)

        sizer.SetSizeHints(self)
        self.SetSizerAndFit(mainSizer)

        self.Bind(wx.EVT_CLOSE, self.exit)

        df = pd.DataFrame(self.plot.code_set, columns=['code'])
        table = DataTable(df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

    def exit(self, event):
        self.Destroy()

    def stat(self, event):
        with open('file.txt', 'w', encoding='utf-8') as f:
            for code in self.plot.code_set:
                f.write(code + '\n')
        with open('file1.txt', 'w', encoding='utf-8') as f:
            for code in self.plot.counter_set:
                f.write(code + '\n')


class DataTable(wx.grid.GridTableBase):
    def __init__(self, data=None):
        wx.grid.GridTableBase.__init__(self)
        self.headerRows = 1
        if data is None:
            data = pd.DataFrame()
        self.data = data

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.data.columns) + 1

    def GetValue(self, row, col):
        if col == 0:
            return self.data.index[row]
        return self.data.iloc[row, col - 1]

    def SetValue(self, row, col, value):
        self.data.iloc[row, col - 1] = value

    def GetColLabelValue(self, col):
        if col == 0:
            if self.data.index.name is None:
                return 'Index'
            else:
                return self.data.index.name
        return str(self.data.columns[col - 1])

    def GetTypeName(self, row, col):
        return wx.grid.GRID_VALUE_STRING

    def GetAttr(self, row, col, prop):
        attr = wx.grid.GridCellAttr()
        if self.data.iloc[row, 0] == 'sum':
            attr.SetBackgroundColour('#CCE6FF')
        return attr


class PlotNotebook(wx.Panel):
    def __init__(self, parent, id=-1):
        super().__init__(parent, id=id)
        self.symbol_df = None
        self.nb = aui.AuiNotebook(self)
        self.grid = wx.grid.Grid(self, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.grid, 1, 0, 0)
        sizer.Add(self.nb, 5, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.plots = {}
        self.symbols = []
        self.init_grid()
        self.current_plot = None

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_symbol_selected, self.grid)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed, self.nb)

    def init_grid(self):
        self.symbol_df = pd.DataFrame(np.array(SYMBOLS).reshape((len(SYMBOLS), 1)), columns=['name'])
        table = DataTable(self.symbol_df)
        self.grid.SetTable(table, takeOwnership=True)
        self.grid.AutoSizeColumns()
        self.Layout()

    def add(self, symbol='XAUUSD'):
        if symbol in self.plots.keys():
            plot = self.plots.get(symbol)
            self.current_plot = plot
            return plot
        else:
            plot = Plot(self.nb, symbol=symbol)
            self.plots[symbol] = plot
            self.symbols.append(symbol)
            self.nb.AddPage(plot, symbol)
            return plot

    def on_symbol_selected(self, e):
        symbol = self.symbol_df.iloc[e.GetRow(), 0]
        self.current_plot = self.add(symbol)

    def on_page_changed(self, e):
        print(self.nb.GetSelection())
        self.current_plot = self.plots[self.symbols[self.nb.GetSelection()]]


def demo():
    # Alternatively you could use:
    # app = wx.App()
    # InspectableApp is a great debug tool, see:
    # http://wiki.wxpython.org/Widget%20Inspection%20Tool
    datasource = mt_datasource()
    for s in datasource.get_symbols():
        SYMBOLS.append(s.name)
    datasource.shutdown()
    app = wit.InspectableApp()
    frame = MainFrame(None, -1, 'Trading Assistant')
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    demo()
