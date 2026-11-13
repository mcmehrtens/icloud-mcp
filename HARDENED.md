# Hardened fork

This is a fork of [mike-tih/icloud-mcp](https://github.com/mike-tih/icloud-mcp) that is
meant to be reachable by Claude's hosted connectors. The `hardened` branch carries a
small set of patches on top of upstream `main`. Each patch is one commit, so rebasing
onto new upstream releases stays straightforward.

## What the patches change

| Commit | Change | Why |
| - | - | - |
| Remove destructive tools | `email_move`, `email_delete`, `calendar_delete_event`, `contacts_create`, `contacts_update`, `contacts_delete` are gone, along with their backing code | Nothing here can delete, move or overwrite data |
| Remove every outbound mail path | `email_send`, all SMTP code and iTIP invitations are gone. Events can't get attendees, and events that already have attendees or an organizer can't be updated. Drafts can't attach local files | A prompt-injected agent has no way to send anything to anyone. iCloud's server-side scheduling would otherwise email changes to existing attendees |
| Credentials from env only; strong token | The `X-Apple-*` header and HTTP Basic credential paths are gone. HTTP mode refuses to start without `MCP_AUTH_TOKEN` (32+ chars) | A request can't switch the account. The endpoint is never open |
| Untrusted content marking | Email bodies come back wrapped in `<untrusted_email_content>` (embedded tags are defanged). Listings are capped at 100 | Helps the model treat mail as data, and bounds output size |
| uv, pinned image, CI/CD | Multi-stage `Dockerfile` using `uv sync --locked`, digest-pinned bases, non-root UID 3020, no curl. Ruff (including `S` security and `B` bugbear rules), pytest and zizmor gate every change. Renovate keeps everything current | Reproducible, minimal, continuously patched image |

## Remaining tools

Reading: `email_list_folders`, `email_list_messages`, `email_search`, `email_get_message`,
`email_get_messages`, `email_get_attachment`, `calendar_list_calendars`,
`calendar_list_events`, `calendar_search_events`, `calendar_list_subscriptions`,
`calendar_list_subscribed_events`, `contacts_list`, `contacts_search`, `contacts_get`.

Writing: `email_save_draft`, `email_mark_read`, `email_mark_unread`,
`calendar_create_event`, `calendar_update_event`.

The deployment's gateway also has its own tool allowlist, which further narrows this
list (for example, it denies `email_get_attachment` and the mark-read tools).

## Images and versions

`ci.yml` gates every PR and push (tests plus an image build) but publishes nothing.
`release.yml` runs daily at 15:00 UTC, two hours after Renovate. If `hardened` has
unreleased commits and `ci` passed on its HEAD, it publishes
`ghcr.io/mcmehrtens/icloud-mcp` with the tags below. Otherwise it skips. So a day of
small changes ships as one release, and an unchanged day ships nothing. Run it by
hand with `gh workflow run release.yml`.

| Tag | Moves? | Use |
| - | - | - |
| `:1` | Yes, to every new 1.x.y | **Pin this on the NAS.** Pull and redeploy to update |
| `:1.0` | Yes, to every new 1.0.y | |
| `:1.0.7` | No | Rollback target |
| `:sha-<commit>` | No | Exact build |

`MAJOR.MINOR` comes from `HARDENED_VERSION`, and `PATCH` increments automatically
(git tag `v1.0.7`, created after the image is pushed). Bump `HARDENED_VERSION` to `2.0` only for a change that needs the
deployment to change too, such as a new required env var or a renamed or removed tool
the gateway allowlist refers to. The NAS then stays on `:1` until you move it.

## Dependency updates (Renovate)

Renovate is self-hosted (`.github/workflows/renovate.yml`, daily at 13:00 UTC) and uses
a GitHub App token, so its PRs trigger the gating CI. `renovate.json` covers Python
dependencies (`uv.lock`), Dockerfile base images (digest-pinned), the actionlint image
in `scripts/verify.sh` and GitHub Actions (SHA-pinned):

- Nothing is adopted until it's **3 days old**. `[tool.uv] exclude-newer = "3 days"`
  enforces the same cooldown for a manual `uv lock`. Security fixes also wait 3 days,
  because the lock can't resolve anything newer. For an urgent one, run
  `uv lock --upgrade-package <pkg> --exclude-newer-package <pkg>=<timestamp>` by hand.
- **Patch, minor and digest** updates automerge once CI is green, and go out in that
  day's release.
- **Major** updates, and a Python minor (3.13 to 3.14), open a PR labelled
  `needs-review` and wait for a human or an LLM.
- **GitHub Actions** come in one grouped PR on Saturdays, labelled `needs-allowlist`,
  and never automerge. The Actions allowlist pins exact SHAs, so the PR fails with
  `startup_failure` until you add its new SHAs (then drop the old ones after merging).
- `uv.lock` maintenance runs on Saturdays.

## Upstream sync

`.github/workflows/upstream-sync.yml` checks
[mike-tih/icloud-mcp](https://github.com/mike-tih/icloud-mcp) every Saturday at 13:00 UTC:

- It merges upstream `main` into `sync/upstream`, runs ruff and the tests, and opens a
  PR into `hardened`. It never merges on its own.
- On a merge conflict it opens an issue instead.
- Upstream code is untrusted until reviewed, so it runs only in a job with a read-only
  token. The job that pushes the branch and opens the PR runs no repository code.

Before merging a sync PR, look for new tools, anything touching `smtplib`, credentials
or URLs, and check the gateway allowlist still matches. The tests
`test_nothing_can_send_mail`, `test_destructive_tools_are_gone` and
`test_contacts_are_read_only` fail if upstream reintroduces those paths.

To sync by hand:

```sh
git fetch upstream
git log --oneline hardened..upstream/main       # what's new
git diff hardened...upstream/main -- src        # review it
git merge upstream/main                          # on hardened
uv lock && uv run ruff check . && uv run pytest -q
```

## Local checks mirror CI

`scripts/verify.sh` is the single definition of the gates: `uv sync --locked`, ruff
(including `S` security and `B` bugbear rules), pytest, zizmor and actionlint. CI's
`test` job runs it as is, and the `pre-push` hook runs it with `--image` (adding the
Docker build that CI's `image` job does). If a push gets past the hook, CI passes too.

- `pre-commit` (the lint-staged equivalent) runs `ruff check --fix` on staged Python
  files and re-stages them. A file that also has unstaged edits is only checked. It
  also runs zizmor and actionlint when a workflow file is staged, and checks that
  staged JSON parses.
- Formatting isn't enforced: upstream isn't ruff-formatted, and reformatting its
  files would conflict on every upstream merge.
- The hooks need Docker running (for actionlint and the image build) and are enabled
  per clone:

  ```sh
  git config core.hooksPath .githooks
  ```

## One-time GitHub setup

1. **Renovate app:** install the existing Renovate GitHub App (the one mehrtens.com
   uses) on this repository, and add its `RENOVATE_CLIENT_ID` and
   `RENOVATE_APP_PRIVATE_KEY` as repository secrets. `upstream-sync` uses the same app
   token so its PR triggers CI. Each workflow scopes the token to the permissions it
   needs.
2. **Actions allowlist:** Settings → Actions → allow only selected actions, with
   SHA pinning required. Allowlist exactly:

   ```text
   actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
   actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510
   actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333
   actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9
   astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2
   docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc
   docker/login-action@8aa5831fb8d48d8f76594c7ddde61ae58019f550
   docker/metadata-action@dc802804100637a589fabce1cb79ff13a1411302
   docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069
   renovatebot/github-action@1c0cf989c02653fba0efe7ca5772338860ca71dc
   ```

   Default workflow token: **read repository contents**.
3. **Ruleset on `hardened`:** require the `test` and `image` checks from `ci` (Renovate's
   automerge waits on them), and enable **Allow auto-merge** in Settings → General.
4. **Package visibility:** after the first image is published, go to Packages →
   `icloud-mcp` and make it **public** (it contains no secrets), so the NAS can pull
   it without a token.
