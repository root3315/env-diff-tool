#!/usr/bin/env python3
"""
env-diff-tool: Compare and diff environment variables between files or systems.
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path


def parse_env_file(filepath):
    """Parse an environment file and return a dictionary of key-value pairs."""
    env_vars = OrderedDict()
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if '=' not in line:
                continue
            
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            env_vars[key] = value
    
    return env_vars


def parse_env_string(env_string):
    """Parse environment variables from a string (e.g., from stdin or command line)."""
    env_vars = OrderedDict()
    
    for line in env_string.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        
        key, _, value = line.partition('=')
        env_vars[key.strip()] = value.strip()
    
    return env_vars


def get_current_env():
    """Get current process environment variables."""
    return OrderedDict(sorted(os.environ.items()))


def compare_envs(env1, env2):
    """Compare two environment dictionaries and return differences."""
    keys1 = set(env1.keys())
    keys2 = set(env2.keys())
    
    only_in_first = keys1 - keys2
    only_in_second = keys2 - keys1
    common_keys = keys1 & keys2
    
    modified = {}
    for key in common_keys:
        if env1[key] != env2[key]:
            modified[key] = {
                'old': env1[key],
                'new': env2[key]
            }
    
    return {
        'only_in_first': {k: env1[k] for k in sorted(only_in_first)},
        'only_in_second': {k: env2[k] for k in sorted(only_in_second)},
        'modified': {k: v for k, v in sorted(modified.items())},
        'unchanged': sorted([k for k in common_keys if env1[k] == env2[k]])
    }


def format_value(value, max_length=60):
    """Format a value for display, truncating if necessary."""
    value_str = str(value)
    if len(value_str) > max_length:
        return value_str[:max_length - 3] + '...'
    return value_str


def print_diff_human(diff, name1='file1', name2='file2'):
    """Print differences in human-readable format."""
    print(f"\n{'=' * 60}")
    print(f"Environment Diff: {name1} vs {name2}")
    print(f"{'=' * 60}\n")
    
    if diff['only_in_first']:
        print(f"📦 Only in {name1}:")
        print(f"{'-' * 40}")
        for key, value in diff['only_in_first'].items():
            print(f"  - {key}={format_value(value)}")
        print()
    
    if diff['only_in_second']:
        print(f"📦 Only in {name2}:")
        print(f"{'-' * 40}")
        for key, value in diff['only_in_second'].items():
            print(f"  + {key}={format_value(value)}")
        print()
    
    if diff['modified']:
        print(f"🔄 Modified:")
        print(f"{'-' * 40}")
        for key, changes in diff['modified'].items():
            print(f"  ~ {key}:")
            print(f"      old: {format_value(changes['old'])}")
            print(f"      new: {format_value(changes['new'])}")
        print()
    
    unchanged_count = len(diff['unchanged'])
    print(f"✓ Unchanged: {unchanged_count} variables")
    
    total_changes = (
        len(diff['only_in_first']) +
        len(diff['only_in_second']) +
        len(diff['modified'])
    )
    
    print(f"\n{'=' * 60}")
    if total_changes == 0:
        print("No differences found!")
    else:
        print(f"Total differences: {total_changes}")
    print(f"{'=' * 60}\n")


def print_diff_json(diff):
    """Print differences in JSON format."""
    output = {
        'only_in_first': diff['only_in_first'],
        'only_in_second': diff['only_in_second'],
        'modified': diff['modified'],
        'unchanged_count': len(diff['unchanged'])
    }
    print(json.dumps(output, indent=2))


def print_diff_export(diff, name1='file1', name2='file2'):
    """Print differences as export commands to sync environments."""
    for key, value in diff['only_in_second'].items():
        print(f"export {key}=\"{value}\"")
    
    for key in diff['only_in_first']:
        print(f"unset {key}")
    
    for key, changes in diff['modified'].items():
        print(f"export {key}=\"{changes['new']}\"")


def merge_envs(env1, env2, prefer_second=True):
    """Merge two environment dictionaries."""
    merged = OrderedDict(env1)
    
    for key, value in env2.items():
        if prefer_second or key not in merged:
            merged[key] = value
    
    return merged


def filter_env_vars(env_vars, pattern=None, exclude_pattern=None):
    """Filter environment variables by include/exclude patterns."""
    filtered = OrderedDict()
    
    include_re = re.compile(pattern) if pattern else None
    exclude_re = re.compile(exclude_pattern) if exclude_pattern else None
    
    for key, value in env_vars.items():
        if include_re and not include_re.search(key):
            continue
        if exclude_re and exclude_re.search(key):
            continue
        filtered[key] = value
    
    return filtered


def main():
    parser = argparse.ArgumentParser(
        description='Compare and diff environment variables between files or systems.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s .env.dev .env.prod
  %(prog)s --current .env.local
  %(prog)s file1 file2 --format json
  %(prog)s --stdin file1
  %(prog)s file1 file2 --filter "DB_" --exclude "PASSWORD"
        '''
    )
    
    parser.add_argument('file1', nargs='?', help='First environment file or "current" for system env')
    parser.add_argument('file2', nargs='?', help='Second environment file or "current" for system env')
    parser.add_argument('--format', '-f', choices=['human', 'json', 'export'], default='human',
                        help='Output format (default: human)')
    parser.add_argument('--stdin', '-s', action='store_true',
                        help='Read first environment from stdin')
    parser.add_argument('--filter', metavar='PATTERN',
                        help='Include only variables matching this regex pattern')
    parser.add_argument('--exclude', metavar='PATTERN',
                        help='Exclude variables matching this regex pattern')
    parser.add_argument('--merge', '-m', action='store_true',
                        help='Merge environments instead of diffing (outputs merged result)')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Write output to file instead of stdout')
    
    args = parser.parse_args()
    
    if not args.file1 and not args.stdin:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.stdin:
            env1 = parse_env_string(sys.stdin.read())
        elif args.file1 == 'current':
            env1 = get_current_env()
        elif args.file1:
            env1 = parse_env_file(args.file1)
        else:
            env1 = OrderedDict()
        
        if args.file2:
            if args.file2 == 'current':
                env2 = get_current_env()
            else:
                env2 = parse_env_file(args.file2)
        else:
            env2 = OrderedDict()
        
        env1 = filter_env_vars(env1, args.filter, args.exclude)
        env2 = filter_env_vars(env2, args.filter, args.exclude)
        
        if args.merge:
            merged = merge_envs(env1, env2)
            output_lines = [f"{k}={v}" for k, v in merged.items()]
            output = '\n'.join(output_lines) + '\n'
        else:
            diff = compare_envs(env1, env2)
            
            if args.format == 'json':
                output = json.dumps(diff, indent=2) + '\n'
            elif args.format == 'export':
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    print_diff_export(diff, args.file1 or 'stdin', args.file2 or 'empty')
                output = f.getvalue()
            else:
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    print_diff_human(diff, args.file1 or 'stdin', args.file2 or 'empty')
                output = f.getvalue()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Output written to {args.output}")
        else:
            print(output, end='')
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
