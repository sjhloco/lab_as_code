from typing import Any, Dict, Union
import tabulate
import click

from virl2_client import ClientLibrary
from virl2_client.models.lab import Lab
from virl2_client.models.node import Node
from virl2_client.exceptions import APIError


# ----------------------------------------------------------------------------
# 1. CONN: Create EVE-NG or CML connection
# ----------------------------------------------------------------------------
def create_conn(host: str, username: str, password: str) -> ClientLibrary:
    client = ClientLibrary("https://" + host, username, password, ssl_verify=False)
    return client


# ----------------------------------------------------------------------------
# 2. LAB: Create the lab, returned lab object used to create nodes
# ----------------------------------------------------------------------------
def create_lab(client: ClientLibrary, topo: dict[Any, Any]) -> Lab:
    lab = client.create_lab(topo["name"], topo.get("description", ""))
    topo["lab_id"] = lab.id
    return lab


# ----------------------------------------------------------------------------
# 3b. NODE: Create a node (device) and adds the interfaces, returned node object
# ----------------------------------------------------------------------------
def create_node(
    nd_name: str, nd: Dict[str, Any], x: int, y: int, lab: Lab, client: ClientLibrary
) -> Node:
    # NODE: Create the node (if dont specify interfaces use True to populate default number)
    # Needed as EC sporadically fails creating links if populate interface is False
    if nd["type"] == "external_connector":
        tmp_nd = lab.create_node(nd_name, nd["type"], x, y)
    elif nd.get("ethernet") == None:
        tmp_nd = lab.create_node(nd_name, nd["type"], x, y, None, True)
    # Creates node with no interfaces and then adds custom number of interfaces
    elif nd.get("ethernet") != None:
        tmp_nd = lab.create_node(nd_name, nd["type"], x, y)
        for intf in range(nd["ethernet"]):
            tmp_nd.create_interface()
    if nd.get("image") != None:
        tmp_nd.update({"image_definition": nd["image"]}, True)

    return tmp_nd


# ----------------------------------------------------------------------------
# 3c. CONFIG: Generates and applies the startup config
# ----------------------------------------------------------------------------
def apply_config(tmp_nd: Node, cfg: str, lab: Lab, client: ClientLibrary) -> None:
    tmp_nd.configuration = cfg


# ----------------------------------------------------------------------------
# 4. NETWORK_OBJ: Create the network object (external connectors or unmanaged switch)
# ----------------------------------------------------------------------------
def create_net(
    net_name: str, net: Dict[str, Any], x: int, y: int, lab: Lab, client: ClientLibrary
) -> Node:
    xtra_net = None
    # EC: Needs config (for bridge or vrbr), node_definition and possibly xtra switch
    if net["type"].split("_")[0].lower() == "ec":
        net["config"] = net["type"].split("_")[1]
        # XTRA_SWI: Create xtra SWI if more than 1 interface or 2 or more defined links
        if net.get("ethernet", 1) != 1 or len(net.get("links", [])) >= 2:
            net["type"] = "unmanaged_switch"
            xtra_net = create_node(net_name + "_SWI", net, x, y, lab, client)
            del net["ethernet"]
            # Add EC to links as the SWI (not EC) will hold the links dict
            net.get("links", []).append(net_name)
        net["type"] = "external_connector"
    # NETWORK_OBJ: Create the network object and apply config (empty if not EC)
    tmp_net = create_node(net_name, net, x, y, lab, client)
    tmp_net.configuration = net.get("config", "")

    return tmp_net, xtra_net


# ----------------------------------------------------------------------------
# 5a. MGMT_LINKs: Create mgmt links between MGMT-SWI and the specified devices interfaces
# ----------------------------------------------------------------------------
def create_mgmt_link(
    topo_nodes: dict,
    nodes: dict[str, Node],
    node_a: str,
    nodes_b: list[str],
    lab: Lab,
    client: ClientLibrary,
) -> None:
    for node_b in nodes_b:
        if node_b != True:
            # Get interface object for the next available interface on the mgmt switch
            node_a_intf = nodes[node_a].next_available_interface()
            # Get interface object for the devices specified management interface name from the topo inventory
            try:
                mgmt_intf = list(topo_nodes[node_b]["config"]["vars"]["mgmt"].keys())[0]
                node_b_intf = nodes[node_b].get_interface_by_label(mgmt_intf)
            # Catchall incase cant get mgmt interface, such as external_connectors
            except:
                if nodes[node_b].next_available_interface() == None:
                    nodes[node_b].create_interface()
                node_b_intf = nodes[node_b].next_available_interface()
            # Create the link
            lab.create_link(node_a_intf, node_b_intf)
            click.echo(
                f"- {node_a}:{str(node_a_intf).split()[1]} --> {node_b}:{str(node_b_intf).split()[1]}"
            )


