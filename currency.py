import re
import copy


def getmoney(server, info, playername, moneytype):
    resultstr = server.rcon_query('scoreboard players get ' + playername + ' ' + moneytype)
    if (re.fullmatch(r'\w+ has \d* .*', resultstr)):
        vals = resultstr.split(' ')
        return int(vals[2])
    else:
        server.tell(info.player, 'Warning: ' + playername + ' haven''t had any ' + moneytype)
        return 0


def getmoney_pr(server, playername, moneytype):
    return server.rcon_query('scoreboard players get ' + playername + ' ' + moneytype)


def setmoney(server, playername, moneytype, val):
    server.execute('scoreboard players set ' + playername + ' ' + moneytype + ' ' + str(val))


def addmoney(server, playername, moneytype, val):
    server.execute('scoreboard players add ' + playername + ' ' + moneytype + ' ' + str(val))


def submoney(server, playername, moneytype, val):
    server.execute('scoreboard players remove ' + playername + ' ' + moneytype + ' ' + str(val))


def onServerInfo(server, info):
    info2 = copy.deepcopy(info)
    info2.isPlayer = info2.is_player
    on_info(server, info2)


def on_info(server, info):
    if info.is_player:
        if info.content.startswith("!!give "):
            if server.get_permission_level(info) < 3:
                server.tell(info.player, 'You don''t have permission to do that!')
                return
            args = info.content.split(" ")
            if (len(args) != 4):
                server.tell(info.player, '!!give <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            addmoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!take "):
            if server.get_permission_level(info) < 3:
                server.tell(info.player, 'You don''t have permission to do that!')
                return
            args = info.content.split(" ")
            if (len(args) != 4):
                server.tell(info.player, '!!take <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            submoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!set "):
            if server.get_permission_level(info) < 3:
                server.tell(info.player, 'You don''t have permission to do that!')
                return
            args = info.content.split(" ")
            if (len(args) != 4):
                server.tell(info.player, '!!set <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            setmoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!get "):
            args = info.content.split(" ")
            if (len(args) != 3):
                server.tell(info.player, '!!get <player> <type>')
                return
            playername = args[1]
            cointype = args[2]
            server.tell(info.player, str(getmoney(server, info, playername, cointype)))
    else:
        if info.content.startswith("!!give "):
            args = info.content.split(" ")
            if (len(args) != 4):
                print('!!give <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            addmoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!take "):
            args = info.content.split(" ")
            if (len(args) != 4):
                print('!!take <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            submoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!set "):
            args = info.content.split(" ")
            if (len(args) != 4):
                print('!!set <player> <type> amount')
                return
            playername = args[1]
            cointype = args[2]
            coinamount = args[3]
            setmoney(server, playername, cointype, coinamount)
        if info.content.startswith("!!get "):
            args = info.content.split(" ")
            if (len(args) != 3):
                print('!!get <player> <type>')
                return
            playername = args[1]
            cointype = args[2]
            print(str(getmoney_pr(server, playername, cointype)))


def on_load(server, old):
    server.add_help_message('!!give', 'Give money to someone')
    server.add_help_message('!!take', 'Take money from someone')
    server.add_help_message('!!set', 'Set money for someone')
    server.add_help_message('!!get', 'Get money of someone')
