# Labbing as code

This repo holds the code and data in relation to the *lab as code* [part1](https://theworldsgonemad.net/2025/lab-as-code-pt1/) and [part2](https://theworldsgonemad.net/2025/lab-as-code-pt2/) blogs I wrote about trying to deploy labs from a semi-declarative YAML file rather than using the GUI. The idea behind it is to define the devices, links and a bootstrap config to bring the lab up in a state ready to apply features and do your actual labbing. This includes:

- Management VRF, IP and GW connected to a pass through network to allow access to the lab device from an external remote host
- Username, password, privileges and sessions to allow generation of SSH key and therefore SSH access
- IP or VLAN configuration for all interfaces on the device

The associated folders are my attempts to deploy labs using the different tool-sets:

- [**evengsdk topology builder**](https://ttafsir.github.io/evengsdk/topology_builder/): Uses a pre-built tool to deploy a lab from a topology file with the device startup config generated by jinja templates
- [**cmlutils**](https://github.com/CiscoDevNet/virlutils): Uses a pre-built tool to import a CML lab file, device configs must be input statically in this same file
- **EVE-NG/CML custom tool**: Makes use of the [evengsdk](https://ttafsir.github.io/evengsdk/api_reference/#evengsdk.api.EvengApi.create_lab) and [virl2-client](https://github.com/CiscoDevNet/virl2-client) libraries to deploy labs from a minimalistic topology file with the device startup config generated by jinja templates
- **[Containerlab](https://containerlab.dev):** Deploys the lab from a minimalistic topology file and natively applies device management config to allow SSH access
- **[Netlab](https://netlab.tools):** Deploys a lab using VMs (vagrant) and containers (clab) from a minimalistic topology file and uses Ansible to generate and apply initial startup config as well as more advanced feature configurations (VLANs, routing protocols, etc)
- **[Netlab configuration modules](https://netlab.tools/module-reference/)** Generates the configuration for device features (VRF, VLAN, BGP, etc) and deploys this configuration with Ansible after the initial startup configuration
