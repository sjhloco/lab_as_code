# Netlab configuration modules

[Netlab configuration modules](https://netlab.tools/module-reference/) are used to generate the configuration for device features and deploys this configuration with Ansible after the initial startup configuration. The features supported are:

- Routing protocols: *OSPF, IS-IS, EIGRP, BGP, RIPv2/ng*
- Additional control-plane protocols or BGP address families: *BFD, EVPN, MPLS/VPN, FHRP*
- Layer-2 control plane: *STP, LAG*
- Data plane: *VLAN, VRF, VXLAN, MPLS, SR-MPLS, SRv6*
- Network services: *DHCP, DHCPv6*
- IPv6 support: *IPv6 addresses, OSPFv3, IS-IS MT, EIGRP IPv6 AF, BGP IPv6 AF, SR-MPLS*

For any features not covered by the modules you can apply custom config snippets using your own jinja templates. The .j2 template file is created in the lab directory and then referenced (no need for .j2 extension) under a node with `config [ template_name ]`. You can use existing *host_vars* (*host_vars/NODE_NAME/topology.yml*) and existing or custom *group_vars* (set with `vars` under a group) in the template. For example, the below template and group_vars are to deploy OSPF and NAT on an ASA.

```jinja
router ospf {{ ospf.process }}
 router-id {{ ospf.router_id }} 
 network {{ interfaces[0]["ipv4"] | ipaddr('address') }} {{ interfaces[0]["ipv4"] | ipaddr('netmask') }} area {{ ospf.area }}
 redistribute static subnets
```

```yaml
groups
  asa:
    members: [ XNET-ASA ]
    vars:
      ospf:
        router_id: 3.3.3.3
        process: 1
        area: 0.0.0.0
```

This lab topology and configuration that is achieved with the *netlab_topo.yml*.

!!! image !!!!

I have had to stop using *AS path prepend* (hashed out *plugin: [ bgp.policy ]*) because if the plugin is enabled and there are clab linux containers (*device: linux*) in the lab ***netlab up*** fails with the following message:

  ```bash
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │ STARTING clab nodes                                                              │
  └──────────────────────────────────────────────────────────────────────────────────┘
  Traceback (most recent call last):
    File "/usr/local/bin/netlab", line 14, in <module>
      netsim.cli.lab_commands(__file__)
    File "/usr/local/lib/python3.12/dist-packages/netsim/cli/__init__.py", line 356, in lab_commands
      mod.run(sys.argv[arg_start:])   # type: ignore
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/usr/local/lib/python3.12/dist-packages/netsim/cli/up.py", line 368, in run
      run_up(cli_args)
    File "/usr/local/lib/python3.12/dist-packages/netsim/cli/up.py", line 331, in run_up
      start_provider_lab(topology,p_provider)
    File "/usr/local/lib/python3.12/dist-packages/netsim/cli/up.py", line 198, in start_provider_lab
      p_module.call('pre_start_lab',p_topology)
    File "/usr/local/lib/python3.12/dist-packages/netsim/utils/callback.py", line 42, in call
      return method(*args, **kwargs)
            ^^^^^^^^^^^^^^^^^^^^^^^
    File "/usr/local/lib/python3.12/dist-packages/netsim/providers/clab.py", line 204, in pre_start_lab
      load_kmods(topology)
    File "/usr/local/lib/python3.12/dist-packages/netsim/providers/clab.py", line 149, in load_kmods
      for m in (['initial']+ndata.get('module',[])):          # Now iterate over all the netlab modules the node uses
                ~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~~
    File "box/box.py", line 317, in box.box.Box.__radd__
  box.exceptions.BoxTypeError: Box can only merge two boxes or a box and a dictionary.
  ```