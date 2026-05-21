"""Graph metrics — cycles, coupling (Ca/Ce/I), deep chains."""
from __future__ import annotations

import sys
from typing import Dict, List

# Tarjan SCC can recurse deeply; raise the stack limit modestly.
sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))


def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Find all simple cycles via Tarjan's SCC algorithm.

    A non-trivial SCC (size > 1, or single-node with self-loop) counts as a cycle.
    """
    index_counter = [0]
    stack: List[str] = []
    lowlinks: Dict[str, int] = {}
    indices: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    result: List[List[str]] = []

    def strongconnect(node: str) -> None:
        indices[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True

        for successor in graph.get(node, []):
            if successor not in indices:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif on_stack.get(successor):
                lowlinks[node] = min(lowlinks[node], indices[successor])

        if lowlinks[node] == indices[node]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            if len(scc) > 1 or (len(scc) == 1 and scc[0] in graph.get(scc[0], [])):
                result.append(scc)

    for n in list(graph):
        if n not in indices:
            strongconnect(n)
    return result


def compute_coupling(graph: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
    """Compute Ca (afferent), Ce (efferent), I (instability) per node.

    I = Ce / (Ca + Ce), defaulting to 0.0 when both are zero.
    """
    ca: Dict[str, int] = {n: 0 for n in graph}
    ce: Dict[str, int] = {n: len(set(deps)) for n, deps in graph.items()}
    for src, deps in graph.items():
        for d in set(deps):
            if d in ca:
                ca[d] += 1
    out: Dict[str, Dict[str, float]] = {}
    for n in graph:
        denom = ca[n] + ce[n]
        i = (ce[n] / denom) if denom else 0.0
        out[n] = {"ca": ca[n], "ce": ce[n], "i": round(i, 3)}
    return out


def find_deep_chains(
    graph: Dict[str, List[str]],
    min_depth: int = 6,
    max_paths: int = 50,
) -> List[List[str]]:
    """Find the deepest acyclic import chains.

    Returns up to `max_paths` chains of length >= min_depth, sorted by length descending.
    Cycle-safe via a per-path visited set.
    """
    chains: List[List[str]] = []

    def dfs(node: str, path: List[str], visited: set) -> None:
        successors = [s for s in graph.get(node, []) if s not in visited]
        if not successors:
            if len(path) >= min_depth:
                chains.append(list(path))
            return
        for s in successors:
            visited.add(s)
            path.append(s)
            dfs(s, path, visited)
            path.pop()
            visited.discard(s)

    for start in list(graph):
        dfs(start, [start], {start})

    chains.sort(key=len, reverse=True)
    return chains[:max_paths]
