import copy
import time
# import currency
# import PlayerInfoAPI
import pandas as pd
import math
import scipy.special as sc
import os

config_path = 'shop'

total_bought_count_multiplied = 0
total_sold_count_multiplied = 0

list_buy = []
list_sell = []

buy_df = pd.DataFrame()
sell_df = pd.DataFrame()


class Goods_to_buy(object):
    def __init__(self, row=None):
        if not (row is None):
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
            self.bought_price_multiplier = row.bought_price_multiplier
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
        self.bought_price_multiplier = 0.998


def calc_buy_price(current_time, item: Goods_to_buy, total_bought):
    reduced_max_price = math.exp(-item.max_price_reduce_rate * item.bought_count / item.bought_multiplier) * (
            item.max_price - item.protected_max_price) + item.protected_max_price
    reduced_bought_max_price = (1 - item.bought_count / item.bought_multiplier / (
            1 + total_bought)) * reduced_max_price
    a = item.half_time_recover / item.time_scale + 1
    last_price_decreased = (item.last_price - item.lowest_price) * item.bought_price_multiplier + item.lowest_price
    pb = (last_price_decreased - item.lowest_price) / (reduced_bought_max_price - item.lowest_price)
    if (pb >= 1):
        pb = 1 - 1e-8
    tb = sc.gammaincinv(a, pb)
    delta_time = current_time - item.last_bought_time
    delta_time_normalized = delta_time / item.time_scale
    current_price = sc.gammainc(a, tb + delta_time_normalized) * (
            reduced_bought_max_price - item.lowest_price) + item.lowest_price
    # debug use
    # print(item.bought_count, ' ', total_bought, ' ', reduced_bought_max_price, ' ', item.last_price, ' ', pb, ' ', tb,
    #      ' ', delta_time_normalized, ' ', current_price)
    return current_price


def calc_buy_multi_price(current_time, item: Goods_to_buy, amount):
    virtual_item = copy.deepcopy(item)
    virtual_total_bought = total_bought_count_multiplied
    totalmoney = 0
    lastmoney = 0
    for i in range(amount):
        curr_price = calc_buy_price(current_time, virtual_item,
                                    total_bought=virtual_total_bought + i / item.bought_multiplier)
        totalmoney += curr_price
        lastmoney = curr_price
        virtual_item.last_bought_time = current_time
        virtual_item.last_price = curr_price
        virtual_item.bought_count += 1
        virtual_total_bought += 1
    return totalmoney, lastmoney


class Goods_to_sell(object):
    def __init__(self, row=None):
        if not (row is None):
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


def calc_sell_price(current_time, item: Goods_to_sell, total_sold):
    current_base_price = item.base_price * (item.base_price_increase_rate ** (item.sold_count / item.sold_multiplier))
    current_sold_base_price = current_base_price * (
            1 + item.sold_count / item.sold_multiplier / (total_sold + 1))  # add one in case of zero
    a = item.half_time_recover / item.time_scale + 1
    delta_time = current_time - item.last_sold_time
    delta_time_normalized = delta_time / item.time_scale
    depriced_percentage = sc.gammaincc(a, delta_time_normalized)
    before_decrease_price = item.last_sold_price * item.sold_price_multiplier
    if (before_decrease_price < current_sold_base_price):
        return current_sold_base_price
    current_price = (before_decrease_price - current_sold_base_price) * depriced_percentage + current_sold_base_price
    return current_price


def calc_sell_multi_price(current_time, item: Goods_to_sell, amount):
    virtual_item = copy.deepcopy(item)
    virtual_total_sold = total_sold_count_multiplied
    totalmoney = 0
    lastmoney = 0
    for i in range(amount):
        curr_price = calc_sell_price(current_time, virtual_item,
                                     total_sold=virtual_total_sold + i / item.sold_multiplier)
        totalmoney += curr_price
        virtual_item.last_sold_price = curr_price
        virtual_item.last_sold_time = current_time
        virtual_item.sold_count += 1
        virtual_total_sold += 1
        lastmoney = curr_price
    return totalmoney, lastmoney


def load_config():
    global buy_df
    global sell_df
    global list_buy
    global list_sell
    global total_bought_count_multiplied
    global total_sold_count_multiplied
    if not os.path.exists(config_path):
        os.mkdir('shop')
        f = open(os.path.join(config_path, 'price_buy.csv'), 'w')
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

        f = open(os.path.join(config_path, 'price_sell.csv'), 'w')
        f.write('item_name,money_type,'
                'base_price_increase_rate,base_price,sold_count,sold_multiplier,'
                'half_time_recover,time_scale,'
                'last_sold_time,last_sold_price,sold_price_multiplier')
        f.write('\n')
        f.close()

        print('blank config files generated.')
        return
    else:
        buy_df = pd.read_csv(os.path.join(config_path, 'price_buy.csv'))
        sell_df = pd.read_csv(os.path.join(config_path, 'price_sell.csv'))
        list_buy = [Goods_to_buy(row) for index, row in buy_df.iterrows()]
        list_sell = [Goods_to_sell(row) for index, row in sell_df.iterrows()]
        total_bought_count_multiplied = 0.0
        for item in list_buy:
            # ('before ', total_bought_count_multiplied, ' ', item.bought_count, ' ', item.bought_multiplier)
            total_bought_count_multiplied += item.bought_count / item.bought_multiplier
            # print('after ', total_bought_count_multiplied)
        total_sold_count_multiplied = 0.0
        for item in list_sell:
            total_sold_count_multiplied += item.sold_count / item.sold_multiplier
        print(len(list_buy), ' buy config(s) loaded, ', len(list_sell), ' sell config(s) loaded.')


