from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bend_score.config import OBSERVER_CONFIG_PATH
from bend_score.models import Signal
from bend_score.observers.base import Observer
from bend_score.utils.confidence import clamp_confidence, weighted_confidence
from bend_score.utils.config_loader import load_observer_config


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
MAX_RESULTS_PER_QUERY = 20
LOGGER = logging.getLogger("bend_score")
LOGGER.addHandler(logging.NullHandler())


class GitHubObserver(Observer):
    name = "github"
    label = "GitHub Observer"

    def __init__(self, token: str | None = None) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.errors: list[str] = []

    def collect(self) -> list[dict[str, Any]]:
        LOGGER.info("GitHub observer started")
        if self.token:
            LOGGER.info("GitHub token present")
        else:
            LOGGER.warning("GitHub token missing; using lower unauthenticated rate limits")

        repos_by_name: dict[str, dict[str, Any]] = {}
        for query_name, query in self.enabled_queries().items():
            LOGGER.info("GitHub query run name=%s query=%s", query_name, query)
            repos = self._search(query)
            LOGGER.info("GitHub repos found query=%s count=%s", query_name, len(repos))
            for repo in repos:
                full_name = repo.get("full_name")
                if not full_name:
                    continue
                normalized = _repo_metadata(repo)
                normalized["query_name"] = query_name
                normalized["query"] = query
                existing = repos_by_name.get(full_name)
                if existing:
                    queries = set(existing.get("matched_queries", []))
                    queries.add(query_name)
                    existing["matched_queries"] = sorted(queries)
                    continue
                normalized["matched_queries"] = [query_name]
                repos_by_name[full_name] = normalized

        LOGGER.info("GitHub observer repos collected count=%s", len(repos_by_name))
        return list(repos_by_name.values())

    def normalize(self, raw_items: list[dict[str, Any]]) -> list[Signal]:
        seen: set[tuple[str, str]] = set()
        signals: list[Signal] = []
        for repo in raw_items:
            for signal in generate_github_signals(repo):
                key = (signal.metadata["github_full_name"], signal.signal_type)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(signal)
        LOGGER.info("GitHub signals generated count=%s", len(signals))
        return signals

    def enabled_queries(self) -> dict[str, str]:
        config = load_observer_config(OBSERVER_CONFIG_PATH)
        github_config = config.get(self.name, {})
        queries = github_config.get("queries", {})
        enabled: dict[str, str] = {}
        if isinstance(queries, dict):
            for name, query_config in queries.items():
                if not isinstance(query_config, dict):
                    continue
                if query_config.get("enabled", False) and query_config.get("query"):
                    enabled[name] = str(query_config["query"])
        return enabled

    def _search(self, query: str) -> list[dict[str, Any]]:
        params = urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": MAX_RESULTS_PER_QUERY})
        request = Request(f"{GITHUB_SEARCH_URL}?{params}", headers=self._headers())
        try:
            with urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = f"GitHub API error {exc.code}: {exc.reason}"
            if exc.code in {401, 403}:
                message += " (check token or rate limit)"
            self.errors.append(message)
            LOGGER.warning(message)
            return []
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            message = f"GitHub API request failed: {exc}"
            self.errors.append(message)
            LOGGER.warning(message)
            return []

        if not isinstance(data, dict):
            LOGGER.warning("GitHub malformed response: expected object")
            return []
        items = data.get("items", [])
        if not isinstance(items, list):
            LOGGER.warning("GitHub malformed response: items missing")
            return []
        return [item for item in items if isinstance(item, dict)]

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "bend-score",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


def generate_github_signals(repo: dict[str, Any]) -> list[Signal]:
    signals: list[Signal] = []
    if not repo.get("full_name"):
        return signals
    if repo.get("archived") and _stars(repo) < 500:
        return [_signal(repo, "github_low_quality_repo", "Low-quality or archived repo", 35, "low", "IGNORE")]

    if _is_fast_growth_candidate(repo):
        signals.append(_fast_growth_signal(repo))
    if _is_abandoned_popular(repo):
        signals.append(_abandoned_signal(repo))
    if _has_commercial_potential(repo):
        signals.append(_commercial_signal(repo))
    if _is_developer_tool(repo):
        signals.append(_developer_tool_signal(repo))
    if _is_ai_tool(repo):
        signals.append(_ai_tool_signal(repo))
    if _is_automation_tool(repo):
        signals.append(_automation_signal(repo))
    if _is_high_issue_demand(repo):
        signals.append(_issue_demand_signal(repo))
    if _is_no_homepage_opportunity(repo):
        signals.append(_no_homepage_signal(repo))

    if not signals:
        signals.append(_signal(repo, "github_low_quality_repo", "Repo does not show a strong opportunity signal yet.", 42, "low", "IGNORE"))
    return signals


