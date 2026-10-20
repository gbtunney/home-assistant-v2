# Home Assistant Repository Workflow

## Branch roles

### main
The intended current production Home Assistant configuration.

Code on `main` should represent the configuration that is intended to be
running in Home Assistant.

### feat/<name>
Active work intended to become part of the normal Home Assistant configuration.

Examples:
- feat/notification-dispatcher
- feat/reptile-schedules

A feature branch should eventually graduate into `main` or be archived.

### device/<device>/<name>
Work specific to a particular physical device or device family.

Examples:
- device/cyd/panel
- device/rfid/reader

Use this when experimental hardware configuration should not be confused with
the production Home Assistant configuration.

### experiment/<name>
Exploratory work where the implementation or even the idea may be discarded.

Experiments do not imply that the configuration is production-ready.

### recovery/<date-or-reason>
Safety checkpoints created before potentially disruptive repository work.

Recovery branches are preservation points and should not be used for normal
development.

### archive/<name>
Historical work retained for reference but no longer actively developed.

## Current branch classification

- recovery/current-ha-2026-10-10
  Current preserved Home Assistant state while repository cleanup is performed.

- feat/issuequeue
  Misleading historical name. This became the main post-March 2026 Home
  Assistant development lineage and is not specifically an issue-queue feature.

- feat/cyd-examples
  CYD experiment containing a failed-update path. Preserve as experimental
  history until CYD configurations are reconciled.

- feat/refactor
- fix/cyd
  Duplicate branch tips representing CYD-specific development history.

- fix/working-rfid
  RFID-specific branch containing a configuration recorded as working.
  Preserve until the current RFID configuration is compared against it.

## Historical branches already contained in main

The following branch tips are ancestors of main and do not represent divergent
work:

- >git-pull
- development
- developmentnew
- feat/cyd
- feat/entityscript
- feat/rework
- feat/tryingcyd
- refactor

These may eventually be archived or removed after the repository cleanup is
complete.

## Cleanup rule

Do not delete a divergent historical branch merely because it looks obsolete.

Before retiring it:

1. determine whether its commits exist in the current production lineage;
2. inspect any unique files or configuration;
3. preserve useful device/experimental history under an appropriate branch,
   tag, or documentation;
4. only then remove redundant branch names.
