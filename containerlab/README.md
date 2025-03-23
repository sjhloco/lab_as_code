# containerlab

[Containerlab](https://containerlab.dev) deploys the lab from a minimalistic topology file and natively applies device management config to allow SSH access. The topology file is split up into 4 parts

**lab/mgmt:** The lab and node naming syntax as well as the management network details.

```yaml
name: # The lab name is by default added to each node name, so they are named in the format clab-{{lab_name}}-{{node_name}}
prefix: # Replaces "clab" so becomes {{prefix}}-{{lab_name}}-{{node_name}}, or if you use "" removes everything so you just have {{node_name}}
mgmt: # This is optional, if you omit creates the a docker network called 'clab' (type bridge) with a subnet of 172.20.20.0/24
  network: # Name for the docker network, can check with 'docker network ls' and 'docker network inspect <name>'
  ipv4-subnet: # Subnet assigned to the management network, so what the node IPs will come from (local only to docker host)
```

**kinds:** Defines the parameters of the different device types, this can be configured either here or at the node level. Configuring here means less repetition keeping the topology file cleaner, you can always override any of these settings on a per-node basis. For example, IOL covers switches and routers, so you can set router as global kind and override *image* and *type* on the odd nodes that are a switch.

```yaml
# Kinds, links and nodes are all defined under the topology dictionary
topology: 
  kinds:
    cisco_iol: # Name of the kind, can find full list at https://containerlab.dev/manual/kinds/
      image: # The device type image, follows the same naming rules as the images you use with Docker
      type: # A further classification for a kind, such as 'l2' for IOL switch
```

Are a lot more optional parameters which again can be set here or under the node.

**nodes:** Dictionary of nodes with the key being the node name and value the node details. *kind* is mandatory but all other attributes are optional, there are many more available. If you don't define a mgmt address it will be assigned by DHCP from the mgmt range. The mgmt network is only accessible locally from the containerlab host, to access hosts remotely add a *port* binding in the same format used with `docker run -p/--export`.

```yaml
  nodes:
    ISP:
      kind: # The type of device
      image: # The device type image
      type: # A further clarification for the device type
      startup-config: # Files of either full config (replace/override the default config) or partial to amend to existing (file name ends .partial). Can also just add raw config inline
      mgmt-ipv4: # Optionally set static IP, if omit is automatically assigned from the mgmt range
      ports: #List of ports to "expose", so to allow for accessing the device from a remote host using containerlab server ip
        - # Port translation in the format "Containerlab_server_port:node_port"
```

You can also define a static startup config file under the node, the lack of any ability to template it seems to be by design according to [this](https://github.com/srl-labs/containerlab/issues/1371).

**links:** List of links between nodes. They can be defined in brief format (as below) where you just define the device and interface name (linux interface name or 'true' device interface name) or in extended format where you can define the link type (veth, mgmt-net, vxlan, etc) and other link parameters such as mac, mtu and link type specific settings.

```yaml
  links:
    - endpoints: ["node_a:intf_a","node_b:intf_b"] 
```

Containerlab supports two kinds of interface naming, *Linux interfaces* and *interface aliases*. Linux interface names normally do not match the name used by the NOS which is where interface aliases come in with interface aliases transparently mapping to Linux interface names.

Deploying the lab is pretty straightforward, if you are using just containerised images it is amazing how fast everything comes up. The lab layout is the same as from the previous blog but to avoid using non-native container images the CSR and ASA have been swapped for cEOS and IOL.

```bash
$ containerlab deploy -t clab_topo.yml
INFO[0000] Containerlab v0.64.0 started
INFO[0000] Parsing & checking topology file: clab_topo.yml
INFO[0000] Creating docker network: Name="mgmt", IPv4Subnet="192.168.255.0/24", IPv6Subnet="", MTU=0
INFO[0000] Creating lab directory: /home/ste/containerlab/clab_topo/clab-clab_topo
INFO[0000] Creating container: "WS01"
INFO[0000] Creating container: "R1"
INFO[0003] Running postdeploy actions for Cisco IOL 'R1' node
INFO[0003] Creating container: "XNET-FW"
INFO[0005] Creating container: "XNET-SWI"
INFO[0013] Running postdeploy actions for Cisco IOL 'XNET-FW' node
INFO[0013] Creating container: "CORE-SWI"
INFO[0014] Created link: XNET-SWI:eth1 (e0/1) <--> R1:eth2 (e0/2)
INFO[0014] Created link: XNET-SWI:eth3 (e0/3) <--> XNET-FW:eth1 (e0/1)
INFO[0014] Running postdeploy actions for Cisco IOL 'XNET-SWI' node
INFO[0014] Creating container: "ISP"
INFO[0017] Created link: CORE-SWI:eth1 (e0/1) <--> XNET-FW:eth2 (e0/2)
INFO[0030] Created link: CORE-SWI:eth3 (e0/3) <--> WS01:eth1
INFO[0030] Running postdeploy actions for Cisco IOL 'CORE-SWI' node
INFO[0030] Creating container: "R2"
INFO[0031] Created link: ISP:eth1 <--> R1:eth1 (e0/1)
INFO[0031] Running postdeploy actions for Arista cEOS 'ISP' node
INFO[0032] Created link: ISP:eth2 <--> R2:eth1 (e0/1)
INFO[0032] Created link: XNET-SWI:eth2 (e0/2) <--> R2:eth2 (e0/2)
INFO[0032] Running postdeploy actions for Cisco IOL 'R2' node
INFO[0033] Creating container: "SVR01"
INFO[0056] Created link: CORE-SWI:eth2 (e0/2) <--> SVR01:eth1
INFO[0201] Adding containerlab host entries to /etc/hosts file
INFO[0201] Adding ssh config for containerlab nodes
╭──────────┬─────────────────────────────────┬─────────┬────────────────╮
│   Name   │            Kind/Image           │  State  │ IPv4/6 Address │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ CORE-SWI │ cisco_iol                       │ running │ 192.168.255.31 │
│          │ vrnetlab/cisco_iol:L2-17.12.01  │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ ISP      │ ceos                            │ running │ 192.168.255.10 │
│          │ ceos:4.33.1F                    │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ R1       │ cisco_iol                       │ running │ 192.168.255.11 │
│          │ vrnetlab/cisco_iol:17.12.01     │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ R2       │ cisco_iol                       │ running │ 192.168.255.12 │
│          │ vrnetlab/cisco_iol:17.12.01     │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ SVR01    │ linux                           │ running │ 192.168.255.32 │
│          │ ghcr.io/hellt/network-multitool │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ WS01     │ linux                           │ running │ 192.168.255.33 │
│          │ ghcr.io/hellt/network-multitool │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ XNET-FW  │ cisco_iol                       │ running │ 192.168.255.22 │
│          │ vrnetlab/cisco_iol:17.12.01     │         │ N/A            │
├──────────┼─────────────────────────────────┼─────────┼────────────────┤
│ XNET-SWI │ cisco_iol                       │ running │ 192.168.255.21 │
│          │ vrnetlab/cisco_iol:L2-17.12.01  │         │ N/A            │
╰──────────┴─────────────────────────────────┴─────────┴────────────────╯
```

You can use *`docker logs -f <container-name>`* to actively view the boot process of any of the containers. *`containerlab inspect -t clab_topo.yml`* to review the above table of node status.

As you would expect under the hood you have docker containers, from here you can verify the port-forwarding:

```bash
ste@mob-ubt-doc01:~/containerlab$ docker container ls
CONTAINER ID   IMAGE                             COMMAND                  CREATED         STATUS         PORTS                                                        NAMES
1fafef007c74   vrnetlab/cisco_iol:L2-17.12.01    "/entrypoint.sh"         5 minutes ago   Up 5 minutes   0.0.0.0:65021->22/tcp, [::]:65021->22/tcp                    XNET-SWI
87abcd513ab9   vrnetlab/cisco_iol:17.12.01       "/entrypoint.sh"         5 minutes ago   Up 5 minutes   0.0.0.0:65022->22/tcp, [::]:65022->22/tcp                    XNET-FW
38444ba39f4c   ghcr.io/hellt/network-multitool   "/docker-entrypoint.…"   5 minutes ago   Up 5 minutes   80/tcp, 443/tcp, 0.0.0.0:65032->22/tcp, [::]:65032->22/tcp   SVR01
5945e2f55bd5   vrnetlab/cisco_iol:17.12.01       "/entrypoint.sh"         6 minutes ago   Up 5 minutes   0.0.0.0:65012->22/tcp, [::]:65012->22/tcp                    R2
7b76cad307ae   vrnetlab/cisco_iol:17.12.01       "/entrypoint.sh"         6 minutes ago   Up 6 minutes   0.0.0.0:65011->22/tcp, [::]:65011->22/tcp                    R1
2f15ce504702   ceos:4.33.1F                      "bash -c '/mnt/flash…"   6 minutes ago   Up 6 minutes   0.0.0.0:65010->22/tcp, [::]:65010->22/tcp                    ISP
c11ea7d5ff03   vrnetlab/cisco_iol:L2-17.12.01    "/entrypoint.sh"         6 minutes ago   Up 6 minutes   0.0.0.0:65031->22/tcp, [::]:65031->22/tcp                    CORE-SWI
a56c60dd9bd8   ghcr.io/hellt/network-multitool   "/docker-entrypoint.…"   6 minutes ago   Up 6 minutes   80/tcp, 443/tcp, 0.0.0.0:65033->22/tcp, [::]:65033->22/tcp   WS01
```

A really nice feature is the interactive topology map, you render it locally and access in a browser with `http://<containerlan_ip>:50080`

```bash
$ containerlab graph -t clab_topo.yml
INFO[0000] Parsing & checking topology file: clab_topo.yml
INFO[0000] Serving topology graph on http://0.0.0.0:50080
```

<img width="888" alt="Image" src="https://github.com/user-attachments/assets/b684a59b-e14d-4df7-b2c9-ba4d04f21137" />

A Cisco IOL container starts with a bootstrap config that uses *Ethernet0/0* for management (clab always uses 1st interface for management) in the *clab-mgmt* VRF and enables SSH. Have 3 ways to access the nodes, the username/password is whatever the default is for that device_type:

- SSH to the management IP from the containerlab host
- SSH remotely to the containerlab host IP using the exposed port
- Access the container using  *`docker exec -it <device_name> bash`*. This is limited as can only access the CLI on certain nodes such as SRL (swap bash for sr_cli), is no option for IOL

When a lab is deployed containerlab creates a local directory that holds things such as device configs and an ansible_inventory file. Once finished with the lab are a few options for tearing it down:

```bash
containerlab destroy -t clab_topo.yml                 # Shuts down everything in the lab maintaining any saved configurations
containerlab destroy -t clab_topo.yml --cleanup       # Shuts down everything in the lab and factory resets the devices (deletes the lab folder)
containerlab redeploy -t clab_topo.yml                # Combines the `destroy` and `deploy` commands into a single operation so you can edit the lab topology without losing current configs
```