# ----------------------------------------------------------------------------
# 5b. DVC_LINKs: Create non-mgmt links between devices using the next available interface on all devices
# ----------------------------------------------------------------------------
def create_dvc_link(
    idx: int,
    topo: dict[Any, Any],
    nodes: dict[str, Node],
    node_a: str,
    nodes_b: list[str],
    lab: Lab,
    client: ClientLibrary,
) -> int:
    for node_b in nodes_b:
        idx += 1
        link = lab.connect_two_nodes(nodes[node_a], nodes[node_b])
        intf_a = link.interface_a.label
        intf_b = link.interface_b.label
        node_a_descr = f"L{idx} >> {node_b}:{intf_b}"
        node_b_descr = f"L{idx} >> {node_a}:{intf_a}"
        try:
            topo["nodes"][node_a]["config"]["vars"]["intf_links"][intf_a] = node_a_descr
        except KeyError:
            topo["networks"][node_a]["intf_links"][intf_a] = node_a_descr
        try:
            topo["nodes"][node_b]["config"]["vars"]["intf_links"][intf_b] = node_b_descr
        except KeyError:
            topo["networks"][node_b]["intf_links"][intf_b] = node_b_descr
        print(f"- {node_a}:{intf_a} --> {node_b}:{intf_b}")
    return idx


# ----------------------------------------------------------------------------
# GET_LAB_OBJ: Used by all post build commands to get lab object
# ----------------------------------------------------------------------------
def get_lab_obj(lab_id: str, client: ClientLibrary) -> Union[Lab, None]:
    if lab_id == None:
        click.secho(
            "lab_id' dictionary does not exist, check got correct input file", fg="red"
        )
        exit()
    else:
        try:
            return client.join_existing_lab(lab_id)
        except Exception as err:
            click.secho(f"{err} - Lab_ID: '{lab_id}'", fg="red")
            exit()


# ----------------------------------------------------------------------------
# LAB_STOP_WIPE: Stops and wipes all devices in lab ready to apply new startup config
# ----------------------------------------------------------------------------
def lab_stop_wipe(lab: Lab, client: ClientLibrary) -> None:
    lab.stop()
    lab.wipe()


# ----------------------------------------------------------------------------
# GET_NODE_OBJ: Stops and wipes all devices in lab ready to apply new startup config
# ----------------------------------------------------------------------------
def get_node_obj(lab: Lab, client: ClientLibrary, nd_name: str) -> Node:
    return lab.get_node_by_label(nd_name)


# ----------------------------------------------------------------------------
# UP: Brings up all devices in the lab
# ----------------------------------------------------------------------------
def lab_up(lab: Lab, client: ClientLibrary) -> None:
    try:
        lab.start()
    # To tidy message get for free-tier due to trying to start too many nodes
    except APIError as e:
        click.secho(f"⚠️ {e}")


# ----------------------------------------------------------------------------
# DOWN: Takes down all devices in the lab
# ----------------------------------------------------------------------------
def lab_down(lab: Lab, client: ClientLibrary) -> None:
    lab.stop()


# ----------------------------------------------------------------------------
# MODES: Lists all nodes in the lab
# ----------------------------------------------------------------------------
def ls_nodes(lab: Lab, client: ClientLibrary) -> None:
    nodes = lab.nodes()
    table = list()
    headers = ["ID", "Label", "Type", "State", "Wiped?", "L3 Address(es)"]
    for node in nodes:
        tr = list()
        tr.append(node.id)
        tr.append(node.label)
        tr.append(node.node_definition)
        color = "red"
        booted = node.is_booted()
        if booted:
            color = "green"
        elif node.is_active():
            color = "yellow"
        node_state = node.state
        tr.append(click.style(node_state, fg=color))
        tr.append(node_state == "DEFINED_ON_CORE")
        intfs = []
        if booted:
            for i in node.interfaces():
                disc_ipv4 = i.discovered_ipv4
                if disc_ipv4:
                    intfs += disc_ipv4
        tr.append("\n".join(intfs))
        table.append(tr)
    try:
        click.echo(tabulate.tabulate(table, headers, tablefmt="fancy_grid"))
    except UnicodeEncodeError:
        click.echo(tabulate.tabulate(table, headers, tablefmt="grid"))
