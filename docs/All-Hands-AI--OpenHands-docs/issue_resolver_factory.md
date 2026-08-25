# Issue Resolver: handler factory

Source: `openhands/resolver/issue_handler_factory.py` (`IssueHandlerFactory`).

The factory isolates provider selection from orchestration. It receives repository identity, credentials, provider type, domain, issue mode, and `LLMConfig`, then returns a service context around a concrete handler.

```mermaid
flowchart TD
    F[IssueHandlerFactory.create] --> T{issue_type}
    T -->|issue| I[ServiceContextIssue]
    T -->|pr| P[ServiceContextPR]
    I --> PI{platform}
    P --> PP{platform}
    PI --> GH1[GithubIssueHandler]
    PI --> GL1[GitlabIssueHandler]
    PI --> BB1[BitbucketIssueHandler]
    PP --> GH2[GithubPRHandler]
    PP --> GL2[GitlabPRHandler]
    PP --> BB2[BitbucketPRHandler]
```

Each branch constructs the handler with owner, repository, token, username, and base domain. Issue contexts and PR contexts expose the common operations needed by `IssueResolver`; the PR context additionally evaluates review feedback.

Invalid issue types and unsupported platforms raise `ValueError`. This makes provider support explicit and prevents the resolver from running with a partially configured handler.
