# CML lab from cmlutils topology file

Uses the [cmlutils](https://github.com/CiscoDevNet/virlutils) tool to import a CML lab file, device configs must be input statically in this same file (can't use templates or external files).

**nodes:** A list of nodes with each requiring a name and unique ID, the node interfaces are defined in a similar manner. The startup config must also be included in the file, it cant be sourced externally.

```yaml
- id: # Unique identifier of the node (nX), is what is used to reference it in the links
  label: # Friendly name of the node as seen in GUI
  node_definition: # Is the device type
  image_definition: # Optionally specify an image if the node_definition has more than one 
  x: # Location from left, works on 0 being centre
  y: # Location down, works on 0 being centre
  interfaces:
    - id: # Unique identifier of the node interface (iX), is what is used to reference it in the links section 
      label: # Name of the interface
      slot: # Unique number of the interface, not sure how relates but loopback is 0 and then other interfaces start from 1
      type: # Can be physical or loopback
  configuration:
    - name: # Name of the configuration file as seen in CML GUI
      content: # Startup config (defined 'inline') to be applied to the node
```

**links:** A list of dictionaries that contain connections between nodes and connections between nodes and external connectors.

```yaml
- id: # Unique identifier of the link (lX)
  n1: # Node ID for A end of the link
  n2: # Node ID for B end of the link
  i1: # Interface ID for A end of the link
  i2: # Interface ID for B end of the link
  label: # Friendly name for the link, not sure where is used
```

The CML credentials can be set as environment variables or in a *.virlrc* file in various hierarchical locations.

```bash
pip install cmlutils

export VIRL_HOST=10.30.10.107
export VIRL_USERNAME=admin
export VIRL_PASSWORD='pa$$w0rd'
export CML_VERIFY_CERT=False
```

To view a table of all labs on the CML server.

```bash
> cml ls
Labs on Server
╒══════════════════════════════════════╤═══════════════════╤═══════════════╤═════════╤══════════╤═════════╤═════════╤══════════════╕
│ ID                                   │ Title             │ Description   │ Owner   │ Status   │   Nodes │   Links │   Interfaces │
╞══════════════════════════════════════╪═══════════════════╪═══════════════╪═════════╪══════════╪═════════╪═════════╪══════════════╡
│ 5fc145a5-b4f4-4100-9424-d1e75880a582 │ edited config     │               │ ste     │ STOPPED  │       3 │       2 │            7 │
├──────────────────────────────────────┼───────────────────┼───────────────┼─────────┼──────────┼─────────┼─────────┼──────────────┤
│ 6f1cadb8-98ae-4494-9799-6664c1e317c1 │ CML UTILs Base    │               │ ste     │ STOPPED  │       8 │       8 │           33 │
├──────────────────────────────────────┼───────────────────┼───────────────┼─────────┼──────────┼─────────┼─────────┼──────────────┤
│ edc56ab4-317e-4c00-b2f1-f906c566ad0a │ CML UTIL Topology │               │ ste     │ STARTED  │      11 │      15 │           43 │
╘══════════════════════════════════════╧═══════════════════╧═══════════════╧═════════╧══════════╧═════════╧═════════╧══════════════╛
```

The *cmlutil_lab_topo.yaml* file defines the topology to be deployed, omit *--no-start* if you want all nodes brought up immediately once the lab has been imported

```bash
❯ cml up  --no-start -f cmlutil_lab_topo.yaml
Importing lab CMLUTIL lab topology from file cmlutil_lab_topo.yaml
```

This created the following topology:

<img width="1423" alt="Image" src="https://github.com/user-attachments/assets/09237a9c-98b1-417e-b00b-cc4ff6ec5065" />


For cmlutils to be able to perform any further actions on the lab you must tell it which lab to use, this can be done with either the lab name or ID (use ID if have duplicate lab names).

```bash
❯ cml use [--id | -n] <lab_ID_or_name>
❯ cml use -n "CMLUTIL lab topology"
❯ cml id
CMLUTIL lab topology (ID: 7325c1d4-f235-422e-a28d-d3652e9a776f)
```

With the ID set can now perform actions against the lab such as check the state of all the nodes and stop or start them all:

```yaml
❯ cml nodes
Here is a list of nodes in this lab
╒══════════════════════════════════════╤══════════╤════════════════════╤════════════════╤═════════════════╤══════════╤══════════════════╕
│ ID                                   │ Label    │ Type               │ Compute Node   │ State           │ Wiped?   │ L3 Address(es)   │
╞══════════════════════════════════════╪══════════╪════════════════════╪════════════════╪═════════════════╪══════════╪══════════════════╡
│ c08d3124-119a-45b9-8059-3e8d4b699893 │ ISP      │ csr1000v           │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ e54d2b92-c36e-445e-823f-6efae39680c8 │ R1       │ iol-xe             │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ f51a7edb-d18d-496a-ab4e-3c15facfc82d │ R2       │ iol-xe             │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ 422cd679-79c6-4484-9db1-0c504860e28f │ SWI-XNET │ ioll2-xe           │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ 9d0c5742-4339-4a34-8870-a0a969236a94 │ XNET-ASA │ asav               │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ c76e93a2-846e-42c5-8a39-ee9399570ea4 │ CORE_SWI │ unmanaged_switch   │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ c7d1fad6-96ad-4d4d-842e-2c96b434d300 │ WS01     │ desktop            │ Unknown        │ DEFINED_ON_CORE │ True     │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ bcad5197-1a11-46cf-80c6-ce0b32c9059f │ SVR01    │ server             │ Unknown        │ DEFINED_ON_CORE │ True     │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ 17fcba09-4ab2-4a01-a7c7-f906d2a461b5 │ INET     │ external_connector │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ 3ce5fb79-3d2b-48a9-9dd5-15ebf1c8cf8f │ MGMT     │ external_connector │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
├──────────────────────────────────────┼──────────┼────────────────────┼────────────────┼─────────────────┼──────────┼──────────────────┤
│ db3b44a5-a899-4d9f-ad33-cba143eb9c9f │ MGMT-SWI │ unmanaged_switch   │ mob-ubt-cml01  │ BOOTED          │ False    │                  │
╘══════════════════════════════════════╧══════════╧════════════════════╧════════════════╧═════════════════╧══════════╧══════════════════╛

❯ cml down
❯ cml up
Lab CMLUTIL lab topology (ID: af8b2568-4c23-4811-aeb9-fca46d540426) is already set as the current lab
Starting lab CMLUTIL lab topology (ID: af8b2568-4c23-4811-aeb9-fca46d540426)
Exception raised while running your command
Please re-run as 'cml --debug ...' and collect the output before opening an issue
Client error - 5 of 5 node licenses are in use.
```

Another useful option within cmlutuls is the ability to console into any of the lab devices, although guess would more likely use breakout tool to do this rather than doing one at a time.

```bash
❯ cml console R1
ste@10.30.10.107's password:
Connecting to console for R1
Connected to CML terminalserver.
Escape character is '^]'.

R1>
```
