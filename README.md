# env-diff-tool

Compare and diff environment variables between files or systems.

## Why I Built This

Ever had to figure out what's different between your `.env.development` and `.env.production` files? Or needed to sync environment variables between two configs without manually eyeballing hundreds of lines? Yeah, me too. This tool does that thing where it shows you exactly what changed, what's missing, and what's new.

## Quick Start

```bash
# Compare two env files
python env_diff.py .env.local .env.production

# Compare current shell env with a file
python env_diff.py current .env.docker

# Pipe from stdin
cat .env.base | python env_diff.py --stdin .env.overrides

# Get JSON output for scripting
python env_diff.py file1 file2 --format json
```

## Installation

No installation needed really. Just grab the files:

```bash
git clone <repo>
cd env-diff-tool
pip install -r requirements.txt  # actually there's nothing to install, but the file exists
```

It's a single Python file with zero dependencies. Works with Python 3.6+.

## Usage

### Basic Comparison

```bash
python env_diff.py .env.dev .env.prod
```

This shows you:
- Variables only in the first file
- Variables only in the second file  
- Variables that exist in both but have different values
- Count of unchanged variables

### Output Formats

**Human readable (default):**
```bash
python env_diff.py file1 file2
```

**JSON (for scripting/CI):**
```bash
python env_diff.py file1 file2 --format json
```

**Export format (to sync environments):**
```bash
python env_diff.py file1 file2 --format export > sync.sh
source sync.sh
```

### Filtering

Only care about certain variables?

```bash
# Only show DB-related vars
python env_diff.py file1 file2 --filter "DB_"

# Exclude sensitive stuff
python env_diff.py file1 file2 --exclude "PASSWORD|SECRET|KEY"

# Combine both
python env_diff.py file1 file2 --filter "API" --exclude "PRIVATE"
```

### Merge Mode

Want to combine two env files instead of diffing?

```bash
python env_diff.py base.env overrides.env --merge > merged.env
```

Second file takes precedence for duplicate keys.

### Compare with Current Environment

```bash
# See what's different between your shell and a file
python env_diff.py current .env.template

# Save current env to a file-like format
python env_diff.py current "" --format json
```

## Real-World Scenarios

### Debugging "Works on My Machine"

```bash
# What env vars do I have that the docker container doesn't?
python env_diff.py current .env.docker
```

### Pre-Deployment Check

```bash
# Make sure production has all required vars
python env_diff.py .env.required .env.production
```

### CI/CD Pipeline

```yaml
# In your GitHub Actions or similar
- name: Check env parity
  run: |
    python env_diff.py .env.staging .env.production --format json > diff.json
    # Then parse diff.json and fail if critical vars differ
```

### Sync Development Environments

```bash
# Generate commands to update your env
python env_diff.py .env.john .env.me --format export | bash
```

## File Format

Standard `.env` format:

```bash
# Comments are ignored
DATABASE_URL=postgres://localhost/mydb
API_KEY="quoted values work"
SECRET='single quotes too'

# Empty lines skipped
DEBUG=true
```

## Exit Codes

- `0`: Success (even if differences found)
- `1`: Error (file not found, invalid args, etc.)

## Tips

- Use `--format json` when you need to parse the output in scripts
- The `current` keyword is handy for debugging environment issues
- Combine with `diff` command for side-by-side terminal views
- Pipe to `grep` for quick searches in large diffs

## Limitations

- Doesn't handle multi-line values (neither do I honestly)
- No interactive mode (maybe someday)
- Doesn't validate variable values, just compares them as strings

## License

Do whatever you want with it.
