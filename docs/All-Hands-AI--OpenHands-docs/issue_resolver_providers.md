# Issue Resolver: provider handlers

Sources: `openhands/resolver/interfaces/github.py`, `gitlab.py`, and `bitbucket.py`.

Provider handlers implement the shared `IssueHandlerInterface` and translate platform APIs into the normalized `Issue` and `ReviewThread` structures consumed by the service contexts.

| Provider | Issue API | PR metadata | Notable behavior |
|---|---|---|---|
| GitHub | REST issues/comments | GraphQL closing issues, reviews, unresolved review threads | Supports GitHub Enterprise through `base_domain`; can fetch referenced external issues and reply to review threads via GraphQL. |
| GitLab | REST issues/notes | REST related issues plus GraphQL discussions | Supports self-managed GitLab; filters PR notes to resolvable non-system comments. |
| Bitbucket | Basic issue/PR creation and retrieval helpers | Limited | Several download, comment, branch, and reviewer operations are explicitly unimplemented placeholders. |

```mermaid
flowchart LR
    API[Provider REST / GraphQL API] --> H[Concrete handler]
    H --> P[Pagination and filtering]
    P --> M[Issue / ReviewThread normalization]
    M --> C[ServiceContext]
    C --> R[IssueResolver]
    R --> H2[Comments, replies, PR creation]
    H2 --> API
```

## Common handler responsibilities

- Build API, clone, branch, compare, and pull-request URLs.
- Construct provider-specific authorization headers and authenticated clone URLs.
- Download paginated issues or pull/merge requests and comments.
- Filter by issue number and optional comment ID.
- Normalize missing bodies to empty strings and preserve the PR head branch.
- Create comments/PRs and, where supported, reply to review threads.
- Expand referenced issue context where the platform implementation supports it.

## Provider-specific caveats

GitHub and GitLab PR handlers include unresolved review threads only, so resolved feedback does not drive evaluation. Their metadata queries have bounded page sizes noted in source comments. Bitbucket's `download_issues()` and several comment/review methods return empty placeholders, so selecting Bitbucket may produce incomplete context or no resolvable items despite the factory supporting the platform.
