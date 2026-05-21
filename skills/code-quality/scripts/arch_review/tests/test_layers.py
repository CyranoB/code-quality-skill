"""Unit tests for layers.py."""
from __future__ import annotations

import unittest

from arch_review.layers import infer_layer, find_layer_violations


class InferLayerTest(unittest.TestCase):
    def test_presentation_match(self) -> None:
        self.assertEqual(infer_layer("src/api/users.py", "none"), "presentation")
        self.assertEqual(infer_layer("src/routes/auth.ts", "none"), "presentation")

    def test_application_match(self) -> None:
        self.assertEqual(infer_layer("src/services/orders.py", "none"), "application")
        self.assertEqual(infer_layer("src/usecases/checkout.ts", "none"), "application")

    def test_domain_match(self) -> None:
        self.assertEqual(infer_layer("src/domain/user.py", "none"), "domain")
        self.assertEqual(infer_layer("src/entities/order.py", "none"), "domain")

    def test_infrastructure_match(self) -> None:
        self.assertEqual(infer_layer("src/db/session.py", "none"), "infrastructure")
        self.assertEqual(infer_layer("src/repositories/user_repo.py", "none"), "infrastructure")

    def test_unclassified(self) -> None:
        self.assertIsNone(infer_layer("src/foo/bar.py", "none"))

    def test_nextjs_app_is_presentation(self) -> None:
        self.assertEqual(infer_layer("app/dashboard/page.tsx", "nextjs"), "presentation")
        self.assertEqual(infer_layer("pages/index.tsx", "nextjs"), "presentation")

    def test_django_models_is_infrastructure(self) -> None:
        self.assertEqual(infer_layer("myapp/models.py", "django"), "infrastructure")
        self.assertEqual(infer_layer("myapp/models/user.py", "django"), "infrastructure")
        self.assertEqual(infer_layer("myapp/models/user.py", "none"), "domain")

    def test_fastapi_routers_is_presentation(self) -> None:
        self.assertEqual(infer_layer("src/routers/users.py", "fastapi"), "presentation")


class FindLayerViolationsTest(unittest.TestCase):
    def test_detects_domain_to_infrastructure(self) -> None:
        graph = {
            "src/domain/order.py": ["src/db/session.py"],
            "src/db/session.py": [],
        }
        layers = {"src/domain/order.py": "domain", "src/db/session.py": "infrastructure"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["importer_layer"], "domain")
        self.assertEqual(v["imported_layer"], "infrastructure")

    def test_allows_outer_to_inner(self) -> None:
        graph = {
            "src/api/users.py": ["src/domain/user.py"],
            "src/domain/user.py": [],
        }
        layers = {"src/api/users.py": "presentation", "src/domain/user.py": "domain"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(violations, [])

    def test_unclassified_imports_are_ignored(self) -> None:
        graph = {
            "src/foo/bar.py": ["src/db/session.py"],
            "src/db/session.py": [],
        }
        layers = {"src/foo/bar.py": None, "src/db/session.py": "infrastructure"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
