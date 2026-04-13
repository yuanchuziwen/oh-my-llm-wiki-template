#!/usr/bin/env python3
"""
LLM Wiki — Knowledge Graph MCP Server

自建的轻量图谱查询服务，基于 NetworkX。
Agent 平台（Claude Code / Cursor）启动时自动拉起本进程，退出时自动关闭。

依赖：pip install networkx mcp
"""

import asyncio
import json
import os
import sys
import threading

import networkx as nx
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# ---------------------------------------------------------------------------
# 图谱加载
# ---------------------------------------------------------------------------

GRAPH_PATH = os.environ.get(
    "WIKI_GRAPH_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "graph", "graph.json"),
)

G: nx.Graph | None = None


def load_graph() -> nx.Graph | None:
    """加载 graph.json，不存在时返回 None（降级模式）。"""
    if not os.path.isfile(GRAPH_PATH):
        print(f"[wiki-graph] graph.json not found at {GRAPH_PATH}, running in empty mode", file=sys.stderr)
        return None
    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        graph = nx.node_link_graph(data, edges="links")
        print(f"[wiki-graph] loaded {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges", file=sys.stderr)
        return graph
    except Exception as exc:
        print(f"[wiki-graph] failed to load graph: {exc}", file=sys.stderr)
        return None


def reload_graph() -> None:
    """重新加载图谱（Ingest 后调用）。"""
    global G
    G = load_graph()


# ---------------------------------------------------------------------------
# 查询工具实现
# ---------------------------------------------------------------------------


def _empty_notice() -> str:
    return "图谱为空或未加载。请先执行一次 Ingest 操作生成 graph/graph.json。"


def handle_get_neighbors(arguments: dict) -> str:
    """查询某节点的关联节点（1-N 跳），可选按置信度过滤。"""
    if G is None:
        return _empty_notice()
    node_id = arguments["node_id"]
    depth = arguments.get("depth", 1)
    min_confidence = arguments.get("min_confidence")
    if node_id not in G:
        return f"节点 '{node_id}' 不存在于图谱中。"
    subgraph = nx.ego_graph(G, node_id, radius=depth)
    neighbors = []
    for n in subgraph.nodes():
        if n == node_id:
            continue
        attrs = dict(G.nodes[n])
        neighbors.append({"id": n, **attrs})
    # 置信度过滤
    confidence_rank = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}
    min_rank = confidence_rank.get(min_confidence, 0) if min_confidence else 0
    edges = []
    for u, v, data in subgraph.edges(data=True):
        edge_conf = data.get("confidence", "EXTRACTED")
        if confidence_rank.get(edge_conf, 0) >= min_rank:
            edges.append({"source": u, "target": v, **data})
    return json.dumps(
        {"center": node_id, "depth": depth, "neighbors": neighbors, "edges": edges},
        ensure_ascii=False,
        indent=2,
    )


def handle_shortest_path(arguments: dict) -> str:
    """查询两节点间的最短路径。"""
    if G is None:
        return _empty_notice()
    source = arguments["source"]
    target = arguments["target"]
    for node_id in (source, target):
        if node_id not in G:
            return f"节点 '{node_id}' 不存在于图谱中。"
    try:
        path = nx.shortest_path(G, source, target)
    except nx.NetworkXNoPath:
        return f"'{source}' 和 '{target}' 之间没有连通路径。"
    # 收集路径上的边信息
    path_edges = []
    for i in range(len(path) - 1):
        edge_data = G.edges[path[i], path[i + 1]]
        path_edges.append({"from": path[i], "to": path[i + 1], **dict(edge_data)})
    return json.dumps(
        {"path": path, "length": len(path) - 1, "edges": path_edges},
        ensure_ascii=False,
        indent=2,
    )


def handle_top_nodes(arguments: dict) -> str:
    """返回连接度最高的节点。"""
    if G is None:
        return _empty_notice()
    limit = arguments.get("limit", 10)
    ranked = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:limit]
    result = []
    for node_id, degree in ranked:
        attrs = dict(G.nodes[node_id])
        result.append({"id": node_id, "degree": degree, **attrs})
    return json.dumps(result, ensure_ascii=False, indent=2)


def handle_graph_stats(arguments: dict) -> str:
    """返回图谱统计信息（含置信度分布）。"""
    if G is None:
        return _empty_notice()
    isolated = list(nx.isolates(G))
    type_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    # 置信度分布
    confidence_counts: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        c = data.get("confidence", "EXTRACTED")
        confidence_counts[c] = confidence_counts.get(c, 0) + 1
    return json.dumps(
        {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "isolated_nodes": len(isolated),
            "node_types": type_counts,
            "confidence_distribution": confidence_counts,
            "density": round(nx.density(G), 4),
        },
        ensure_ascii=False,
        indent=2,
    )


