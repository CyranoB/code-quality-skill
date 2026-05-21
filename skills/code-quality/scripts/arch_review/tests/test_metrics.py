"""Unit tests for metrics.py."""
from __future__ import annotations

import unittest

from arch_review.metrics import find_cycles, compute_coupling, find_deep_chains


class FindCyclesTest(unittest.TestCase):
    def test_no_cycles_in_dag(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": []}
        self.assertEqual(find_cycles(graph), [])

    def test_finds_two_node_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["a"]}
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b"})

    def test_finds_three_node_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b", "c"})

    def test_finds_multiple_independent_cycles(self) -> None:
        graph = {
            "a": ["b"], "b": ["a"],
            "c": ["d"], "d": ["c"],
            "e": [],
        }
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 2)


class ComputeCouplingTest(unittest.TestCase):
    def test_isolated_node(self) -> None:
        graph = {"a": []}
        m = compute_coupling(graph)
        self.assertEqual(m["a"], {"ca": 0, "ce": 0, "i": 0.0})

    def test_simple_chain(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": []}
        m = compute_coupling(graph)
        # a: imports b (Ce=1), no importers (Ca=0)
        self.assertEqual(m["a"]["ca"], 0)
        self.assertEqual(m["a"]["ce"], 1)
        self.assertEqual(m["a"]["i"], 1.0)
        # b: imported by a (Ca=1), imports c (Ce=1)
        self.assertEqual(m["b"]["ca"], 1)
        self.assertEqual(m["b"]["ce"], 1)
        self.assertEqual(m["b"]["i"], 0.5)
        # c: imported by b (Ca=1), no imports (Ce=0)
        self.assertEqual(m["c"]["ca"], 1)
        self.assertEqual(m["c"]["ce"], 0)
        self.assertEqual(m["c"]["i"], 0.0)

    def test_hub_module(self) -> None:
        graph = {"a": ["e"], "b": ["e"], "c": ["e"], "d": ["e"], "e": []}
        m = compute_coupling(graph)
        self.assertEqual(m["e"]["ca"], 4)
        self.assertEqual(m["e"]["ce"], 0)


class FindDeepChainsTest(unittest.TestCase):
    def test_linear_chain(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}
        chains = find_deep_chains(graph, min_depth=3)
        self.assertTrue(any(c[0] == "a" and c[-1] == "d" for c in chains))

    def test_does_not_report_chains_shorter_than_min(self) -> None:
        graph = {"a": ["b"], "b": []}
        chains = find_deep_chains(graph, min_depth=3)
        self.assertEqual(chains, [])

    def test_safe_with_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["a"]}
        chains = find_deep_chains(graph, min_depth=3)
        self.assertIsInstance(chains, list)


if __name__ == "__main__":
    unittest.main()
