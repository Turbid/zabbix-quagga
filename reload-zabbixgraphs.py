#!/usr/bin/python2.7

import sys
import re
from zabbix_api import ZabbixAPI, ZabbixAPIException

zbx_server = "http://zabbix/"
zbx_username = "Admin"
zbx_password = "qwerty"
zebra_conf = "/etc/quagga/zebra.conf"
host_name="Router"

oids = {
    "IN": ".1.3.6.1.2.1.31.1.1.1.6",  # ifHCInOctets
    "OUT": ".1.3.6.1.2.1.31.1.1.1.10" # ifHCOutOctets
    }

def err_msg(msg):
    sys.stderr.write("Fail: " + str(msg) + "\n")
    sys.exit(-1)

def read_zebra_conf(zebra_conf):
    try:
        f = open(zebra_conf, 'r')
    except IOError, e:
        err_msg(e)
    else:
        ifaces = {}
        for line in f:
            iface_m = re.search('^interface\svlan(\d+)', line)
            if iface_m:
                desc_m = re.search('^\s*description\s+(.*)', f.next())
                if desc_m:
                    vlan = iface_m.group(1)
                    desc = desc_m.group(1)
                    ifaces[vlan] = desc
        return ifaces
        f.close()

def add_item(host_id, vlan, oid_id):
    try:
        item_id = zapi.item.create({
            "hostid": host_id,
            "description": vlan + "-" + oid_id,
            "type": 4,
            "snmp_oid": oids[oid_id] + "." + vlan,
            "snmp_community": "zabbix",
            "snmp_port": "161",
            "key_": vlan + "." + oid_id,
            "value_type": 3,
            "data_type": 0,
            "units": "bit/s",
            "multiplier": 1,
            "formula": 8,
            "delay": 60,
            "history": 90,
            "trends": 365,
            "status": 0,
            "delta": 1
            })['itemids'][0]
        return item_id
    except ZabbixAPIException, e:
        err_msg(e)

def add_graph(graph_name, in_item_id, out_item_id):
    try:
        zapi.graph.create({
            "name": graph_name,
            "width": 900,
            "height": 200,
            "graphtype": 0,
            "gitems": [
               {"itemid": in_item_id,
                "drawtype": 5,
                "sortorder": 1,
                "color": "009900",
                "yaxisside": 1,
                "calc_fnc": 2,
                "type": 0,
                "periods_cnt": 5},
               {"itemid": out_item_id,
                "drawtype": 5,
                "sortorder": 2,
                "color": "000099",
                "yaxisside": 1,
                "calc_fnc": 2,
                "type": 0,
                "periods_cnt": 5}
            ]
        })
    except ZabbixAPIException, e:
        err_msg(e)

if  __name__ == "__main__":

    ifaces = read_zebra_conf(zebra_conf)

    zapi = ZabbixAPI(server = zbx_server, log_level = 0)

    try:
        zapi.login(zbx_username, zbx_password)
    except ZabbixAPIException, e:
        err_msg(e)

    host_id = zapi.host.get({"filter": {"host": host_name}})[0]["hostid"]
    if host_id == []:
        err_msg("Host '" + host_name + "' not found")

    # get exists graphs
    graphs_ex_ids = {}
    graphs_ex_names = {}
    for graph in zapi.graph.get({"filter": {"host": host_name}, "output": "extend"}):
        vlan = re.search('.*\[(\d+)\]', graph["name"]).group(1)
        name = re.search('(.*)\s\[\d+\]', graph["name"]).group(1)
        graphs_ex_ids[vlan] = graph["graphid"] 
        graphs_ex_names[vlan] = name

    for vlan in ifaces:
        graph_name = ifaces[vlan] + " [" + vlan + "]"
        graph_name = graph_name.decode('utf-8')

        if (vlan in graphs_ex_names):
            if not (graph_name == graphs_ex_names[vlan] + " [" + vlan + "]"):
                zapi.graph.update({"graphid": graphs_ex_ids[vlan], "name": graph_name})
        else:
            in_item_id = add_item(host_id, vlan, 'IN')
            out_item_id = add_item(host_id, vlan, 'OUT')
            add_graph(graph_name, in_item_id, out_item_id)
