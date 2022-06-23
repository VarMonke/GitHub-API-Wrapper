from __future__ import annotations

import asyncio
import logging
import platform
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Awaitable, Dict, List, Literal, NamedTuple, Optional, Tuple, Union

from aiohttp import ClientSession, TraceConfig

from github.utils import human_readable_time_until

from .. import __version__
from ..errors import HTTPError

if TYPE_CHECKING:
    from types import SimpleNamespace

    from aiohttp import BasicAuth, TraceRequestEndParams
    from typing_extensions import Self

    from ..types import SecurtiyAndAnalysis

__all__: Tuple[str, ...] = ("HTTPClient",)

log = logging.getLogger("github")


class Ratelimit(NamedTuple):
    remaining: Optional[int]
    used: Optional[int]
    total: Optional[int]
    reset_time: Optional[datetime]
    last_request: Optional[datetime]


class HTTPClient:
    def __new__(
        cls,
        *,
        headers: Optional[Dict[str, Union[str, int]]] = None,
        auth: Optional[BasicAuth] = None,
    ) -> Awaitable[HTTPClient]:
        async def init() -> HTTPClient:
            self = super(HTTPClient, cls).__new__(cls)

            nonlocal headers
            if not headers:
                headers = {}

            headers.setdefault(
                "User-Agent",
                "GitHub-API-Wrapper (https://github.com/VarMonke/Github-Api-Wrapper) @"
                f" {__version__} CPython/{platform.python_version()} aiohttp/{__version__}",
            )

            self._rates = Ratelimit(None, None, None, None, None)
            self.__headers = headers
            self.__auth = auth

            self._last_ping = 0
            self._latency = 0

            trace_config = TraceConfig()

            @trace_config.on_request_start.append
            async def on_request_start(_: ClientSession, __: SimpleNamespace, params: TraceRequestEndParams) -> None:
                if (remaining := self._rates.remaining) is not None and int(remaining) < 2:
                    dt = self._rates.reset_time
                    log.info(
                        "Ratelimit exceeded, trying again in"
                        f" {human_readable_time_until(self._rates.reset_time - datetime.now(timezone.utc))} (URL: {params.url},"  # type: ignore
                        f" method: {params.method})"
                    )

                    # TODO: I get about 3-4 hours of cooldown this might not be a good idea, might make this raise an error instead.
                    now = datetime.now(timezone.utc)
                    await asyncio.sleep(max((dt - now).total_seconds(), 0))

            @trace_config.on_request_end.append
            async def on_request_end(_: ClientSession, __: SimpleNamespace, params: TraceRequestEndParams) -> None:
                """After-request hook to adjust remaining requests on this time frame."""
                headers = params.response.headers

                self._rates = Ratelimit(
                    int(headers["X-RateLimit-Remaining"]),
                    int(headers["X-RateLimit-Used"]),
                    int(headers["X-RateLimit-Limit"]),
                    datetime.fromtimestamp(int(headers["X-RateLimit-Reset"])).replace(tzinfo=timezone.utc),
                    datetime.now(timezone.utc),
                )
                print(repr(self._rates))

            self.__session = ClientSession(
                headers=headers,
                auth=auth,
                trace_configs=[trace_config],
            )

            return self

        return init()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_) -> None:
        await self.__session.close()

    def data(self):
        # TODO: is this needed?
        # Returns session headers and auth.
        return {"headers": dict(self.__session.headers), "auth": self.__auth}

    async def latency(self) -> float:
        last_ping = self._last_ping

        # If there was no ping or the last ping was more than 5 seconds ago.
        if not last_ping or int(time.time()) > last_ping + 5:
            start = time.monotonic()
            await self._request("GET")
            self._latency = time.monotonic() - start

        return self._latency

    async def _request(self, method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"], url: str = "", /, **kwargs):
        initialized = getattr(self, "_HTTPClient__session", False)
        if not initialized:
            raise ValueError("Client isnt initialized yet. Await the class before making HTTP requests.")

        async with self.__session.request(method, f"https://api.github.com/{url.removeprefix('/')}", **kwargs) as request:
            if 200 <= request.status <= 299:
                return await request.json()

            raise HTTPError(request)

    # === ROUTES === #

    # Users

    async def get_self(self):
        return await self._request("GET", "user")

    async def update_self(
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

        return await self._request("PATCH", "user", json=data)

    async def list_users(self, *, since: Optional[int] = None, per_page: Optional[int] = None):
        data = {}

        if since:
            data["since"] = since
        if per_page:
            data["per_page"] = per_page

        return await self._request("GET", "users", json=data)

    async def get_user(self, *, username: str):
        return await self._request("GET", f"users/{username}")

    # TODO: /users/{username}/hovercard
    # idk what to name it

    # Repos

    async def list_org_repos(
        self,
        *,
        org: str,
        type: Optional[Literal["all", "public", "private", "forks", "sources", "member", "internal"]] = None,
        sort: Optional[Literal["created", "updated", "pushed", "full_name"]] = None,
        direction: Optional[Literal["asc", "desc"]] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        data = {}

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

        return await self._request("GET", f"orgs/{org}/repos", json=data)

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
        data = {
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

        return await self._request("POST", f"orgs/{org}/repos", json=data)

    async def get_repo(self, *, owner: str, repo: str):
        return await self._request("GET", f"repos/{owner}/{repo}")

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

        return await self._request("PATCH", f"repos/{owner}/{repo}")

    async def delete_repo(self, *, owner: str, repo: str):
        return await self._request("DELETE", f"repos/{owner}/{repo}")

    async def enable_repo_automated_security_fixes(self, *, owner: str, repo: str):
        return await self._request("PUT", f"repos/{owner}/{repo}/automated-security-fixes")

    async def disable_repo_automated_security_fixes(self, *, owner: str, repo: str):
        return await self._request("DELETE", f"repos/{owner}/{repo}/automated-security-fixes")

    async def list_repo_codeowners_erros(self, *, owner: str, repo: str, ref: Optional[str] = None):
        params = {}

        if ref:
            params["ref"] = ref

        return await self._request("GET", f"repos/{owner}/{repo}/codeowners/errors", params=params)

    async def list_repo_contributors(
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

        return await self._request("GET", f"repos/{owner}/{repo}/contributors", params=params)

    async def create_repo_dispatch_event(
        self, *, owner: str, repo: str, event_name: str, client_payload: Optional[str] = None
    ):
        data = {
            "event_name": event_name,
        }

        if client_payload:
            data["client_payload"] = client_payload

        return await self._request("POST", f"repos/{owner}/{repo}/dispatches", json=data)

    async def list_repo_languages(self, *, owner: str, repo: str):
        return await self._request("GET", f"repos/{owner}/{repo}/languages")

    async def list_repo_tags(self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self._request("GET", f"repos/{owner}/{repo}/tags", params=params)

    async def list_repo_teams(self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self._request("GET", f"repos/{owner}/{repo}/teams", params=params)

    async def get_all_repo_topic(self, *, owner: str, repo: str, per_page: Optional[int] = None, page: Optional[int] = None):
        params = {}

        if per_page:
            params["per_page"] = per_page
        if page:
            params["page"] = page

        return await self._request("GET", f"repos/{owner}/{repo}/topics", params=params)

    async def replace_all_repo_topics(self, *, owner: str, repo: str, names: List[str]):
        return await self._request("PUT", f"repos/{owner}/{repo}/topics", json={"names": names})

    async def transfer_repo(self, *, owner: str, repo: str, new_owner: str, team_ids: Optional[List[int]] = None):
        data = {
            "new_owner": new_owner,
        }

        if team_ids:
            data["team_ids"] = team_ids

        return await self._request("POST", f"repos/{owner}/{repo}/transfer", json=data)

    async def check_repo_vulnerability_alerts_enabled(self, *, owner: str, repo: str):
        return await self._request("GET", f"repos/{owner}/{repo}/vulnerability-alerts")

    async def enable_repo_vulnerability_alerts(self, *, owner: str, repo: str):
        return await self._request("PUT", f"repos/{owner}/{repo}/vulnerability-alerts")

    async def disable_repo_vulnerability_alerts(self, *, owner: str, repo: str):
        return await self._request("DELETE", f"repos/{owner}/{repo}/vulnerability-alerts")

    async def create_repo_using_template(
        self,
        *,
        template_owner: str,
        template_repo: str,
        owner: Optional[str] = None,
        name: str,
        include_all_branches: Optional[bool] = None,
        private: Optional[bool] = None,
    ):
        data = {
            "name": str,
        }

        if owner:
            data["owner"] = owner
        if include_all_branches:
            data["include_all_branches"] = include_all_branches
        if private:
            data["private"] = private

        return await self._request("POST", f"repos/{template_owner}/{template_repo}/generate", json=data)

    async def list_public_repos(self, *, since: Optional[int] = None):
        return await self._request("GET", "repositories", params={"since": since})

    async def list_self_repos(
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

        return self._request("POST", "user/repos", json=data)

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
        data = {
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

        return await self._request("POST", "user/repos", json=data)

    async def list_user_repos(
        self,
        *,
        username: str,
        type: Optional[Literal["all", "public", "private", "forks", "sources", "member", "internal"]] = None,
        sort: Optional[Literal["created", "updated", "pushed", "full_name"]] = None,
        direction: Optional[Literal["asc", "desc"]] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ):
        data = {}

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

        return await self._request("GET", f"users/{username}/repos", json=data)
