# netlab

[Netlab](https://netlab.tools) deploys a lab using VMs (vagrant) and containers (clab) from a minimalistic topology file and uses Ansible to generate and apply initial startup config as well as more advanced feature configurations (VLANs, routing protocols, etc).

In the YAML topology files you can use the normal dictionary format, the more minimal dotted decimal format or a mix of the both.

- **defaults/addressing:** Global settings which are either lab specific or provider specific. The address ranges and prefixes can be changed for any of the default address pools (*mgmt, p2p, lan, loopback, vrf_loopback, router_id*) as well as defining your own. All port-forwarding is done globally on a per-service basis, so define the the service and seed port and each node is automatically a port based on seed and node_id. Some useful commands to see default attributes:

  - `netlab show defaults`: All default attributes
  - `netlab show defaults providers`: All provider default attributes
    - `netlab show defaults providers.clab`
    - `netlab show defaults providers.libvirt`
  - `netlab show defaults addressing`: To see the default address ranges IPs are given out to different network types from
    - `netlab show defaults addressing.mgmt`: Just the mgmt address range attributes<br><br>

  ```yaml
  name: # Optional lab, it uses the directory name if undefined
  provider: # Provider used for all nodes (default is libvirt), can be overridden on a per-node basis
  tools.graphite: # Creates an interactive topology similar to clab
  defaults:
    providers.clab.bridge_type: # Change clab bridges to be ovs-bridge rather Linux bridge (OVS interferes less with L2 protocols)           
    providers.clab.lab_prefix: # Prefix added to clab node names, use "" to remove prefix so left with just the node_name
    providers.clab.forwarded.ssh: # Global clab ssh port-forwarding, maps this value + node_id to 22 on each host (verify with 'docker container ls')
    providers.libvirt.batch_size: # Number of vagrant boxes to start in each batch (default 2) 
    providers.libvirt.batch_interval: # Idle interval between batches (default 10)
    providers.libvirt.forwarded.ssh: # Global vagrant ssh port-forwarding, maps this value + node_id to 22 on each host (verify with 'netlab report mgmt')
    device: # Default node device type for the whole lab, can override on per-node basis
    devices.eos.clab.image: # clab default image (OS version) for that device type ('netlab show images')
    devices.eos.libvirt.image: # vagrant default image for that device type ('netlab show images')
  addressing:
    mgmt.ipv4: # The mgmt range, default is 192.168.121.0/24
    mgmt.start: # The offset of the first VM mgmt addr (default 100), offset + node_id = mgmt ip
    mgmt._network: # The libvirt or docker mgmt network name (default vagrant-libvirt or netlab_mgmt)
    mgmt._bridge: # The libvirt or docker mgmt bridge/switch name (default libvirt-mgmt or br-<docker_network_id)
    MY_CUSTOM_POOL:
      ipv4: # Address range of a custom pool that networks will be assigned from 
      prefix: # Prefix used for networks assigned from this range
  ```

- **nodes:** If no node attributes are being changed (they all use *"defaults.device"*) they can be defined as a list of string objects, otherwise it has to be a dictionary with the key being the *node_name* and the optional value defining nodes attributes. By default all nodes are automatically assigned a loopback interface (if supported) and node IP addresses assigned based on the node ID.<br>

  - `netlab show attributes node`: See all the possible node attributes that can be set
  - `netlab show defaults devices`: See default attributes for all device types
    - `netlab show defaults devices.iol` See the default attributes for a specific device type<br><br>

  ```yaml
    NODE_NAME:
      id: # Statically set node identifier for this specific node
      provider: # Override the globally set provider for this specific node
      device: # Overrides "defaults.device" to set device type for this specific node
      image: # The vagrant box or docker container used, can see default images with 'netlab show images'
      mgmt.ipv4: # Override the default mgmt IP that would be auto assigned from mgmt range using node id
      loopback.pool: # Override the pool that the loopback IP is automatically assigned from
      loopback.ipv4: # Override the automatic default loopback IP allocation with a static IP address
  ```

- **vlans:** VLANs are defined at global (recommended) or node level and assigned at global (access only), link or interface level. If no VLAN ID is set the ID is auto generated starting at 1000 (change with `defaults.vlan.start_vlan_id`). The default VLAN mode is ***irb*** (SVI/bridge groups with BVI interface) with a /24 address coming from the *lan* pool, the other options are ***bridge*** (VLAN/Linux bridge, no L3) or ***route*** (routed subinterfaces under VLAN trunk interface). It is recommended to define VLANs globally.
  - Globally defined VLANs will not be configured on a switch if not also associated to the switch at link or interface level
  - Node-level VLANs will be configured on that switch regardless of whether they are associated to the switch at link or interface level
  - VLANs listed within a **vlan.trunk** attribute must be defined as global VLANs.
  - `netlab show defaults vlan`: Show the VLAN module default settings
  - `netlab show attributes --module vlan`: Show all the possible VLAN module attributes <br><br>

  ```yaml
  groups:
    GROUP_NAME:
      members: # List of nodes that are group members
      module: # Have to enable the VLAN module for these switches
      vlan.mode: # To change the VLAN mode for this group of switches, by default is bridge
      device: # Set the device_type for this group of switches
  vlans:
    VLAN_NAME: 
      id: # VLAN ID, if not defined is auto generated using 'defaults.vlan.start_vlan_id` (1000)
      mode: # To override the default mode for this VLAN, by default is 'irb' and creates an SVI with an IP from lan pool
      pool: # To change the pool (and that pools mask) from which addresses are assigned from (default is lan)
      links: # List of switches to add access ports/links (switchport access vlan x), a simple way to do host ports
  ```

- **links:** A list of links with the interconnecting nodes defined under the same loop object. In a similar manner to nodes, if no attributes need to be set it can be defined as a simple string. To define attributes for the link or any of its associated node interfaces it must be a dictionary. Interfaces, networks (from address pools based on the link type) and IP addresses are all automatically assigned to links.<br><br>

  ```yaml
  links:
    - r1 # Stub link with a single node attached, assigned next /24 from lan pool. network + node_id = interface IP 
    - r1-r2 # PtP link between 2 devices, assigned next /30 from p2p pool. Alphabetically, node_a = .odd, node_b = .even
    - r1-r2-r3 # Multi-access, assigned next /24 from lan pool (if L2 change pool to l2only and use VLAN module)
    - type: # To change the default interface type (lan, p2p, stub, loopback, lag, tunnel)
      pool: # Assign network address for this link from a specific address pool (also uses prefix of that pool)
      bandwidth: # Set the bandwidth for all interfaces on this link
      r1: 
        ipv4: # Manually assign an IP address to this specific node interface
      r2:
    - HST2:
      SW3:
        vlan.access: # Interface-level Switch-to-host access link, VLAN name to assign on this specific switch interface
    - SW2:
      SW3:
      vlan.access: # link-level inter-switch access link, VLAN name to assign on the interfaces of all switches on this link
    - SW1:
      SW2:
      vlan.trunk: #  Trunk link with a list of VLAN names to allow over trunk link, can also set set VLAN attributes
  ```

Before deploying the lab is good idea to first do a *dry-run* to pick up errors and check the configuration files without having to wait for the nodes to be built. This is a 2 part process where you first *'build lab topology files'* such Ansible files, netlab snapshot and the *clab.yml* topology or *Vagrantfile*. The second command *'builds the device config snippets'* which are saved in per-device */config* folder and split up into separate files for *initial* and *module* configs. 

```bash
$ netlab create mylab.yml                 # Build lab topology files (Ansible files, netlab snapshot, clab.yml or Vagrantfile)
$ netlab initial -o                       # Builds the device config snippets and save in /config
```

Deploying the lab is slower than native containerlab as once the devices are up netlab uses Ansible to deploy the initial config.  By default all config will be applied  (initial, module and custom), can use `--no-config` to start the lab without configuring the lab devices (doesn't run Ansible).

```bash
$ ‌netlab up netlab_topo.yml
```

`netlab status` will show a table of all the lab devices, can add `-l` to show a log of all the commands run by netlab when building the lab.

```bash
$ netlab status
Lab default in /home/ste/labs/blog_lab1
  status: started
  provider(s): libvirt,clab
┏━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ node       ┃ device ┃ image                           ┃ mgmt IPv4       ┃ connection  ┃ provider ┃ VM/container         ┃ status     ┃
┡━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ ISP        │ csr    │ cisco/csr1000v                  │ 192.168.255.101 │ network_cli │ libvirt  │ netlab_topo_ISP      │ running    │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ R1         │ iol    │ vrnetlab/cisco_iol:17.12.01     │ 192.168.255.102 │ network_cli │ clab     │ R1                   │ Up 4 hours │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ R2         │ iol    │ vrnetlab/cisco_iol:17.12.01     │ 192.168.255.103 │ network_cli │ clab     │ R2                   │ Up 4 hours │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ XNET-ASA   │ asav   │ cisco/asav                      │ 192.168.255.104 │ network_cli │ libvirt  │ netlab_topo_XNET-ASA │ running    │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ CORE_SWI   │ ioll2  │ vrnetlab/cisco_iol:L2-17.12.01  │ 192.168.255.105 │ network_cli │ clab     │ CORE_SWI             │ Up 4 hours │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ ACCESS_SWI │ ioll2  │ vrnetlab/cisco_iol:L2-17.12.01  │ 192.168.255.106 │ network_cli │ clab     │ ACCESS_SWI           │ Up 4 hours │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ SVR01      │ linux  │ ghcr.io/hellt/network-multitool │ 192.168.255.107 │ docker      │ clab     │ SVR01                │ Up 4 hours │
├────────────┼────────┼─────────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────────────┼────────────┤
│ WS01       │ linux  │ python:3.13-alpine              │ 192.168.255.108 │ docker      │ clab     │ WS01                 │ Up 4 hours │
└────────────┴────────┴─────────────────────────────────┴─────────────────┴─────────────┴──────────┴──────────────────────┴────────────┘
```

By adding the *graphite* external tool (Web UI/graphing tool used with *containerlab*) to the topology file *‌netlab up* also creates an interactive topology map that can be accessed using *http://netlab_host_ip:8080/graphite/* (deploys a graphite container with port-forwarding).

<img width="1192" alt="Image" src="https://github.com/user-attachments/assets/b5531a8f-ad70-4125-ae54-9ecf73660fac" />

Can connect locally to any of the nodes using *netlab connect* (don't need to accept SSH key or enter credentials) or via SSH to the mgmt address (use `netlab report mgmt` to get the node default credentials).

```bash
$ netlab connect iol1
```

To connect remotely can either use port-forwarding (`defaults.providers.clab/libvirt.forwarded.ssh: xxx`) or add an extra NIC on the netlab host (disable DHCP for this network in fusion) put it into the management Linux bridge.

```bash
$ sudo ip link set ens34 master libvirt-mgmt                  # If libvirt or multi-provider
$ sudo ip link set ens34 master br-8c6a5186dfd1               # If clab only
$ brctl show                                                  # See all the bridges and member interfaces
```

Netlab can also create tabled reports that can be saved as text files, markdown or html pages. A few useful ones for this topology:

- `netlab report mgmt.html mgmt_report.html`: [mgmt_report.html](https://github.com/sjhloco/lab_as_code/blob/main/netlab/mgmt_report.html) shows mgmt interfaces, addresses, default creds and port-forwarding
- `netlab report wiring.html wiring_report.html`: [wiring_report.html](https://github.com/sjhloco/lab_as_code/blob/main/netlab/wiring_report.html) show lab wiring topology, so PtP and Lan links
- `netlab report addressing.html address_report.html`: [address_report.html](https://github.com/sjhloco/lab_as_code/blob/main/netlab/address_report.html) shows node interface and link interface addresses

Once finished can just lab shutdown the nodes or use `--cleanup` to delete all the files and folders that where created in the working directory.

```bash
$ netlab down
$ netlab down --cleanup
```
