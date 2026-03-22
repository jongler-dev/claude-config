# claude-config

Shared [Claude Code](https://docs.anthropic.com/en/docs/claude-code) commands and skills. Clone the repo and run the setup script to symlink everything into your `~/.claude/` directory.

## Install

```bash
git clone https://github.com/jongler-dev/claude-config.git
cd claude-config
./setup.sh
```

The setup script creates symlinks from this repo into `~/.claude/commands/` and `~/.claude/skills/`. If a directory already exists at the destination, it's backed up to `<name>.bak/` before linking. Re-running the script is safe — it updates existing symlinks in place.

## What's included

### Commands

| Command                  | Description                                                                    |
| ------------------------ | ------------------------------------------------------------------------------ |
| `/workflow:where-we-at`  | Concise project status recap — recent activity, branch state, and open threads |
| `/workflow:init-backlog` | Initialize a `BACKLOG.md` and configure `CLAUDE.md` with backlog instructions  |
| `/git:commit`            | Stage and commit changes                                                       |
| `/git:commit-push`       | Stage, commit, and push to the current branch                                  |
| `/git:commit-branch-pr`  | Stage, commit, create a feature branch, push, and open a PR                    |

### Skills

| Skill            | Description                                                        |
| ---------------- | ------------------------------------------------------------------ |
| `send-slack-msg` | Send Slack messages by display name with automatic user ID caching |

## Prerequisites

- **`gh` CLI** — Required by `/git:commit-branch-pr` for creating pull requests. [Install](https://cli.github.com/)
- **Slack MCP** — Required by `send-slack-msg`. Configure the [Slack MCP integration](https://docs.anthropic.com/en/docs/claude-code/mcp) in Claude Code before using this skill.

## Acknowledgments

The git commands are partially based on the [Commit Commands Plugin](https://github.com/anthropics/claude-code/tree/main/plugins/commit-commands) from the Claude Code repo.

## License

MIT
