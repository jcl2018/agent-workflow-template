# Milestones: commands and flows

Moved from the wiki page, which is now only a summary, criteria and tests.

## Commands

```text
features
new FEATURE|backlog|--all [--live]
attach SLUG [--live]
move ISSUE FEATURE|backlog [--live]
```

- `features` lists the features: the pages in the page map except Home.
- `new` creates the milestone for one feature, the `Backlog`, or all of them, and nothing that already exists.
- `attach` puts a goal's pull request in the milestone of the feature its touched files belong to. The pull request step
  of the delivery skill runs it, and a failure never stops the goal.
- `move` puts an issue in a feature's milestone, or back on the `Backlog`.

Each one prints what it would do and writes nothing unless you pass `--live` or set `GH_TOKEN` or `GITHUB_TOKEN`. None
of them closes, deletes or merges anything. The `file --group` command of [Health](Health) files findings on the `Backlog`.

### Stage charts

Amber marks where the command stops for the owner. [Home](Home) says what each status means. "Toy test" means a throwaway repo with stand-ins for GitHub.

#### `new`

```mermaid
flowchart LR
  a["Read the milestones that exist"]
  b["Create the missing ones"]
  a --> b
```

Status: built and proven: Read the milestones that exist; Create the missing ones. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests with a stand-in for GitHub. No real milestone exists on this repo yet.

#### `attach`

```mermaid
flowchart LR
  a["Find the feature from the goal's touches"]
  b["Put the pull request in its milestone"]
  a --> b
```

Status: built and proven: Find the feature from the goal's touches; Put the pull request in its milestone. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests with a stand-in for GitHub. It has never run on a real pull request.

#### `move`

```mermaid
flowchart LR
  a["Choose the feature or the Backlog"]
  b["Put the issue in that milestone"]
  a --> b
```

Status: built and proven: Choose the feature or the Backlog; Put the issue in that milestone. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests with a stand-in for GitHub.

#### `features`

```mermaid
flowchart LR
  a["List the pages in the page map except Home"]
  a
```

Status: built and proven: List the pages in the page map except Home. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests use it through `new --all`.

