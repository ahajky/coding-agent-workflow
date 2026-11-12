#!/usr/bin/env python3
"""Shared scalar front-matter and contained-path checks (not a general YAML parser)."""
import argparse
from pathlib import Path
import re
import sys


def fields(path):
    if path == Path('-'):
        text = sys.stdin.read()
    elif not path.exists():
        return {}
    else:
        text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)', text, re.S)
    if not match:
        return {}
    result = {}
    for line in match[1].splitlines():
        item = re.match(r'^([a-z_]+):[ \t]*(.*)$', line)
        if not item:
            continue
        key, value = item.groups()
        if key in result:
            raise ValueError('front-matter 字段重复: ' + key)
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('引号未闭合: ' + key)
            value = value[1:-1]
        else:
            value = value.split(' #', 1)[0].rstrip()
        result[key] = value
    return result


def contained(root, name):
    path = Path(name)
    if not name or path.is_absolute() or '..' in path.parts or path == Path('.') or any(c in name for c in '\r\n\\'):
        raise ValueError('路径必须是项目内非空相对目录: ' + name)
    root = root.resolve()
    resolved = (root / path).resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError('路径不能通过符号链接越出项目: ' + name)
    # Reject symlinks on write paths, also when they point within the project.
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('工作流写入路径不能包含符号链接: ' + str(current))
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['field', 'path', 'name'])
    parser.add_argument('root', type=Path)
    parser.add_argument('value')
    args = parser.parse_args()
    try:
        if args.operation == 'field':
            print(fields(args.root).get(args.value, ''))
        elif args.operation == 'path':
            contained(args.root, args.value)
        else:
            if args.value in ('', '.', '..') or any(c in args.value for c in '/\\\n\r'):
                raise ValueError('名称必须是单一文件名，不能含路径分隔符')
    except (ValueError, OSError) as exc:
        print('错误:', exc, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
