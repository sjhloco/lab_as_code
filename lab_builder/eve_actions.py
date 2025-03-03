from typing import Any, Dict, Union
import os
import click
from evengsdk.client import EvengClient
from evengsdk.exceptions import EvengHTTPError, EvengApiError
from evengsdk.cli.console import cli_print_error, cli_print_output, console


# ----------------------------------------------------------------------------
# 1. CONN: Create EVE-NG or CML connection
# ----------------------------------------------------------------------------
def create_conn(host: str, username: str, password: str) -> EvengClient:
    client = EvengClient(host, ssl_verify=False, protocol="http")
    client.disable_insecure_warnings()  # disable warnings for self-signed certificates (only needed for https)
    client.login(username=username, password=password)
    return client.api


# ----------------------------------------------------------------------------
# 2. LAB: Create the lab, returned lab path used in all future API calls
# ----------------------------------------------------------------------------
def create_lab(client: EvengClient, topo: dict[Any, Any]) -> str:
    lab = {
        "name": topo["name"],
        "description": topo.get("description", ""),
        "path": topo.get("path", "/"),
    }
    try:
        tmp_lab = client.create_lab(**lab)
        # {'code': 200, 'status': 'success', 'message': 'Lab has been created (60019).'}
        lab_path = f"{os.path.join(lab['path'], lab['name'])}.unl"
        topo["lab_id"] = lab_path
        return lab_path
    except EvengHTTPError as e:
        click.secho(f"❌ {e.msg}")
        exit()


# ----------------------------------------------------------------------------
# 3b. NODE: Create a node (device) and adds the interfaces, returned node ID
# ----------------------------------------------------------------------------
def create_node(
    nd_name: str, nd: Dict[str, Any], x: int, y: int, lab: str, client: EvengClient
) -> int:
    # NODE: Create the node
    node = {
        "name": nd_name,
        "template": nd["type"],
        "node_type": nd.get("eve_type", "qemu"),
        "left": y,
        "top": x,
    }
    if nd.get("image") != None:
        node["image"] = nd["image"]
    # Adds default number of interfaces if defined
    if nd.get("ethernet") != None:
        node["ethernet"] = int(nd["ethernet"])
    tmp_nd = client.add_node(lab, **node)
    # {'code': 201, 'status': 'success', 'message': 'Lab has been saved (60023).', 'data': {'id': 1}}
    return tmp_nd["data"]["id"]


# ----------------------------------------------------------------------------
# 3c. CONFIG: Generates and applies the startup config
# ----------------------------------------------------------------------------
def apply_config(tmp_nd: str, cfg: str, lab: str, client: EvengClient) -> None:
    tmp_upload_config = client.upload_node_config(lab, tmp_nd, cfg, True)
    # {'code': 201, 'status': 'success', 'message': 'Lab has been saved (60023).'
    tmp_apply_config = client.enable_node_config(lab, tmp_nd)
    # {'code': 201, 'status': 'success', 'message': 'Lab has been saved (60023).'}


# ----------------------------------------------------------------------------
# 4. NETWORK_OBJ: Create the network object (external connectors or unmanaged switch)
# ----------------------------------------------------------------------------
def create_net(
    net_name: str, net: Dict[str, Any], x: int, y: int, lab: str, client: EvengClient
) -> tuple[str, None]:
    xtra_net = None
    network = {
        "name": net_name,
        "network_type": net["type"],
        "visibility": 1,
        "left": y,
        "top": x,
    }
    tmp_net = client.add_lab_network(lab, **network)
    # {'code': 201, 'status': 'success', 'message': 'Network has been added to the lab (60006).', 'data': {'id': 1}}
    return tmp_net["data"]["id"], xtra_net


# ----------------------------------------------------------------------------
# 5. MGMT_LINKs: Create mgmt links between MGMT-SWI and the specified devices interfaces
# ----------------------------------------------------------------------------
def create_mgmt_link(
    topo_nodes: dict,
    nodes: dict[str, int],
    node_a: str,
    nodes_b: list[str],
    lab: str,
    client: EvengClient,
) -> None:
    for node_b in nodes_b:
        if node_b != True:
            # Get interface object for the devices specified management interface name from the topo inventory
            try:
                intf_b = list(topo_nodes[node_b]["config"]["vars"]["mgmt"].keys())[0]
            # Catchall incase cant get mgmt interface
            except:
                intf_b = next_available_interface(client, lab, nodes[node_b])
            # Create the link
            link = {"src": node_b, "src_label": intf_b, "dst": node_a}
            client.connect_node_to_cloud(lab, **link)
            # {'code': 201, 'status': 'success', 'message': 'Lab has been saved (60023).'}
            click.echo(f"- {node_b}:{intf_b} --> {node_a}")


