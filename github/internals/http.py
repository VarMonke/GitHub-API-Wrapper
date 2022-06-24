from __future__ import annotations

__all__ = ("HTTPClient",)

import asyncio
import logging
import platform
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Dict, List, Literal, NamedTuple, Optional, Union

from aiohttp import ClientSession, TraceConfig

from .. import __version__
from ..utils import error_from_request, human_readable_time_until

if TYPE_CHECKING:
    from types import SimpleNamespace

    from aiohttp import BasicAuth, TraceRequestEndParams, TraceRequestStartParams
    from typing_extensions import Self

    from ..objects import File
    from ..types import SecurtiyAndAnalysis

log = logging.getLogger("github")


class Ratelimits(NamedTuple):
    remaining: Optional[int]
    used: Optional[int]
    total: Optional[int]
    reset_time: Optional[datetime]
    last_request: Optional[datetime]


# ========= TODO ========= #
# Make a good paginator
# Make objects for all API Types
# Make the requests return TypedDicts with those objects
# Make specific errrors
# Make route /users/{username}/hovercard
# Make it so an error gets raised when the cooldown is reached

# === ROUTES CHECKLIST === #
# Actions
# Activity
# Apps
# Billing
# Branches
# Checks
# Codes of conduct
# Code Scanning
# Codespaces
# Collaborators
# Commits
# Dependabot
# Dependency Graph
# Deploy keys
# Deployments
# Emojis
# Enterprise administration
# Gists                      DONE
# Git database
# Gitignore
# Interactions
# Issues
# Licenses
# Markdown
# Meta
# Metrics
# Migrations
# OAuth authorizations
# Organizations
# Packages
# Pages
# Projects
# Pulls
# Rate limit
# Reactions
# Releases
# Repositories               DONE
# SCIM
# Search
# Teams
# Users                      DONE
# Webhooks


