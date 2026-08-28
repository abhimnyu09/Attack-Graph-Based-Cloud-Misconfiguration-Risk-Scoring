import streamlit as st
import pandas as pd
import json
import pathlib
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="CSPM Risk Dashboard", layout="wide")

st.title("☁️ Attack‑Graph CSPM Risk Dashboard")

DATA_DIR = pathlib.Path("/data")
findings_file = DATA_DIR / "scored_findings.jsonl"
graph_file = DATA_DIR / "graph.graphml"

# -------------------------------------------------
# Load data
# -------------------------------------------------


@st.cache_data
def load_findings():
    if not findings_file.exists():
        return pd.DataFrame()
    rows = []
    with findings_file.open() as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


@st.cache_data
def load_graph():
    if not graph_file.exists():
        return nx.DiGraph()
    return nx.read_graphml(graph_file)


df = load_findings()
G = load_graph()

# -------------------------------------------------
# Sidebar – view selector
# -------------------------------------------------
view = st.sidebar.radio("View", ["Risk‑Ranked Table", "Attack Graph"])

if view == "Risk‑Ranked Table":
    st.subheader("Findings ranked by risk_score")
    if df.empty:
        st.warning("No scored findings yet. Run `make scan graph score` first.")
    else:
        # sort
        df_sorted = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
        st.dataframe(df_sorted[["resource_id", "rule_id", "static_severity", "risk_score", "scoring_method"]],
                     use_container_width=True, height=400)

        # show attack path for selected row
        sel = st.selectbox("Select a finding to see its attack path", df_sorted.index, format_func=lambda i: f"{df_sorted.loc[i, 'resource_id']} – {df_sorted.loc[i, 'rule_id']}")
        if sel is not None:
            row = df_sorted.loc[sel]
            st.markdown("**Attack path**")
            if row["attack_path"]:
                for step in row["attack_path"]:
                    st.code(step)
            else:
                st.info("No attack path (low risk)")

else:   # Attack Graph view
    st.subheader("Full IAM Access / Escalation Graph")
    if G.number_of_nodes() == 0:
        st.warning("Graph not built yet. Run `make graph` first.")
    else:
        # Convert to agraph format
        nodes = [Node(id=n, label=n.split(":")[-1], size=20) for n in G.nodes()]
        edges = [Edge(source=u, target=v, label=d.get("action", "")) for u, v, d in G.edges(data=True)]
        config = Config(
            width=1100,
            height=750,
            directed=True,
            physics=True,
            hierarchical=True,
            hierarchicalDirection="UD",
            hierarchicalSortMethod="directed",
            nodeSpacing=180,
            levelSeparation=150,
            edgeMinimization=True,
            parentCentralization=True,
        )
        agraph(nodes=nodes, edges=edges, config=config)