# ----------------------------------------------------------------------------
# 4b. DVC_LINKs: Create non-mgmt links between devices using the next available interface on all devices
# ----------------------------------------------------------------------------
def create_dvc_link(
    idx: int,
    topo: dict[Any, Any],
    nodes: dict[str, int],
    node_a: str,
    nodes_b: list[str],
    lab: str,
    client: EvengClient,
) -> int:
    for node_b in nodes_b:
        idx += 1
        # Is a network link as not in nodes dict
        if topo["nodes"].get(node_a) == None:
            intf_b = next_available_interface(client, lab, nodes[node_b])
            link = {"src": node_b, "src_label": intf_b, "dst": node_a}
            client.connect_node_to_cloud(lab, **link)
            node_b_descr = f"L{idx} >> {node_a}"
            print(f"- {node_a} --> {node_b}:{intf_b}")
        else:
            intf_a = next_available_interface(client, lab, nodes[node_a])
            intf_b = next_available_interface(client, lab, nodes[node_b])
            link = {
                "src": node_a,
                "src_label": intf_a,
                "dst": node_b,
                "dst_label": intf_b,
            }
            tmp_link = client.connect_node_to_node(lab, **link)
            # Just get back True from API call
            node_b_descr = f"L{idx} >> {node_a}:{intf_a}"
            print(f"- {node_a}:{intf_a} --> {node_b}:{intf_b}")
            # Only need Node A description if is not a network object as the dont have ports
            node_a_descr = f"L{idx} >> {node_b}:{intf_b}"
            try:
                topo["nodes"][node_a]["config"]["vars"]["intf_links"][
                    intf_a
                ] = node_a_descr
            except KeyError:
                topo["networks"][node_a]["intf_links"][intf_a] = node_a_descr
        try:
            topo["nodes"][node_b]["config"]["vars"]["intf_links"][intf_b] = node_b_descr
        except KeyError:
            topo["networks"][node_b]["intf_links"][intf_b] = node_b_descr
    return idx


# ----------------------------------------------------------------------------
# NEXT_INTF: Gets net available interface on the node
# ----------------------------------------------------------------------------
def next_available_interface(client: EvengClient, lab: str, node_id: int) -> str | None:
    interfaces = client.get_node_interfaces(lab, node_id)
    # For IOL as is a dict rather than the normal list
    if type(interfaces["data"].get("ethernet", [])) == dict:
        tmp_interfaces = []
        for intf in interfaces["data"]["ethernet"].values():
            tmp_interfaces.append(intf)
        interfaces["data"]["ethernet"] = tmp_interfaces
    # Get next available interface
    for intf in interfaces["data"].get("ethernet", []):
        if intf["network_id"] == 0:
            return intf["name"]
    return None


# ----------------------------------------------------------------------------
# GET_LAB_OBJ: Used by all post build commands to get lab path
# ----------------------------------------------------------------------------
def get_lab_obj(lab_id: str, client: EvengClient) -> Union[str, None]:
    if lab_id == None:
        click.secho(
            "lab_id' dictionary does not exist, check got correct input file", fg="red"
        )
        exit()
    else:
        return lab_id


# ----------------------------------------------------------------------------
# LAB_STOP_WIPE: Stops and wipes all devices in lab ready to apply new startup config
# ----------------------------------------------------------------------------
def lab_stop_wipe(lab: str, client: EvengClient) -> None:
    client.stop_all_nodes(lab)
    client.wipe_all_nodes(lab)


# ----------------------------------------------------------------------------
# GET_NODE_OBJ: Stops and wipes all devices in lab ready to apply new startup config
# ----------------------------------------------------------------------------
def get_node_obj(lab: str, client: EvengClient, nd_name: str) -> str:
    tmp_nd = client.get_node_by_name(lab, nd_name)
    return tmp_nd["id"]


# ----------------------------------------------------------------------------
# UP: Brings up all devices in the lab
# ----------------------------------------------------------------------------
def lab_up(lab: str, client: EvengClient) -> None:
    try:
        client.start_all_nodes(lab)
    except EvengHTTPError as e:
        # Tried getting lab name from output but ID returned is not right
        click.secho(f"❌ {e.msg}")


# ----------------------------------------------------------------------------
# DOWN: Takes down all devices in the lab
# ----------------------------------------------------------------------------
def lab_down(lab: str, client: EvengClient) -> None:
    client.stop_all_nodes(lab)


# ----------------------------------------------------------------------------
# MODES: Lists all nodes in the lab
# ----------------------------------------------------------------------------
def ls_nodes(lab: str, client: EvengClient) -> None:
    # Copied from eve SDK  (node>>commands>>ls) rather than imported as SDK logs in as part of method
    nd_status_code = {
        0: ("stopped", ":red_circle:"),
        1: ("running", ":green_circle:"),
        2: ("started", ":orange_circle:"),
        3: ("building", ":red_circle:"),
    }
    resp = client.list_nodes(lab)
    try:
        node_data = resp.get("data", {})
        if not node_data:
            cli_print_error("No nodes found. Is this lab empty?")
        node_indexes = resp.get("data", {}).keys()
        nodes_list = [(idx, resp["data"][idx]) for idx in node_indexes]
        node_table = []
        for idx, n in nodes_list:
            node_status = n["status"]
            status = nd_status_code[node_status]
            table_row = {
                "id": idx,
                "name": n["name"],
                "url": n["url"],
                "image": n["image"],
                "template": n["template"],
                "status": f"{status[0]} {status[1]}",
                "console": n["console"],
                "ram": n["ram"],
                "cpu": n.get("cpu"),
            }
            node_table.append(table_row)
        table_header = [
            ("ID", dict(justify="right", style="cyan", no_wrap=True)),
            ("Name", {}),
            ("Url", {}),
            ("Image", {}),
            ("Template", {}),
            ("Status", {}),
            ("Console", {}),
            ("RAM", {}),
            ("CPU", {}),
        ]
        table_data = {"data": node_table}
        #  Easier to import from eve SDK as multiple nested modules and error checking
        cli_print_output(
            "table",
            table_data,
            table_header=table_header,
            table_title=f"Nodes @ {lab}",
        )
    except (EvengHTTPError, EvengApiError) as err:
        console.print_error(err)