class HTTPClient:
    __session: ClientSession
    _rates: Ratelimits
    _last_ping: float
    _latency: float

    def __new__(
        cls,
        *,
        headers: Optional[Dict[str, Union[str, int]]] = None,
        auth: Optional[BasicAuth] = None,
    ) -> Awaitable[Self]:
        # Basically async def __init__
        return cls.__async_init()

    @classmethod
    async def __async_init(
        cls,
        *,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[BasicAuth] = None,
    ) -> Self:
        self = super(cls, cls).__new__(cls)

        if not headers:
            headers = {}

        headers.setdefault(
            "User-Agent",
            "GitHub-API-Wrapper (https://github.com/Varmonke/GitHub-API-Wrapper) @"
            f" {__version__} CPython/{platform.python_version()} aiohttp/{__version__}",
        )

        self._rates = Ratelimits(None, None, None, None, None)
        self.__headers = headers
        self.__auth = auth

        self._last_ping = 0
        self._latency = 0

        trace_config = TraceConfig()

        @trace_config.on_request_start.append
        async def on_request_start(
            _: ClientSession, __: SimpleNamespace, params: TraceRequestStartParams
        ) -> None:
            if self.ratelimited:
                log.info(
                    "Ratelimit exceeded, trying again in"
                    f" {human_readable_time_until(self._rates.reset_time - datetime.now(timezone.utc))} (URL:"
                    f" {params.url}, method: {params.method})"
                )

                # TODO: I get about 3-4 hours of cooldown this might not be a good idea, might make this raise an error instead.
                await asyncio.sleep(
                    max((self._rates.reset_time - datetime.now(timezone.utc)).total_seconds(), 0)
                )

        @trace_config.on_request_end.append
        async def on_request_end(
            _: ClientSession, __: SimpleNamespace, params: TraceRequestEndParams
        ) -> None:
            """After-request hook to adjust remaining requests on this time frame."""
            headers = params.response.headers

            self._rates = Ratelimits(
                int(headers["X-RateLimit-Remaining"]),
                int(headers["X-RateLimit-Used"]),
                int(headers["X-RateLimit-Limit"]),
                datetime.fromtimestamp(int(headers["X-RateLimit-Reset"])).replace(
                    tzinfo=timezone.utc
                ),
                datetime.now(timezone.utc),
            )

        self.__session = ClientSession(
            headers=headers,
            auth=auth,
            trace_configs=[trace_config],
        )

        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_) -> None:
        await self.__session.close()

    @property
    def ratelimited(self) -> bool:
        remaining = self._rates.remaining
        return remaining is not None and remaining < 2

    @property
    def latency(self) -> Awaitable[float]:
        async def inner() -> float:
            last_ping = self._last_ping

            # If there was no ping or the last ping was more than 5 seconds ago.
            if not last_ping or time.monotonic() > last_ping + 5 or self.ratelimited:
                self._last_ping = time.monotonic()

                start = time.monotonic()
                await self.request("GET", "/")
                self._latency = time.monotonic() - start

            return self._latency

        return inner()

    async def request(
        self, method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"], path: str, /, **kwargs: Any
    ):
        async with self.__session.request(
            method, f"https://api.github.com{path}", **kwargs
        ) as request:
            if 200 <= request.status <= 299:
                return await request.json()

            raise error_from_request(request)

    # === ROUTES === #

    # === USERS === #

    async def get_logged_in_user(self):
        return await self.request("GET", "/user")

    async def update_logged_in_user(
        self,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        blog: Optional[str] = None,
        twitter_username: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        hireable: Optional[str] = None,
        bio: Optional[str] = None,
    ):
        data = {}

        if name:
            data["name"] = name
        if email:
            data["email"] = email
        if blog:
            data["blog"] = blog
        if twitter_username:
            data["twitter_username"] = twitter_username
        if company:
            data["company"] = company
        if location:
            data["location"] = location
        if hireable:
            data["hireable"] = hireable
        if bio:
            data["bio"] = bio

        return await self.request("PATCH", "/user", json=data)

    async def list_users(self, *, since: Optional[int] = None, per_page: Optional[int] = None):
        params = {}

        if since:
            params["since"] = since
        if per_page:
            params["per_page"] = per_page

        return await self.request("GET", "/users", params=params)

    async def get_user(self, *, username: str):
        return await self.request("GET", f"/users/{username}")

    # TODO: /users/{username}/hovercard
    # IDK what to name it

    # === REPOS === #

    async def list_org_repos(
        self,
        *,
        org: str,
        type: Optional[
            Literal["all", "public", "private", "forks", "sources", "member", "internal"]
        ] = None,
        sort: Optional[Literal["created", "updated", "pushed", "full_name"]] = None,
        direction: Optional[Literal["asc", "desc"]] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if type:
            params["type"] = type
        if sort:
            params["sort"] = sort
        if direction:
            params["direction"] = direction
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/orgs/{org}/repos", params=params)

    async def create_org_repo(
        self,
        *,
        org: str,
        name: str,
        description: Optional[str] = None,
        homepage: Optional[str] = None,
        private: Optional[bool] = None,
        visibility: Optional[Literal["public", "private", "internal"]] = None,
        has_issues: Optional[bool] = None,
        has_projects: Optional[bool] = None,
        has_wiki: Optional[bool] = None,
        is_template: Optional[bool] = None,
        team_id: Optional[int] = None,
        auto_init: Optional[bool] = None,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None,
        allow_squash_merge: Optional[bool] = None,
        allow_merge_commit: Optional[bool] = None,
        allow_rebase_merge: Optional[bool] = None,
        allow_auto_merge: Optional[bool] = None,
        delete_branch_on_merge: Optional[bool] = None,
        use_squash_pr_title_as_default: Optional[bool] = None,
    ):
        data: Dict[str, Union[str, bool, int]] = {
            "name": name,
        }

        if description:
            data["description"] = description
        if homepage:
            data["homepage"] = homepage
        if private:
            data["private"] = private
        if visibility:
            data["visibility"] = visibility
        if has_issues:
            data["has_issues"] = has_issues
        if has_projects:
            data["has_projects"] = has_projects
        if has_wiki:
            data["has_wiki"] = has_wiki
        if is_template:
            data["is_template"] = is_template
        if team_id:
            data["team_id"] = team_id
        if auto_init:
            data["auto_init"] = auto_init
        if gitignore_template:
            data["gitignore_template"] = gitignore_template
        if license_template:
            data["license_template"] = license_template
        if allow_squash_merge:
            data["allow_squash_merge"] = allow_squash_merge
        if allow_merge_commit:
            data["allow_merge_commit"] = allow_merge_commit
        if allow_rebase_merge:
            data["allow_rebase_merge "] = allow_rebase_merge
        if allow_auto_merge:
            data["allow_auto_merge"] = allow_auto_merge
        if delete_branch_on_merge:
            data["delete_branch_on_merge"] = delete_branch_on_merge
        if use_squash_pr_title_as_default:
            data["use_squash_pr_title_as_default"] = use_squash_pr_title_as_default

        return await self.request("POST", f"/orgs/{org}/repos", json=data)

    async def get_repo(self, *, owner: str, repo: str):
        return await self.request("GET", f"/repos/{owner}/{repo}")

    async def update_repo(
        self,
        *,
        owner: str,
        repo: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        homepage: Optional[str] = None,
        private: Optional[bool] = None,
        visibility: Optional[Literal["public", "private", "internal"]] = None,
        security_and_analysis: Optional[SecurtiyAndAnalysis] = None,
        has_issues: Optional[bool] = None,
        has_projects: Optional[bool] = None,
        has_wiki: Optional[bool] = None,
        is_template: Optional[bool] = None,
        default_branch: Optional[str] = None,
        allow_squash_merge: Optional[bool] = None,
        allow_merge_commit: Optional[bool] = None,
        allow_rebase_merge: Optional[bool] = None,
        allow_auto_merge: Optional[bool] = None,
        delete_branch_on_merge: Optional[bool] = None,
        use_squash_pr_title_as_default: Optional[bool] = None,
        archived: Optional[bool] = None,
        allow_forking: Optional[bool] = None,
    ):
        data = {}

        if name:
            data["name"] = name
        if description:
            data["description"] = description
        if homepage:
            data["homepage"] = homepage
        if private:
            data["private"] = private
        if visibility:
            data["visibility"] = visibility
        if security_and_analysis:
            data["security_and_analysis"] = security_and_analysis
        if has_issues:
            data["has_issues"] = has_issues
        if has_projects:
            data["has_projects"] = has_projects
        if has_wiki:
            data["has_wiki"] = has_wiki
        if is_template:
            data["is_template"] = is_template
        if default_branch:
            data["default_branch"] = default_branch
        if allow_squash_merge:
            data["allow_squash_merge"] = allow_squash_merge
        if allow_merge_commit:
            data["allow_merge_commit"] = allow_merge_commit
        if allow_rebase_merge:
            data["allow_rebase_merge "] = allow_rebase_merge
        if allow_auto_merge:
            data["allow_auto_merge "] = allow_auto_merge
        if delete_branch_on_merge:
            data["delete_branch_on_merge "] = delete_branch_on_merge
        if use_squash_pr_title_as_default:
            data["use_squash_pr_title_as_default"] = use_squash_pr_title_as_default
        if archived:
            data["archived"] = archived
        if allow_forking:
            data["allow_forking"] = allow_forking

        return await self.request("PATCH", f"/repos/{owner}/{repo}", json=data)

    async def delete_repo(self, *, owner: str, repo: str):
        return await self.request("DELETE", f"/repos/{owner}/{repo}")

    async def enable_automated_security_fixes_for_repo(self, *, owner: str, repo: str):
        return await self.request("PUT", f"/repos/{owner}/{repo}/automated-security-fixes")

    async def disable_automated_security_fixes_for_repo(self, *, owner: str, repo: str):
        return await self.request("DELETE", f"/repos/{owner}/{repo}/automated-security-fixes")

    async def list_codeowners_erros_for_repo(
        self, *, owner: str, repo: str, ref: Optional[str] = None
    ):
        params = {}

        if ref:
            params["ref"] = ref

        return await self.request("GET", f"/repos/{owner}/{repo}/codeowners/errors", params=params)

    async def list_contributors_for_repo(
        self,
        *,
        owner: str,
        repo: str,
        anon: Optional[bool] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if anon:
            params["anon"] = anon
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/repos/{owner}/{repo}/contributors", params=params)

    async def create_dispatch_event_for_repo(
        self, *, owner: str, repo: str, event_name: str, client_payload: Optional[str] = None
    ):
        data = {
            "event_name": event_name,
        }

        if client_payload:
            data["client_payload"] = client_payload

        return await self.request("POST", f"/repos/{owner}/{repo}/dispatches", json=data)

    async def list_repo_languages_for_repo(self, *, owner: str, repo: str):
        return await self.request("GET", f"/repos/{owner}/{repo}/languages")

    async def list_tags_for_repo(
        self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None
    ):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/repos/{owner}/{repo}/tags", params=params)

    async def list_teams_for_repo(
        self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None
    ):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/repos/{owner}/{repo}/teams", params=params)

    async def get_all_topic_for_repo(
        self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None
    ):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/repos/{owner}/{repo}/topics", params=params)

    async def replace_all_topics_for_repo(self, *, owner: str, repo: str, names: List[str]):
        return await self.request("PUT", f"/repos/{owner}/{repo}/topics", json={"names": names})

    async def transfer_repo(
        self, *, owner: str, repo: str, new_owner: str, team_ids: Optional[List[int]] = None
    ):
        data: Dict[str, Union[str, List[int]]] = {
            "new_owner": new_owner,
        }

        if team_ids:
            data["team_ids"] = team_ids

        return await self.request("POST", f"/repos/{owner}/{repo}/transfer", json=data)

    async def check_vulnerability_alerts_enabled_for_repo(self, *, owner: str, repo: str):
        return await self.request("GET", f"/repos/{owner}/{repo}/vulnerability-alerts")

    async def enable_vulnerability_alerts_for_repo(self, *, owner: str, repo: str):
        return await self.request("PUT", f"/repos/{owner}/{repo}/vulnerability-alerts")

    async def disable_vulnerability_alerts_for_repo(self, *, owner: str, repo: str):
        return await self.request("DELETE", f"/repos/{owner}/{repo}/vulnerability-alerts")

    async def create_repo_using_template_repo(
        self,
        *,
        template_owner: str,
        template_repo: str,
        owner: Optional[str] = None,
        name: str,
        include_all_branches: Optional[bool] = None,
        private: Optional[bool] = None,
    ):
        data: Dict[str, Union[str, bool]] = {
            "name": name,
        }

        if owner:
            data["owner"] = owner
        if include_all_branches:
            data["include_all_branches"] = include_all_branches
        if private:
            data["private"] = private

        return await self.request(
            "POST", f"/repos/{template_owner}/{template_repo}/generate", json=data
        )

    async def list_public_repos(self, *, since: Optional[int] = None):
        params = {}

        if since:
            params["since"] = since

        return await self.request("GET", "/repositories", params=params)

    async def list_logged_in_user_repos(
        self,
        *,
        visibility: Optional[Literal["all", "private", "public"]] = None,
        affiliation: Optional[Literal["owner", "collaborator", "organization_member"]] = None,
        type: Optional[Literal["all", "owner", "public", "private", "member"]] = None,
        sort: Optional[Literal["created", "updated", "pushed", "full_name"]] = None,
        direction: Optional[Literal["asc", "desc"]] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
        since: Optional[str] = None,
        before: Optional[str] = None,
    ):
        data = {}

        if visibility:
            data["visibility"] = visibility
        if affiliation:
            data["affiliation"] = affiliation
        if type:
            data["type"] = type
        if sort:
            data["sort"] = sort
        if direction:
            data["direction"] = direction
        if per_page:
            data["per_page"] = per_page
        if page:
            data["page"] = page
        if since:
            data["since"] = since
        if before:
            data["before"] = before

        return self.request("POST", "/user/repos", json=data)

    async def create_repo(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        homepage: Optional[str] = None,
        private: Optional[bool] = None,
        has_issues: Optional[bool] = None,
        has_projects: Optional[bool] = None,
        has_wiki: Optional[bool] = None,
        team_id: Optional[int] = None,
        auto_init: Optional[bool] = None,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None,
        allow_squash_merge: Optional[bool] = None,
        allow_merge_commit: Optional[bool] = None,
        allow_rebase_merge: Optional[bool] = None,
        allow_auto_merge: Optional[bool] = None,
        delete_branch_on_merge: Optional[bool] = None,
        has_downloads: Optional[bool] = None,
        is_template: Optional[bool] = None,
    ):
        data: Dict[str, Union[str, bool, int]] = {
            "name": name,
        }

        if description:
            data["description"] = description
        if homepage:
            data["homepage"] = homepage
        if private:
            data["private"] = private
        if has_issues:
            data["has_issues"] = has_issues
        if has_projects:
            data["has_projects"] = has_projects
        if has_wiki:
            data["has_wiki"] = has_wiki
        if team_id:
            data["team_id"] = team_id
        if auto_init:
            data["auto_init"] = auto_init
        if gitignore_template:
            data["gitignore_template"] = gitignore_template
        if license_template:
            data["license_template"] = license_template
        if allow_squash_merge:
            data["allow_squash_merge"] = allow_squash_merge
        if allow_merge_commit:
            data["allow_merge_commit"] = allow_merge_commit
        if allow_rebase_merge:
            data["allow_rebase_merge"] = allow_rebase_merge
        if allow_auto_merge:
            data["allow_auto_merge"] = allow_auto_merge
        if delete_branch_on_merge:
            data["delete_branch_on_merge"] = delete_branch_on_merge
        if has_downloads:
            data["has_downloads"] = has_downloads
        if is_template:
            data["is_template"] = is_template

        return await self.request("POST", "/user/repos", json=data)

    async def list_user_repos(
        self,
        *,
        username: str,
        type: Optional[
            Literal["all", "public", "private", "forks", "sources", "member", "internal"]
        ] = None,
        sort: Optional[Literal["created", "updated", "pushed", "full_name"]] = None,
        direction: Optional[Literal["asc", "desc"]] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if type:
            params["type"] = type
        if sort:
            params["sort"] = sort
        if direction:
            params["direction"] = direction
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/users/{username}/repos", params=params)

    # === GISTS === #

    async def list_logged_in_user_gists(
        self,
        *,
        since: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if since:
            params["since"] = since
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", "/gists", params=params)

    async def create_gist(
        self, *, description: Optional[str] = None, files: List[File], public: Optional[bool] = None
    ):
        data: Dict[str, Union[str, bool, Dict[str, str]]] = {
            "files": {f.name: f.read() for f in files},
        }

        if description:
            data["description"] = description
        if public:
            data["public"] = public

        return await self.request("POST", "/gists", json=data)

    async def list_public_gists(
        self,
        *,
        since: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if since:
            params["since"] = since
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", "/gists/public", params=params)

    async def list_starred_gists(
        self,
        *,
        since: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if since:
            params["since"] = since
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", "/gists/starred", params=params)

    async def get_gist(self, *, gist_id: str):
        return await self.request("GET", f"/gists/{gist_id}")

    async def update_gist(
        self, *, gist_id: str, description: Optional[str] = None, files: Optional[List[File]] = None
    ):
        data = {}

        if description:
            data["description"] = description
        if files:
            data["files"] = {f.name: f.read() for f in files}

        return await self.request("PATCH", f"/gists/{gist_id}")

    async def delete_gist(self, *, gist_id: str):
        return await self.request("DELETE", f"/gists/{gist_id}")

    async def list_commits_for_gist(
        self, *, gist_id: str, per_page: Optional[int] = None, page: Optional[int] = None
    ):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/gists/{gist_id}/commits", params=params)

    async def list_forks_for_gist(
        self, *, gist_id: str, per_page: Optional[int] = None, page: Optional[int] = None
    ):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/gists/{gist_id}/forks", params=params)

    async def fork_gist(self, *, gist_id: str):
        return await self.request("POST", f"/gists/{gist_id}/forks")

    async def check_starred_for_gist(self, *, gist_id: str):
        return await self.request("GET", f"/gists/{gist_id}/star")

    async def star_gist(self, *, gist_id: str):
        return await self.request("PUT", f"/gists/{gist_id}/star")

    async def unstar_gist(self, *, gist_id: str):
        return await self.request("DELETE", f"/gists/{gist_id}/star")

    async def get_revision_for_gist(self, *, gist_id: str, sha: str):
        return await self.request("GET", f"/gists/{gist_id}/{sha}")

    async def list_user_gists(
        self,
        *,
        username: str,
        since: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        params = {}

        if since:
            params["since"] = since
        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self.request("GET", f"/users/{username}/gists", params=params)
