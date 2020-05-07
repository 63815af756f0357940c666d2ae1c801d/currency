import copy
import currency
import PlayerInfoAPI
import re
import pandas as pd
import math
import scipy.special as sc
import os

total_bought_count_multiplied = 0
total_sold_count_multiplied = 0

list_buy=[]
list_sell=[]


class Goods_to_buy(object):
    def __init__(self, row=None):
        if (row):
            self.item_name = row.item_name
            self.money_type = row.money_type

            self.max_price_reduce_rate = row.max_price_reduce_rate
            self.protected_max_price = row.protected_max_price
            self.bought_count = row.bought_count
            self.bought_multiplier = row.bought_multiplier

            self.half_time_recover = row.half_time_recover
            self.time_scale = row.time_scale

            self.lowest_price = row.lowest_price
            self.max_price = row.max_price

            self.last_price = row.last_price
            self.last_bought_time = row.last_bought_time
            return

        self.item_name = "air"
        self.money_type = "sdvalue"

        self.max_price_reduce_rate = 0.05
        self.protected_max_price = 0.2
        self.bought_count = 0
        self.bought_multiplier = 64

        self.half_time_recover = 1
        self.time_scale = 2

        self.lowest_price = 0.0
        self.max_price = 2.0

        self.last_price = 1.0
        self.last_bought_time = 0.0


def calc_buy_price(current_time, item: Goods_to_buy,total_bought=total_bought_count_multiplied):
    reduced_max_price = math.exp(-item.max_price_reduce_rate * item.bought_count) + item.protected_max_price
    reduced_bought_max_price = (1 - item.bought_count / item.bought_multiplier / (
            1 + total_bought)) * reduced_max_price
    a = item.half_time_recover / item.time_scale + 1
    pb = (reduced_bought_max_price - item.lowest_price) / (item.max_price - item.lowest_price)
    tb = sc.gammaincinv(a, pb)
    delta_time = current_time - item.last_bought_time
    delta_time_normalized = delta_time / item.time_scale
    current_price = sc.gammainc(a, tb + delta_time_normalized)
    return current_price

def calc_buy_multi_price(current_time,item:Goods_to_buy,amount):
    virtual_item=copy.deepcopy(item)
    virtual_total_bought=total_bought_count_multiplied
    totalmoney=0
    for i in range(1,amount):
        curr_price=calc_buy_price(current_time,virtual_item,total_bought=virtual_total_bought)
        totalmoney+=curr_price
        virtual_item.last_bought_time=current_time
        virtual_item.last_price=curr_price
        virtual_item.bought_count+=1
        virtual_total_bought+=1
    return totalmoney

class Goods_to_sell(object):
    def __init__(self, row=None):
        if (row):
            self.item_name = row.item_name
            self.money_type = row.money_type

            self.base_price_increase_rate = row.base_price_increase_rate
            self.base_price = row.base_price
            self.sold_count = row.sold_count
            self.sold_multiplier = row.sold_multiplier

            self.half_time_recover = row.half_time_recover
            self.time_scale = row.time_scale

            self.last_sold_time = row.last_sold_time
            self.last_sold_price = row.last_sold_price
            self.sold_price_multiplier = row.sold_price_multiplier
            return

        self.item_name = "air"
        self.money_type = "sdvalue"

        self.base_price_increase_rate = 1.0001
        self.base_price = 1.0
        self.sold_count = 0
        self.sold_multiplier = 64

        self.half_time_recover = 1
        self.time_scale = 2

        self.last_sold_time = 0
        self.last_sold_price = 1.0
        self.sold_price_multiplier = 1.01


def calc_sell_price(current_time, item: Goods_to_sell,total_sold=total_sold_count_multiplied):
    current_base_price = item.base_price * (item.base_price_increase_rate ** (item.sold_count / item.sold_multiplier))
    current_sold_base_price = current_base_price * (
            1 + item.sold_count / item.sold_multiplier / total_sold)
    a = item.half_time_recover / item.time_scale + 1
    delta_time = current_time - item.last_sold_time
    delta_time_normalized = delta_time / item.time_scale
    depriced_percentage = sc.gammaincc(a, delta_time_normalized)
    before_decrease_price = item.last_sold_price * item.sold_price_multiplier
    if (before_decrease_price < current_sold_base_price):
        return current_sold_base_price
    current_price = (before_decrease_price - current_sold_base_price) * depriced_percentage + current_sold_base_price
    return current_price

def calc_sell_multi_price(current_time,item:Goods_to_sell,amount):
    virtual_item=copy.deepcopy(item)
    virtual_total_sold=total_sold_count_multiplied
    totalmoney=0
    for i in range(1,amount):
        curr_price=calc_sell_price(current_time,virtual_item,total_sold=virtual_total_sold)
        totalmoney+=curr_price
        virtual_item.last_sold_price=curr_price
        virtual_item.last_sold_time=current_time
        virtual_item.sold_count+=1
        virtual_total_sold+=1
    return totalmoney

def load_config(path='shop'):
    global list_buy
    global list_sell
    if not os.path.exists(path):
        os.mkdir('shop')
        f = open(os.path.join(path, 'price_buy.csv'))
        f.write('item_name,money_type,'
                'max_price_reduce_rate,protected_max_price,bought_count,bought_multiplier,'
                'half_time_recover,time_scale,'
                'lowest_price,max_price,'
                'last_price,last_bought_time')
        f.write('\n')
        f.close()
        # Info: lowest_price<=protected_max_price<base_price<max_price
        # Info: half_time_recover>0
        # lowest price and protected base price can be below zero

        f = open(os.path.join(path, 'price_sell.csv'))
        f.write('item_name,money_type,'
                'base_price_increase_rate,base_price,sold_count,sold_multiplier'
                'half_time_recover,time_scale'
                'last_sold_time,last_sold_price,sold_price_multiplier')
        f.write('\n')
        f.close()

        print('blank config files generated.')
        return
    else:
        buy_df = pd.read_csv(os.path.join(path, 'price_buy.csv'))
        sell_df = pd.read_csv(os.path.join(path, 'price_sell.csv'))
        list_buy = [Goods_to_buy(row) for index, row in buy_df.iterrows()]
        list_sell = [Goods_to_sell(row) for index, row in sell_df.iterrows()]

def on_info(server, info):
    if info.is_player:
        if info.content.startswith("!!buy "):
            args = info.content.split(" ")
            if (len(args) != 3):
                server.tell(info.player, '!!buy <item> <cointype>')
                return
            itemname = args[1]
            cointype = args[2]
            # !!buy item, means player buy item, equals to server sell item

            # TODO


def on_load(server, old):
    load_config()
    server.add_help_message('!!buy <item> <cointype>', 'buy item')
    server.add_help_message('!!sell <item> <cointype>', 'sell item')