def handle_get_node(arguments: dict) -> str:
    """返回单个节点的详细信息。"""
    if G is None:
        return _empty_notice()
    node_id = arguments["node_id"]
    if node_id not in G:
        return f"节点 '{node_id}' 不存在于图谱中。"
    attrs = dict(G.nodes[node_id])
    # 附加邻居列表
    neighbor_ids = list(G.neighbors(node_id))
    # 附加关联边
    edges = []
    for u, v, data in G.edges(node_id, data=True):
        other = v if u == node_id else u
        edges.append({"target": other, **dict(data)})
    return json.dumps(
        {"id": node_id, "degree": G.degree(node_id), "attributes": attrs, "neighbors": neighbor_ids, "edges": edges},
        ensure_ascii=False,
        indent=2,
    )


def handle_reload(arguments: dict) -> str:
    """重新加载 graph.json（Ingest 后调用）。"""
    reload_graph()
    if G is None:
        return "重新加载完成，但 graph.json 不存在或加载失败。"
    return f"重新加载完成。当前图谱：{G.number_of_nodes()} 个节点，{G.number_of_edges()} 条边。"


# 工具分发表
_handlers = {
    "get_neighbors": handle_get_neighbors,
    "shortest_path": handle_shortest_path,
    "top_nodes": handle_top_nodes,
    "graph_stats": handle_graph_stats,
    "get_node": handle_get_node,
    "reload": handle_reload,
}

# ---------------------------------------------------------------------------
# MCP Server 定义
# ---------------------------------------------------------------------------

server = Server("wiki-graph")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_neighbors",
            description="查询某节点的关联节点（1-N 跳）。输入节点 ID，返回邻居节点和关联边。可选按置信度过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "节点 ID（与 wiki 文件名一致，如 llm-wiki）"},
                    "depth": {"type": "integer", "description": "查询深度（跳数），默认 1", "default": 1},
                    "min_confidence": {
                        "type": "string",
                        "enum": ["EXTRACTED", "INFERRED", "AMBIGUOUS"],
                        "description": "最低置信度过滤：EXTRACTED 只返回明确关系，INFERRED 包含推断，AMBIGUOUS 返回全部",
                    },
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="shortest_path",
            description="查询两个节点之间的最短路径，发现隐含关联链。",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "起始节点 ID"},
                    "target": {"type": "string", "description": "目标节点 ID"},
                },
                "required": ["source", "target"],
            },
        ),
        types.Tool(
            name="top_nodes",
            description="返回连接度最高的核心节点，了解知识库的重点。",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回数量，默认 10", "default": 10},
                },
            },
        ),
        types.Tool(
            name="graph_stats",
            description="返回图谱统计信息：节点数、边数、孤立节点、密度、置信度分布等。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_node",
            description="返回单个节点的详细信息，包括属性、邻居和关联边。",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "节点 ID"},
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="reload",
            description="重新加载 graph.json。在 Ingest 操作更新图谱后调用此工具刷新内存数据。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = _handlers.get(name)
    if not handler:
        return [types.TextContent(type="text", text=f"未知工具: {name}")]
    try:
        result = handler(arguments)
        return [types.TextContent(type="text", text=result)]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"执行 {name} 时出错: {exc}")]


# ---------------------------------------------------------------------------
# stdin 空行过滤（部分 MCP 客户端会发送空行）
# ---------------------------------------------------------------------------


def _filter_blank_stdin() -> None:
    r_fd, w_fd = os.pipe()
    saved_fd = os.dup(sys.stdin.fileno())

    def _relay() -> None:
        with open(saved_fd, "rb") as src, open(w_fd, "wb") as dst:
            for line in src:
                if line.strip():
                    dst.write(line)
                    dst.flush()

    threading.Thread(target=_relay, daemon=True).start()
    os.dup2(r_fd, sys.stdin.fileno())
    os.close(r_fd)
    sys.stdin = open(0, "r", closefd=False)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def serve(graph_path: str | None = None) -> None:
    global GRAPH_PATH, G
    if graph_path:
        GRAPH_PATH = graph_path
    G = load_graph()
    _filter_blank_stdin()

    async def main() -> None:
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    asyncio.run(main())


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    serve(path)
