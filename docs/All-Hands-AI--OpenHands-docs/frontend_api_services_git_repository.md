# Frontend API Services: Git and Repository Discovery

`GitService` adapts provider-backed repository APIs for repository selectors, branch selectors, and microagent management screens.

## Responsibilities

- Search repositories with optional provider and page-size filters.
- Retrieve a user's repositories and traverse provider installation repositories.
- Retrieve or search repository branches.
- List repository microagents and retrieve a microagent's content.
- Retrieve provider installation IDs.

```mermaid
flowchart LR
    Selector[Repository/branch selector] --> GS[GitService]
    GS --> Repo[/api/user/repositories\nsearch/repositories]
    GS --> Branch[/api/user/repository/branches\nsearch/branches]
    GS --> Install[/api/user/installations]
    GS --> Micro[/api/user/repository/{owner}/{repo}/microagents]
    Repo --> Page[extractNextPageFromLink]
    Page --> Selector
```

`retrieveUserGitRepositories()` derives `nextPage` from the first result's `link_header`. `retrieveInstallationRepositories()` continues the current installation when a next page exists; otherwise it advances to the next installation and eventually returns `null`.

The service returns shared `GitRepository`, `Branch`, `PaginatedBranchesResponse`, and `RepositoryMicroagent` types. Repository microagent content uses the shared `MicroagentContentResponse` contract from the OpenHands API types.