def get_sell_item(item_name, coin_type) -> Goods_to_sell:
    for i in list_sell:
        if (i.item_name == item_name) and (i.money_type == coin_type):
            return i


def get_buy_item(item_name, coin_type) -> Goods_to_buy:
    for i in list_buy:
        if (i.item_name == item_name) and (i.money_type == coin_type):
            return i


def on_info(server, info):
    global total_sold_count_multiplied
    global total_bought_count_multiplied
    if info.is_player:
        if info.content.startswith("!!buy "):
            args = info.content.split(" ")
            if (len(args) != 3):
                server.tell(info.player, '!!buy <item> <cointype>')
                return
            itemname = args[1]
            cointype = args[2]
            # !!buy item, means player buy item, equals to server sell item
            item_val = get_sell_item(itemname, cointype)
            if (not item_val):
                server.tell(info.player, itemname + ' bought with ' + cointype + ' does not exist in buyable list')
                return
            server_sell_price = calc_sell_price(current_time=time.time(), item=item_val,
                                                total_sold=total_sold_count_multiplied)
            server_sell_price_10, _ = calc_sell_multi_price(current_time=time.time(), item=item_val, amount=10)
            server_sell_price_64, _ = calc_sell_multi_price(current_time=time.time(), item=item_val, amount=64)
            server.tell(info.player, itemname + ' : ' + str(server_sell_price) + ' for one, ' + str(
                server_sell_price_10) + ' for tens, ' + str(server_sell_price_64) + ' for 64 items')
            server.tell(info.player, 'Enter !!buyconfirm ' + itemname + ' ' + cointype + ' ' + ' <amount> to buy.')
        if (info.content.startswith("!!sell ")):
            args = info.content.split(" ")
            if (len(args) != 3):
                server.tell(info.player, '!!sell <item> <cointype>')
                return
            itemname = args[1]
            cointype = args[2]
            # !!sell item, means player sell item, equals to server buy item
            item_val = get_buy_item(itemname, cointype)
            if (not item_val):
                server.tell(info.player, itemname + ' sold with ' + cointype + ' does not exist in sellable list')
                return
            server_buy_price = calc_buy_price(current_time=time.time(), item=item_val,
                                              total_bought=total_bought_count_multiplied)
            server_buy_price_10, _ = calc_buy_multi_price(current_time=time.time(), item=item_val, amount=10)
            server_buy_price_64, _ = calc_buy_multi_price(current_time=time.time(), item=item_val, amount=64)
            server.tell(info.player, itemname + ' : ' + str(server_buy_price) + ' for one, ' + str(
                server_buy_price_10) + ' for tens, ' + str(server_buy_price_64) + ' for 64 items')
            server.tell(info.player, 'Enter !!sellconfirm ' + itemname + ' ' + cointype + ' ' + ' <amount> to sell.')
        if (info.content.startswith("!!buyconfirm ")):
            args = info.content.split(" ")
            if (len(args) != 4):
                server.tell(info.player, 'use !!buy <item> <cointype> first')
                return
            itemname = args[1]
            cointype = args[2]
            amount = int(args[3])
            item_val = get_sell_item(itemname, cointype)
            if (not item_val):
                server.tell(info.player, itemname + ' bought with ' + cointype + ' does not exist in buyable list')
                return
            server_sell_price_n, last_item_price = calc_sell_multi_price(current_time=time.time(), item=item_val,
                                                                         amount=amount)
            server_sell_price_n_int = math.ceil(server_sell_price_n)
            # check if the player have enough money
            currency = server.get_plugin_instance('currency')
            player_money = currency.getmoney_svr(server, info.player, cointype)
            if (player_money < server_sell_price_n_int):
                server.tell(info.player, 'Buy ' + str(amount) + ' ' + itemname + ' require ' + str(
                    server_sell_price_n_int) + ' ' + cointype)
                server.tell(info.player, 'You have ' + str(player_money) + ' ' + cointype + ' yet.')
                return
            currency.submoney(server, info.player, cointype, server_sell_price_n_int)
            server.execute('give ' + info.player + ' ' + itemname + ' ' + str(amount))
            item_val.last_sold_price = last_item_price
            item_val.sold_count += amount
            item_val.last_sold_time = time.time()
            total_sold_count_multiplied += amount / item_val.sold_multiplier
            # sell_df.loc[(sell_df['item_name'] == item_val.item_name) and (sell_df['money_type'] == item_val.money_type), "sold_count"] = item_val.sold_count
            df_i = -1
            for i in range(sell_df.shape[0]):
                lineval = sell_df.iloc[i]
                if ((lineval['item_name'] == item_val.item_name) and (lineval['money_type'] == item_val.money_type)):
                    df_i = i
                    break
            sell_df.loc[df_i, 'sold_count'] = item_val.sold_count
            sell_df.loc[df_i, 'last_sold_time'] = item_val.last_sold_time
            sell_df.loc[df_i, 'last_sold_price'] = last_item_price
            sell_df.to_csv(os.path.join(config_path, 'price_sell.csv'), index=False)

        if (info.content.startswith("!!sellconfirm ")):
            args = info.content.split(" ")
            if (len(args) != 4):
                server.tell(info.player, 'use !!sell <item> <cointype> first')
                return
            itemname = args[1]
            cointype = args[2]
            amount = int(args[3])
            item_val = get_buy_item(itemname, cointype)
            if (not item_val):
                server.tell(info.player, itemname + ' sold with ' + cointype + ' does not exist in sellable list')
                return
            server_buy_price_n, last_item_price = calc_buy_multi_price(current_time=time.time(), item=item_val,
                                                                       amount=amount)
            server_buy_price_n_int = math.floor(server_buy_price_n)
            # check if the player have enough items
            # player_backpack_raw=server.rcon_query('data get entity ' + info.player + ' Inventory')
            PlayerInfoAPI = server.get_plugin_instance('PlayerInfoAPI')
            playerinv = PlayerInfoAPI.getPlayerInfo(server, info.player, path='Inventory')
            total_amount = 0
            for invitem in playerinv:
                if (invitem['id'] == itemname) or (invitem['id'] == 'minecraft:' + itemname):
                    total_amount += int(invitem['Count'])
            if (total_amount < amount):
                server.tell(info.player, 'You have ' + str(total_amount) + ' ' + itemname + ' only.')
                return
            currency = server.get_plugin_instance('currency')
            currency.addmoney(server, info.player, cointype, server_buy_price_n_int)
            server.execute('clear ' + info.player + ' ' + itemname + ' ' + str(amount))
            item_val.last_price = last_item_price
            item_val.bought_count += amount
            item_val.last_bought_time = time.time()
            total_bought_count_multiplied += amount / item_val.bought_multiplier
            # buy_df.loc[(buy_df['item_name'] == item_val.item_name) and (buy_df['money_type'] == item_val.money_type), "bought_count"] = item_val.bought_count
            df_i = -1
            for i in range(buy_df.shape[0]):
                lineval = buy_df.iloc[i]
                if ((lineval['item_name'] == item_val.item_name) and (lineval['money_type'] == item_val.money_type)):
                    df_i = i
                    break
            buy_df.loc[df_i, 'bought_count'] = item_val.bought_count
            buy_df.loc[df_i, 'last_bought_time'] = item_val.last_bought_time
            buy_df.loc[df_i, 'last_price'] = last_item_price
            buy_df.to_csv(os.path.join(config_path, 'price_buy.csv'), index=False)
        if (info.content.startswith("!!reloadconfig")):
            if server.get_permission_level(info) < 3:
                server.tell(info.player, 'You don''t have permission to do that!')
                return
            load_config()
        if (info.content.startswith("!!buylist")):
            args = info.content.split(" ")
            if (len(args) > 2):
                server.tell(info.player, 'use !!buylist [pagenum]')
                return
            item_per_page = 10
            pagenum = 1
            if (len(args) == 2):
                pagenum = int(args[1])
            sell_len = sell_df.shape[0]
            for i in range((pagenum - 1) * item_per_page, pagenum * item_per_page):
                if (i >= sell_len):
                    break
                item_val = list_sell[i]
                server.tell(info.player, item_val.item_name + ' ' + item_val.money_type + ' ' + str(
                    calc_sell_price(time.time(), item_val, total_sold=total_sold_count_multiplied)))
        if (info.content.startswith("!!selllist")):
            args = info.content.split(" ")
            if (len(args) > 2):
                server.tell(info.player, 'use !!selllist [pagenum]')
                return
            item_per_page = 10
            pagenum = 1
            if (len(args) == 2):
                pagenum = int(args[1])
            buy_len = buy_df.shape[0]
            for i in range((pagenum - 1) * item_per_page, pagenum * item_per_page):
                if (i >= buy_len):
                    break
                item_val = list_buy[i]
                server.tell(info.player, item_val.item_name + ' ' + item_val.money_type + ' ' + str(
                    calc_buy_price(time.time(), item_val, total_bought=total_bought_count_multiplied)))


def on_load(server, old):
    load_config()
    server.add_help_message('!!buylist [pagenum]', 'see buyable list')
    server.add_help_message('!!selllist [pagenum]', 'see sellable list')
    server.add_help_message('!!sell <item> <cointype>', 'sell item')
    server.add_help_message('!!buy <item> <cointype>', 'buy item')
