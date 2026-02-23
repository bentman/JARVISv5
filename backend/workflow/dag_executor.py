from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


class WorkflowGraphError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowEdge:
    from_node: str
    to_node: str


@dataclass(frozen=True)
class WorkflowGraph:
    nodes: tuple[str, ...]
    edges: tuple[WorkflowEdge, ...]
    entry: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": [
                {"from": edge.from_node, "to": edge.to_node}
                for edge in self.edges
            ],
            "entry": self.entry,
        }


class DAGExecutor:
    def _validate_graph(self, graph: WorkflowGraph, node_registry: dict[str, Any]) -> None:
        if not graph.nodes:
            raise WorkflowGraphError("workflow graph must contain at least one node")

        node_set = set(graph.nodes)
        if graph.entry not in node_set:
            raise WorkflowGraphError(f"workflow entry node not found: {graph.entry}")

        missing_nodes = [node_id for node_id in graph.nodes if node_id not in node_registry]
        if missing_nodes:
            raise WorkflowGraphError(
                f"missing node implementations: {', '.join(sorted(missing_nodes))}"
            )

        for edge in graph.edges:
            if edge.from_node not in node_set:
                raise WorkflowGraphError(f"edge references unknown node: {edge.from_node}")
            if edge.to_node not in node_set:
                raise WorkflowGraphError(f"edge references unknown node: {edge.to_node}")

    def topological_order(self, graph: WorkflowGraph) -> list[str]:
        node_set = set(graph.nodes)
        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree = {node_id: 0 for node_id in graph.nodes}

        for edge in graph.edges:
            adjacency[edge.from_node].append(edge.to_node)
            indegree[edge.to_node] += 1

        for from_node in adjacency:
            adjacency[from_node] = sorted(adjacency[from_node])

        queue = deque(sorted(node_id for node_id in node_set if indegree[node_id] == 0))
        ordered: list[str] = []

        while queue:
            node_id = queue.popleft()
            ordered.append(node_id)
            for downstream in adjacency.get(node_id, []):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    queue.append(downstream)

        if len(ordered) != len(graph.nodes):
            raise WorkflowGraphError("workflow graph contains a cycle")

        return ordered

    def resolve_execution_order(
        self,
        graph: WorkflowGraph,
        node_registry: dict[str, Any],
    ) -> list[str]:
        self._validate_graph(graph, node_registry)
        return self.topological_order(graph)

    def execute(
        self,
        graph: WorkflowGraph,
        node_registry: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        execution_order = self.resolve_execution_order(graph, node_registry)

        for node_id in execution_order:
            context = node_registry[node_id].execute(context)

        return context
