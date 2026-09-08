# Contributing to Syx LLM Overlord

## Development Environment Setup

**Requirements:**
- Python 3.11+ (bridge)
- Java 21 (mod)
- Songs of Syx (any recent version)

**First-time setup:**

```bash
python3 -m venv bridge/.venv
source bridge/.venv/bin/activate
pip install -r bridge/requirements.txt
```

The mod install script handles game detection and linking automatically:

```bash
./install.sh
```

## Running Tests

```bash
cd bridge
source .venv/bin/activate
python -m pytest tests/ -v
```

## Building the Mod

```bash
cd syx-llm-mod
./mvnw install -P linux -Dgame.jar.path=<path-to-game-jar>
```

## Code Style

No formal linting rules are enforced yet. Follow the existing patterns in the codebase:

- Python: 4-space indentation, type annotations where practical
- Java: Standard Java conventions
- Shell: POSIX-compatible where possible

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and ensure tests pass
4. Commit with descriptive messages
5. Open a Pull Request (or Merge Request on GitLab)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and improvements.
