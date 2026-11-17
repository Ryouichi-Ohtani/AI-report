import unittest
import numpy as np
from triangle_ga import Genome, render, Objective, metrics, evolve, crossover
from targets import landscape, add_noise


class TriangleTests(unittest.TestCase):
    def test_drawing_order_and_exact_error(self):
        genes = np.array([[0,0,7,0,0,7,255,0,0], [0,0,7,0,0,7,0,255,0]], float)
        image = render(Genome(genes), 8, np.zeros(3))
        np.testing.assert_array_equal(image[0,0], [0,1,0])
        self.assertEqual(Objective((image*255).astype(np.uint8), "mae")(image,2), 0)

    def test_metrics_zero(self):
        image = landscape(16)
        result = metrics(image.astype(np.float32)/255, image)
        self.assertEqual(result["mae"], 0)
        self.assertEqual(result["edge_mae"], 0)

    def test_real_ga_budget_reproducible_and_elitist(self):
        image = add_noise(landscape(16))
        a = evolve(image, seed=1, evaluations=100, count=8, variable=True)
        b = evolve(image, seed=1, evaluations=100, count=8, variable=True)
        self.assertEqual(a["genome"], b["genome"])
        self.assertEqual(a["evaluations"], 100)
        self.assertEqual(a["trace"][-1]["evaluations"], 100)
        losses = [x["loss"] for x in a["trace"]]
        self.assertTrue(all(x >= y for x,y in zip(losses, losses[1:])))
        self.assertTrue(2 <= a["count"] <= 48)

    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            evolve(landscape(8), evaluations=2)

    def test_crossover_is_not_parent_alias(self):
        a = Genome(np.zeros((3,9)))
        b = Genome(np.ones((4,9)))
        child = crossover(a,b,np.random.default_rng(1))
        child.triangles[0,0] = 90
        self.assertEqual(a.triangles[0,0], 0)
        self.assertEqual(b.triangles[0,0], 1)


if __name__ == "__main__":
    unittest.main()
