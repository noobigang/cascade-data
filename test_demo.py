import json
import sys

import networkx as nx

sys.path.insert(0, r"C:\Users\mrham\.mavis\sessions\mvs_bdf526f4764c45a1ab5698fa4265cada\workspace\cascade-data")
from cascade.parser.manifest_parser import parse_manifest_from_dict

manifest_path = r"C:\Users\mrham\.mavis\sessions\mvs_bdf526f4764c45a1ab5698fa4265cada\workspace\cascade-data\demo\manifest.json"
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)

nodes = parse_manifest_from_dict(manifest)
print(f"Total nodes parsed: {len(nodes)}")
for n in nodes:
    print(f"  {n.unique_id}: {n.resource_type} | deps={len(n.depends_on)} | cols={len(n.columns)}")

# Build DAG
dag = nx.DiGraph()
for n in nodes:
    dag.add_node(n.unique_id, resource_type=n.resource_type)
for n in nodes:
    for dep in n.depends_on:
        if dep in dag:
            dag.add_edge(dep, n.unique_id)

print(f"\nDAG: {dag.number_of_nodes()} nodes, {dag.number_of_edges()} edges")
print(f"Root nodes (no incoming edges): {[n for n in dag.nodes if dag.in_degree(n)==0]}")
print(f"Leaf nodes (no outgoing edges): {[n for n in dag.nodes if dag.out_degree(n)==0]}")

# Check stg_orders feeds 3+ marts
stg_children = list(dag.successors("model.ecommerce.stg_orders"))
print(f"\nstg_orders downstream: {stg_children}")
print(f"stg_orders feeds {len(stg_children)} nodes (need 3+): {'PASS' if len(stg_children)>=3 else 'FAIL'}")

# Check mart_marketing_roi is leaf
mkt_children = list(dag.successors("model.ecommerce.mart_marketing_roi"))
print(f"mart_marketing_roi downstream: {mkt_children} (should be []): {'PASS' if len(mkt_children)==0 else 'FAIL'}")

# Check dim_date feeds all 5 marts
dim_date_children = list(dag.successors("seed.ecommerce.dim_date"))
print(f"dim_date downstream: {dim_date_children}")
mart_nodes = [n for n in dag.nodes if n.startswith("model.ecommerce.mart_")]
print(f"Mart nodes: {mart_nodes}")
for m in mart_nodes:
    has_dd = "seed.ecommerce.dim_date" in dag.predecessors(m)
    print(f"  {m} depends on dim_date: {has_dd}")
