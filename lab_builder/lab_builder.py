"""
Decleratively create a lab by defining the nodes and what devices connect rather the actual port number

1. Create the lab, this will create a new _v1 of the topology with links defined (intf_links)
python cml_lab.py -f "cisco_topo.yml" build

2. Change the name of "intf_links" to "intf", assign IPs to each link (identified by Lx) then run config builder
python cml_lab.py -f "cisco_topo.yml" config
"""

from typing import Any, Dict, TextIO
from types import ModuleType
from collections import defaultdict
import os
import importlib
from ipaddress import IPv4Interface
import click
import yaml
from jinja2 import Environment, FileSystemLoader
from virl2_client import ClientLibrary
from evengsdk.client import EvengClient


# ----------------------------------------------------------------------------
# VARIABLES: Hardcoded default variables, are also environment variables of the same name
# ---------------------------------------------------------------------------
LAB_SERVER = "10.30.10.107"
# LAB_SERVER = "10.30.10.105"
LAB_USERNAME = "admin"
LAB_PASSWORD = "pa$$w0rd"  ### ONLY USE FOR TESTING
LAB_TEMPLATES = "templates"
# The following can only be set here or at runtime, dont have env vars
LAB_TOPO_FILE = "mylab.yml"


# ----------------------------------------------------------------------------
# CLICK_CTX_OPTIONS: Shared context to hold input args (defined options) used by different sub commands
# ----------------------------------------------------------------------------
class AppContext:
    def __init__(self) -> None:
        self.filename: str = ""
        self.templates: str = ""
        self.topo: dict[Any, Any] = {}
        self.client: ClientLibrary | EvengClient = ""
        self.mod: ModuleType = importlib


pass_context = click.make_pass_decorator(AppContext, ensure=True)


# ----------------------------------------------------------------------------
# CLICK_OPT: Variablises the input arguments, loads YAML topology and initialise CML connection
# ----------------------------------------------------------------------------
@click.group()
@click.argument("platform", default="EVE")
@click.option(
    "-f",
    "--filename",
    default=LAB_TOPO_FILE,
    type=click.File(),
    help="file.yaml or path/file.yaml topology defining the lab, defaults to script var (mylab.yml)",
)
@click.option(
    "-t",
    "--templates",
    envvar="LAB_TEMPLATES",
    default=LAB_TEMPLATES,
    type=click.Path(exists=True, writable=True),
    help="Template directory, defaults to env-var -> script var (templates)",
)
@click.option(
    "-h",
    "--host",
    envvar="LAB_SERVER",
    default=LAB_SERVER,
    help="EVE/CML server, defaults to env-var -> script var",
)
@click.option(
    "-u",
    "--username",
    envvar="LAB_USERNAME",
    default=LAB_USERNAME,
    help="EVE/CML username, defaults to env-var -> script var",
)
@click.password_option(
    "-p",
    "--password",
    envvar="LAB_PASSWORD",
    default=LAB_PASSWORD,
    prompt_required=False,
    help="EVE/CML password, defaults to env-var -> script var",
)
@pass_context
def main(
    ctx: AppContext,
    platform: str,
    filename: TextIO,
    templates: str,
    host: str,
    username: str,
    password: str,
) -> None:
    """Build a EVE or CML lab in a semi-declarative fashion based off a YAML topology file"""
    ctx.filename = filename.name
    ctx.templates = templates
    ctx.topo = yaml.load(filename, Loader=yaml.FullLoader)
    # Sets which lab platform modules to import (eve_actions.py or cml_actions.py):
    if platform == "EVE":
        ctx.mod = importlib.import_module("eve_actions")
    elif platform == "CML":
        ctx.mod = importlib.import_module("cml_actions")
    # 1. CONN: Create EVE-NG or CML connection
    ctx.client = ctx.mod.create_conn(host, username, password)