def _repo_metadata(repo: dict[str, Any]) -> dict[str, Any]:
    owner = repo.get("owner") or {}
    license_data = repo.get("license") or {}
    return {
        "repo_name": repo.get("name") or "",
        "full_name": repo.get("full_name") or "",
        "html_url": repo.get("html_url") or "",
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "stars": int(repo.get("stargazers_count") or 0),
        "forks": int(repo.get("forks_count") or 0),
        "open_issues": int(repo.get("open_issues_count") or 0),
        "watchers": int(repo.get("watchers_count") or 0),
        "created_at": repo.get("created_at") or "",
        "updated_at": repo.get("updated_at") or "",
        "pushed_at": repo.get("pushed_at") or "",
        "license": license_data.get("spdx_id") or license_data.get("name") or "",
        "topics": repo.get("topics") or [],
        "owner": owner.get("login") or "",
        "archived": bool(repo.get("archived")),
        "homepage": repo.get("homepage") or "",
        "default_branch": repo.get("default_branch") or "",
    }


def _fast_growth_signal(repo: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (_scale(_stars(repo), 1000, 10000), 2),
            (_scale(_forks(repo), 100, 2000), 1),
            (92 if _pushed_within_days(repo, 120) else 65, 2),
        ]
    )
    return _signal(
        repo,
        "github_fast_growth_candidate",
        "Popular repo with recent activity and broad developer attention.",
        confidence,
        "high" if confidence >= 80 else "medium",
        "RESEARCH" if _is_ai_tool(repo) else "WATCH",
    )


def _abandoned_signal(repo: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (_scale(_stars(repo), 1000, 15000), 2),
            (_scale(_open_issues(repo), 20, 300), 1),
            (88 if not repo.get("archived") else 50, 1),
        ]
    )
    return _signal(
        repo,
        "github_abandoned_popular_repo",
        "Popular repo appears stale but is not archived, suggesting maintenance or fork opportunity.",
        confidence,
        "high" if confidence >= 80 else "medium",
        "BUILD" if _open_issues(repo) >= 50 else "RESEARCH",
    )


def _commercial_signal(repo: dict[str, Any]) -> Signal:
    confidence = weighted_confidence(
        [
            (_scale(_stars(repo), 500, 8000), 2),
            (82 if repo.get("description") else 50, 1),
            (84 if _license_is_permissive(repo) else 65, 1),
            (88 if not repo.get("homepage") else 68, 1),
        ]
    )
    return _signal(
        repo,
        "github_commercial_potential",
        "Repo has enough adoption and utility to explore hosted docs, support, templates, or SaaS wrapper.",
        confidence,
        "high" if confidence >= 82 else "medium",
        "BUILD" if not repo.get("homepage") else "RESEARCH",
    )


def _developer_tool_signal(repo: dict[str, Any]) -> Signal:
    return _signal(
        repo,
        "github_developer_tool",
        "Repository appears to solve a developer workflow or tooling problem.",
        weighted_confidence([(_scale(_stars(repo), 300, 5000), 2), (80 if repo.get("language") else 55, 1)]),
        "medium",
        "WATCH",
    )


def _ai_tool_signal(repo: dict[str, Any]) -> Signal:
    return _signal(
        repo,
        "github_ai_tool",
        "AI-related repo may indicate a technical trend or product wedge.",
        weighted_confidence([(_scale(_stars(repo), 500, 10000), 2), (88 if _pushed_within_days(repo, 180) else 65, 1)]),
        "high",
        "RESEARCH",
    )


def _automation_signal(repo: dict[str, Any]) -> Signal:
    return _signal(
        repo,
        "github_automation_tool",
        "Automation-focused repo suggests workflow pain that may support a hosted product or service.",
        weighted_confidence([(_scale(_stars(repo), 300, 5000), 2), (82 if _open_issues(repo) > 20 else 65, 1)]),
        "medium",
        "WATCH",
    )


