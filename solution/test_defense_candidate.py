"""Independent synthetic checks; no phase schedules or private labels."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness' / 'child_env'))
spec = importlib.util.spec_from_file_location('candidate', ROOT / 'solution' / 'defense_candidate.py')
defense = importlib.util.module_from_spec(spec)
spec.loader.exec_module(defense)


class CandidateTests(unittest.TestCase):
    def context(self):
        return SimpleNamespace(state={}, baseline=json.loads((ROOT / 'data' / 'baselines.json').read_text()))

    def test_cold_start_does_not_guess_upper_only_center(self):
        ctx = self.context()
        for _ in range(12):
            self.assertEqual(defense.subtle_signals(ctx, 'a', [('age', 6, None, 12)]), [])
        self.assertTrue(defense.subtle_signals(ctx, 'a', [('age', 11.5, None, 12)]))

    def test_groups_are_isolated(self):
        ctx = self.context()
        for _ in range(12):
            defense.subtle_signals(ctx, 'a', [('age', 6, None, 12)])
        self.assertEqual(defense.subtle_signals(ctx, 'b', [('age', 11.5, None, 12)]), [])

    def test_bound_violations_do_not_poison_history(self):
        ctx = self.context()
        for _ in range(20):
            defense.subtle_signals(ctx, 'a', [('age', 999, None, 12)])
        self.assertEqual(ctx.state['metric_history']['a']['age'], [])

    def test_two_sided_moderate_anomaly_and_clean_center(self):
        ctx = self.context()
        self.assertFalse(defense.subtle_signals(ctx, 'a', [('volume', 100, 70, 130)]))
        self.assertTrue(defense.subtle_signals(ctx, 'a', [('volume', 126, 70, 130)]))
        self.assertTrue(defense.subtle_signals(ctx, 'a', [('volume', 74, 70, 130)]))

    def test_error_results_are_handled_for_all_events(self):
        ctx = self.context()
        class BrokenTools:
            def batch_profile(self, *args): return {'error': 'unavailable'}
            contract_diff = lineage_graph_slice = feature_drift = embedding_drift = batch_profile
        ctx.tools = BrokenTools()
        payload = dict(batch_id='batch', contract_id='contract', checkpoint_batch_id='batch', run_id='run', feature_view='features', corpus='docs', chunk_batch_id='chunks')
        for handler in (defense.check_data_batch, defense.check_contract_checkpoint, defense.check_lineage_run, defense.check_feature_materialization, defense.check_embedding_batch):
            verdict = handler(payload, ctx)
            self.assertFalse(verdict.alert)
            self.assertEqual(verdict.reason, 'unavailable')

    def test_history_is_bounded(self):
        ctx = self.context()
        for _ in range(1000):
            defense.subtle_signals(ctx, 'a', [('age', 6, None, 12)])
        self.assertEqual(len(ctx.state['metric_history']['a']['age']), 128)


if __name__ == '__main__':
    unittest.main()
