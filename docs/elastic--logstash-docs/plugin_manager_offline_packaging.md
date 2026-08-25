# Plugin Manager: Offline Packaging

`PrepareOfflinePack` requires a plugin name or wildcard, starts Bundler without build/development groups, validates a `.zip` output, and protects existing files unless `--overwrite` is set. `OfflinePluginPackager` expands patterns against installed specifications, rejects explicit core/core-plugin-api/jar-dependencies/mixin requests, and uses Paquet to collect dependencies.

Archive layout:

```text
logstash/
  <explicit-plugin>.gem
  dependencies/
    <dependency>.gem
```

Core implementation gems are ignored for compatibility, and temporary staging is removed in `ensure`. `Pack::GemInformation` classifies gems under `dependencies` as dependencies and others as plugins; Java names are parsed by their final `-java` and version components. Deprecated `Pack` packages the whole cache, while `Unpack` extracts into the cache. Current archives are installed with `install file://...`.

```mermaid
flowchart LR
 Specs[installed specs] --> Select[name/wildcard]
 Select --> Paquet[dependency closure]
 Paquet --> Stage[temp staging]
 Stage --> Split[plugins vs dependencies]
 Split --> Zip[ZIP]
 Zip --> URI[file:// install]
 URI --> Extract[extract pack]
 Extract --> Install[local Bundler install]
```

Current output must end in `.zip`; unmatched patterns raise `PluginNotFoundError`; legacy cache replacement is interactive. See [plugin_manager_pack_and_network_utilities.md](plugin_manager_pack_and_network_utilities.md) for source lookup and HTTP behavior.