def _issue_demand_signal(repo: dict[str, Any]) -> Signal:
    confidence = weighted_confidence([(_scale(_open_issues(repo), 50, 500), 2), (_scale(_stars(repo), 500, 10000), 1)])
    return _signal(
        repo,
        "github_high_issue_demand",
        "High issue count suggests active user demand or a maintenance gap.",
        confidence,
        "high" if confidence >= 80 else "medium",
        "RESEARCH",
    )


def _no_homepage_signal(repo: dict[str, Any]) -> Signal:
    return _signal(
        repo,
        "github_no_homepage_opportunity",
        "Popular repo has no homepage, suggesting room for docs, hosted product, or SaaS wrapper.",
        weighted_confidence([(_scale(_stars(repo), 500, 8000), 2), (90, 1)]),
        "medium",
        "BUILD",
    )


def _signal(repo: dict[str, Any], signal_type: str, description: str, confidence: int, impact: str, recommendation: str) -> Signal:
    metadata = dict(repo)
    metadata.update(
        {
            "github_full_name": repo.get("full_name"),
            "github_html_url": repo.get("html_url"),
            "github_signal_type": signal_type,
            "recommendation_explanation": description,
        }
    )
    return Signal.create(
        observer=GitHubObserver.name,
        signal_type=signal_type,
        title=repo.get("full_name") or repo.get("repo_name") or "GitHub repository",
        description=description,
        category="GitHub",
        confidence=clamp_confidence(confidence),
        impact=impact,
        recommendation=recommendation,
        metadata=metadata,
    )


def _is_fast_growth_candidate(repo: dict[str, Any]) -> bool:
    return _stars(repo) > 1000 and _pushed_within_days(repo, 180) and (_forks(repo) > 100 or _watchers(repo) > 1000)


def _is_abandoned_popular(repo: dict[str, Any]) -> bool:
    return _stars(repo) > 1000 and not repo.get("archived") and not _pushed_within_days(repo, 365)


def _has_commercial_potential(repo: dict[str, Any]) -> bool:
    return _stars(repo) > 500 and bool(repo.get("description")) and not repo.get("archived")


def _is_developer_tool(repo: dict[str, Any]) -> bool:
    return _contains(repo, ["cli", "sdk", "framework", "library", "tool", "developer", "api", "testing", "database"])


def _is_ai_tool(repo: dict[str, Any]) -> bool:
    return _contains(repo, ["ai", "llm", "agent", "rag", "mcp", "model", "automation", "workflow", "gpt"])


def _is_automation_tool(repo: dict[str, Any]) -> bool:
    return _contains(repo, ["automation", "scripts", "workflow", "scraping", "bot", "monitoring", "agent", "scheduler"])


def _is_high_issue_demand(repo: dict[str, Any]) -> bool:
    return _open_issues(repo) > 50 and _stars(repo) > 500


def _is_no_homepage_opportunity(repo: dict[str, Any]) -> bool:
    return _stars(repo) > 500 and not repo.get("homepage")


def _contains(repo: dict[str, Any], needles: list[str]) -> bool:
    text = " ".join(
        [
            str(repo.get("full_name") or ""),
            str(repo.get("description") or ""),
            str(repo.get("query") or ""),
            " ".join(str(topic) for topic in repo.get("topics", [])),
        ]
    ).lower()
    return any(needle in text for needle in needles)


def _license_is_permissive(repo: dict[str, Any]) -> bool:
    return str(repo.get("license") or "").upper() in {"MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC"}


def _pushed_within_days(repo: dict[str, Any], days: int) -> bool:
    pushed = _parse_datetime(repo.get("pushed_at"))
    if not pushed:
        return False
    age = datetime.now(timezone.utc) - pushed
    return age.days <= days


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _scale(value: int, low: int, high: int) -> int:
    if value <= low:
        return 55
    if value >= high:
        return 95
    return int(55 + ((value - low) / (high - low)) * 40)


def _stars(repo: dict[str, Any]) -> int:
    return int(repo.get("stars") or 0)


def _forks(repo: dict[str, Any]) -> int:
    return int(repo.get("forks") or 0)


def _watchers(repo: dict[str, Any]) -> int:
    return int(repo.get("watchers") or 0)


def _open_issues(repo: dict[str, Any]) -> int:
    return int(repo.get("open_issues") or 0)
