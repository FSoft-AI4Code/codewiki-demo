# Frontend API Services: User and Options

This sub-module groups read-only services that populate global frontend context: the current Git identity, server capabilities, and suggested tasks.

## Components

- `UserService.getUser()` calls `/api/user/info` and normalizes the response to the frontend `GitUser` shape. The explicit mapping prevents unrelated backend fields from leaking into UI state.
- `OptionService.getModels()` retrieves available models.
- `OptionService.getAgents()` retrieves available agent names.
- `OptionService.getSecurityAnalyzers()` retrieves available security analyzer names.
- `OptionService.getConfig()` retrieves `GetConfigResponse`, including the application mode consumed by `AuthService`.
- `SuggestionsService.getSuggestedTasks()` retrieves `/api/user/suggested-tasks` for task-start UI.

```mermaid
graph LR
    Bootstrap[Frontend bootstrap/settings] --> Options[OptionService]
    Options --> Models[models, agents, analyzers, config]
    Auth[AuthService] -->|APP_MODE| Options
    Profile[User/profile UI] --> User[UserService]
    User --> GitUser[GitUser]
    Home[Task-start UI] --> Suggestions[SuggestionsService]
    Suggestions --> Tasks[SuggestedTask[]]
```

These methods return backend data or a normalized user object and do not maintain caches themselves; caching and retry behavior belong to their query/state consumers.