# ----------------------------------------------------------------------------
# BUILD: Builds the lab based on the topology file
# ----------------------------------------------------------------------------
@main.command()
@pass_context
def build(ctx: AppContext) -> None:
    """Builds the lab based on the loaded topology file"""
    # 2. LAB: Create the lab, add lab_id to the topo inventory (for when add startup config with interface IPs)
    lab = ctx.mod.create_lab(ctx.client, ctx.topo)
    click.echo("✅ Creating lab:")
    click.echo(f"- {ctx.topo['name']}")

    # 3. NODE Creates the nodes and adds the node objects to a dict as needed to later create the links
    nodes = {}
    x = -800
    click.echo("✅ Creating devices:")
    for idx, (nd_name, nd) in enumerate(ctx.topo["nodes"].items()):
        # LOCATION: Uses the loop index (even or odd) to step device location (down and/or right)
        x, y = set_location(idx, x, 0)
        # 3a. INTF_LINKS: Add a new dict to all nodes to document links (are created in later step)
        ctx.topo = add_dict(ctx.topo, nd_name, "intf_links")
        # 3b. NODE: Create all the nodes and create dict of the node objects
        tmp_nd = ctx.mod.create_node(nd_name, nd, x, y, lab, ctx.client)
        nodes[nd_name] = tmp_nd
        click.echo(f"- {nd_name}")

        # 3c. CONFIG: Generates and applies the startup config
        if nd["config"].get("template") != None:
            tmpl_file = os.path.join(ctx.templates, nd["config"]["template"])
            cfg = render_cfg(ctx.topo["addr"], tmpl_file, nd["config"].get("vars"))
            ctx.mod.apply_config(tmp_nd, cfg, lab, ctx.client)

    # 4. NETWORK_OBJ: Creates the network (eve cloud & bridge, CML external connectors & unmanaged switches)
    net_links: dict = defaultdict(dict)
    if ctx.topo.get("networks") != None:
        click.echo("✅ Creating network devices:")
        for idx, (net_name, net) in enumerate(ctx.topo["networks"].items()):
            # LOCATION: Uses the loop index (even or odd) to step device location (down and/or right)
            x, y = set_location(idx, x, y)
            # INTF_LINKS: Add a new dict to all nodes to document links (are created in later step)
            ctx.topo["networks"][net_name]["intf_links"] = {}
            # NET_OBJ: Create the network objects
            tmp_net, xtra_net = ctx.mod.create_net(net_name, net, x, y, lab, ctx.client)
            nodes[net_name] = tmp_net
            click.echo(f"- {net_name}")
            # XTRA_NET_OBJ: If extra unmanaged switch created for the EC in CML
            if xtra_net != None:
                nodes[xtra_net.label] = xtra_net
                click.echo(f"- {xtra_net.label}")
                net_name = xtra_net.label
            # LINK: Add links to dedicated dict net_links dictionary (True helps differentiate mgmt links)
            if net.get("links") != None:
                if net.get("management", False) == True:
                    net["links"].append(True)
                net_links[net_name] = net["links"]

    # 5a. LINK: Create the links between devices
    click.echo("✅ Creating links:")
    # MGMT_LINKS: Use the pre-defined interfaces to create mgmt links
    mgmt_links = []
    if "True" in str(net_links):
        for node_a, nodes_b in net_links.items():
            if type(nodes_b) == str:
                nodes_b = [nodes_b]
            if "True" in str(nodes_b):
                ctx.mod.create_mgmt_link(
                    ctx.topo["nodes"], nodes, node_a, nodes_b, lab, ctx.client
                )
                mgmt_links.append(node_a)
    # Remove from mgmt links from dict leaving only device links
    if len(mgmt_links) != 0:
        for node_name in mgmt_links:
            del net_links[node_name]

    # 5b. ALL_LINKs: All other links, so devices and external connectors (network)
    net_links.update(ctx.topo.get("links", {}))
    # breakpoint()
    if len(net_links) != 0:
        idx = 0
        for node_a, nodes_b in net_links.items():
            if type(nodes_b) == str:
                nodes_b = [nodes_b]
            idx = ctx.mod.create_dvc_link(
                idx, ctx.topo, nodes, node_a, nodes_b, lab, ctx.client
            )

    # 6. NEW_TOPO_FILE: Create a new topo that contains the intf_links to show connections (can use to assign IPs)
    new_file = ctx.filename.split(".")[0] + "_v1" + "." + ctx.filename.split(".")[1]
    with open(new_file, "w") as outfile:
        yaml.dump(ctx.topo, outfile, sort_keys=False)


# ----------------------------------------------------------------------------
# CONFIG: Generates startup config and applies to all devices in topo inventory (now interface IPs updated)
# ----------------------------------------------------------------------------
@main.command()
@pass_context
def config(ctx: AppContext) -> None:
    """Regenerate and reapply the startup config to all devices"""
    # Get Lab object, stop and wipe all nodes
    lab = ctx.mod.get_lab_obj(ctx.topo.get("lab_id"), ctx.client)
    ctx.mod.lab_stop_wipe(lab, ctx.client)
    for nd_name, nd in ctx.topo["nodes"].items():
        if nd["config"].get("template") != None:
            # Get Node object, render and then apply config
            tmp_nd = ctx.mod.get_node_obj(lab, ctx.client, nd_name)
            tmpl_file = os.path.join(ctx.templates, nd["config"]["template"])
            # If node is up stop before wiping and applying config
            cfg = render_cfg(ctx.topo["addr"], tmpl_file, nd["config"].get("vars"))
            # CML is node object, EVE is node id
            ctx.mod.apply_config(tmp_nd, cfg, lab, ctx.client)


