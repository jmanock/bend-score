import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bend_score.database.repository import ListingRepository
from bend_score.intake.github_opportunities import github_signal_to_listing, github_signals_to_listings
from bend_score.observers.github import GitHubObserver, generate_github_signals, github_founder_fit_score
from bend_score.recommendations import apply_recommendation


def repo(**overrides):
    base = {
        "repo_name": "agent-tool",
        "full_name": "octo/agent-tool",
        "html_url": "https://github.com/octo/agent-tool",
        "description": "AI agent automation workflow tool",
        "language": "Python",
        "stars": 2200,
        "forks": 240,
        "open_issues": 84,
        "watchers": 2200,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
        "pushed_at": "2026-06-01T00:00:00Z",
        "license": "MIT",
        "topics": ["ai", "agent", "automation"],
        "owner": "octo",
        "archived": False,
        "homepage": "",
        "default_branch": "main",
        "query": "AI stars:>1000",
    }
    base.update(overrides)
    return base


class GitHubObserverTest(unittest.TestCase):
    def test_signal_generation_and_recommendations(self) -> None:
        signals = generate_github_signals(repo())
        signal_types = {signal.signal_type for signal in signals}
        recommendations = {signal.recommendation for signal in signals}

        self.assertIn("github_fast_growth_candidate", signal_types)
        self.assertIn("github_ai_tool", signal_types)
        self.assertIn("github_no_homepage_opportunity", signal_types)
        self.assertIn("BUILD", recommendations)
        self.assertIn("RESEARCH", recommendations)

    def test_abandoned_popular_repo_signal(self) -> None:
        signals = generate_github_signals(repo(pushed_at="2023-01-01T00:00:00Z", open_issues=140))

        self.assertIn("github_abandoned_popular_repo", {signal.signal_type for signal in signals})

    def test_observer_deduplicates_repo_across_queries(self) -> None:
        observer = GitHubObserver(token="")
        raw = [repo(query_name="ai_tools"), repo(query_name="automation")]

        signals = observer.normalize(raw)
        keys = [(signal.metadata["github_full_name"], signal.signal_type) for signal in signals]

        self.assertEqual(len(keys), len(set(keys)))

    def test_repository_deduplicates_same_day_github_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ListingRepository(Path(tmpdir) / "bend_score.sqlite3")
            repository.create_schema()
            signal = generate_github_signals(repo())[0]

            first = repository.insert_signals([signal])
            second = repository.insert_signals([signal])

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 0)

    def test_enabled_queries_from_config(self) -> None:
        config = """
github:
  enabled: true
  queries:
    ai_tools:
      enabled: true
      query: "AI stars:>1000"
    disabled_query:
      enabled: false
      query: "stars:>1"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "observers.yaml"
            path.write_text(config, encoding="utf-8")
            with patch("bend_score.observers.github.OBSERVER_CONFIG_PATH", path):
                queries = GitHubObserver(token="").enabled_queries()

        self.assertEqual(queries, {"ai_tools": "AI stars:>1000"})

    def test_empty_api_results_do_not_fail(self) -> None:
        observer = GitHubObserver(token="")
        with patch.object(observer, "_search", return_value=[]):
            with patch.object(observer, "enabled_queries", return_value={"empty": "stars:>9999999"}):
                self.assertEqual(observer.collect(), [])

    def test_github_api_response_is_parsed(self) -> None:
        api_repo = {
            "name": "agent-tool",
            "full_name": "octo/agent-tool",
            "html_url": "https://github.com/octo/agent-tool",
            "description": "AI agent automation workflow tool",
            "language": "Python",
            "stargazers_count": 2200,
            "forks_count": 240,
            "open_issues_count": 84,
            "watchers_count": 2200,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2026-06-01T00:00:00Z",
            "pushed_at": "2026-06-01T00:00:00Z",
            "license": {"spdx_id": "MIT"},
            "topics": ["ai", "agent", "automation"],
            "owner": {"login": "octo"},
            "archived": False,
            "homepage": "",
            "default_branch": "main",
        }
        observer = GitHubObserver(token="")
        with patch.object(observer, "_search", return_value=[api_repo]):
            with patch.object(observer, "enabled_queries", return_value={"ai_tools": "AI stars:>1000"}):
                collected = observer.collect()

        self.assertEqual(collected[0]["full_name"], "octo/agent-tool")
        self.assertEqual(collected[0]["stars"], 2200)
        self.assertEqual(collected[0]["matched_queries"], ["ai_tools"])

    def test_github_signal_converts_to_listing(self) -> None:
        signals = generate_github_signals(repo())

        listings = github_signals_to_listings(signals)

        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].source, "GitHub")
        self.assertIn("GitHub Opportunity", listings[0].title)

    def test_github_founder_scoring_boosts_converted_listing(self) -> None:
        listing = github_signal_to_listing(generate_github_signals(repo())[0])
        self.assertIsNotNone(listing)

        scored = apply_recommendation(listing)

        self.assertGreaterEqual(github_founder_fit_score(repo()), 80)
        self.assertGreaterEqual(scored.founder_score or 0, 70)


if __name__ == "__main__":
    unittest.main()