# ----------------------------------------------------------------------------
# UP: Brings up all devices in the lab
# ----------------------------------------------------------------------------
@main.command()
@pass_context
def up(ctx: AppContext) -> None:
    """Bring UP all devices in the lab"""
    # Get Lab object, start all nodes in lab
    lab = ctx.mod.get_lab_obj(ctx.topo.get("lab_id"), ctx.client)
    ctx.mod.lab_up(lab, ctx.client)


# ----------------------------------------------------------------------------
# DOWN: Takes down all devices in the lab
# ----------------------------------------------------------------------------
@main.command()
@pass_context
def down(ctx: AppContext) -> None:
    """Take DOWN all devices in the lab"""
    # Get Lab object, stop all nodes in lab
    lab = ctx.mod.get_lab_obj(ctx.topo.get("lab_id"), ctx.client)
    ctx.mod.lab_down(lab, ctx.client)


# ----------------------------------------------------------------------------
# MODES: Lists all nodes in the lab
# ----------------------------------------------------------------------------
@main.command()
@pass_context
def ls_nodes(ctx: AppContext) -> None:
    """Table displaying the details and status of all devices in lab"""
    # Get Lab object, stop all nodes in lab
    lab = ctx.mod.get_lab_obj(ctx.topo.get("lab_id"), ctx.client)
    ctx.mod.ls_nodes(lab, ctx.client)


# ----------------------------------------------------------------------------
# 3a. INTF_LINKS: Add extra dict to topo inventory to hold link info, also need config on unman swi to stop errors
# ----------------------------------------------------------------------------
def add_dict(topo: dict[Any, Any], nd_name: str, dict_key: str) -> dict[Any, Any]:
    if topo["nodes"][nd_name].get("config") == None:
        topo["nodes"][nd_name]["config"] = {}
    if topo["nodes"][nd_name]["config"].get("vars") == None:
        topo["nodes"][nd_name]["config"]["vars"] = {}
    topo["nodes"][nd_name]["config"]["vars"][dict_key] = {}
    return topo


# ----------------------------------------------------------------------------
# 3c. CONFIG: Generate the device configuration - unmanaged switch has no template
# ----------------------------------------------------------------------------
def render_cfg(
    addr: dict[str, str], template_file: str, nd_vars: Dict[str, Any]
) -> str:
    # Return empty string if device with no config such as an unmanaged switch or external connector
    startup_cfg = ""
    # MGMT: Create vars for mgmt config (mgmt_intf, mgmt_addr, mgmt_gw)
    nd_vars["mgmt_gw"] = addr["mgmt_gw"]
    ip, prefix = addr["mgmt_prefix"].split("/")
    octets = ip.split(".")
    for mgmt_intf, mgmt_addr in nd_vars["mgmt"].items():
        nd_vars["mgmt_intf"] = mgmt_intf
        octets[3] = str(mgmt_addr)
        nd_vars["mgmt_addr"] = get_netmask(f"{'.'.join(octets)}/{prefix}")
    # INTF: Swap prefix for netmask on all non-mgmt interfaces
    if nd_vars.get("intf") != None:
        for each_intf, each_addr in nd_vars["intf"].items():
            nd_vars["intf"][each_intf] = get_netmask(each_addr)
    # Render the template
    env = Environment(
        loader=FileSystemLoader("./"), trim_blocks=True, lstrip_blocks=True
    )
    template = env.get_template(template_file)
    startup_cfg = template.render(nd_vars)
    return startup_cfg


# ----------------------------------------------------------------------------
# 3. NETMASK: Get netmask from prefix for use in jinja template
# ----------------------------------------------------------------------------
def get_netmask(ip_pfx: str) -> str:
    """
    It takes an IP network in CIDR notation and returns the netmask

    :param ip_pfx: The IP address and subnet mask in CIDR notation
    :return: The IP address and netmask of the ip_pfx
    """
    if ip_pfx == "dhcp":
        return ip_pfx
    else:
        try:
            ip = ip_pfx.split("/")[0]
            netmask = IPv4Interface(ip_pfx).netmask
            return str(ip) + " " + str(netmask)
        except:
            return f"❌ERROR: The prefix {ip_pfx} is not a properly formatted IPv4 network."


# ----------------------------------------------------------------------------
# 2-4. LOCATION: Uses the loop index (even or odd) to step device location (down and/or right)
# ----------------------------------------------------------------------------
def set_location(idx: int, x: int, y: int) -> tuple[int, int]:
    if idx % 2 == 0:
        y = -80  # High height for even loop index
        x = x + 200  # Moves devices over (right) in every even loop index
    else:
        y = 200  # High height for even loop index
    return x, y


if __name__ == "__main__":
    main()
