#!/usr/bin/env python3
"""Search archived task documents; optionally rebuild a disposable JSON index."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

from workflow_io import fields, contained
from importlib.util import spec_from_file_location, module_from_spec
# Reuse atomic writes without making the command-line filenames an import API.
spec = spec_from_file_location('workflow_updater', Path(__file__).with_name('update-project.py'))
updater = module_from_spec(spec)
spec.loader.exec_module(updater)


def records(root):
    name = fields(root / 'AGENTS.md').get('workflow_root', '.agent')
    workflow = contained(root, name)
    archive = contained(root, name+'/work/archive')
    result = []
    warnings = []
    if not archive.exists():
        return result, warnings, workflow
    for task in sorted(archive.iterdir()):
        if task.is_symlink() or not task.is_dir():
            warnings.append('跳过非任务目录或符号链接: ' + str(task))
            continue
        h = task / 'handoff.md'
        try:
            if h.is_symlink() or not h.is_file():
                raise ValueError('缺少真实 handoff.md')
            metadata = fields(h)
            docs = []
            searchable = []
            for p in sorted(task.rglob('*')):
                if any(part in ('scratch', '.git') for part in p.relative_to(task).parts):
                    continue
                if p.is_symlink():
                    warnings.append('跳过符号链接: ' + str(p))
                    continue
                if p.is_file() and p.suffix.lower() == '.md':
                    text = p.read_text(encoding='utf-8')
                    docs.append({'path': p.relative_to(root).as_posix(),
                                 'title': next(iter(re.findall(r'^# (.+)$', text, re.M)), p.stem)})
                    searchable.append(text)
            text = h.read_text()
            goal = re.search(r'^## Goal\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
            result.append({'task': task.name, 'status': metadata.get('status', 'unknown'),
                           'updated': metadata.get('updated', ''), 'branch': metadata.get('branch', ''),
                           'summary': ' '.join(goal[1].strip().split()) if goal else '',
                           'handoff': h.relative_to(root).as_posix(), 'documents': docs,
                           'search_text': '\n'.join(searchable)})
        except (OSError, ValueError) as exc:
            warnings.append(str(task) + ': ' + str(exc))
    return result, warnings, workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path('.'))
    parser.add_argument('--query', default='', help='空格分词，所有关键词均须命中；不区分大小写')
    parser.add_argument('--status', choices=['done', 'abandoned'])
    parser.add_argument('--write', action='store_true', help='重建本地 JSON 索引（始终包含全部归档）')
    parser.add_argument('--json', action='store_true', help='输出匹配结果 JSON')
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        all_records, warnings, workflow = records(root)
        if args.write:
            contained(root, str((workflow / '.workflow').relative_to(root)))
            destination = workflow / '.workflow/archive-index.json'
            if destination.is_symlink():
                raise ValueError('索引不能是符号链接')
            updater.atomic(destination, (json.dumps({'schema': 1, 'tasks': all_records}, ensure_ascii=False, indent=2) + '\n').encode())
        terms = args.query.casefold().split()
        found = [r for r in all_records if (not args.status or args.status == r['status'])
                 and all(term in (r['task'] + '\n' + r['branch'] + '\n' + r['search_text']).casefold() for term in terms)]
        if args.json:
            print(json.dumps([{k: v for k, v in r.items() if k != 'search_text'} for r in found], ensure_ascii=False, indent=2))
        else:
            print('# 归档查询结果\n')
            for r in found:
                print('- [%s](%s) · %s · %s\n  %s' %
                      (r['task'], quote(r['handoff']), r['status'], r['updated'], r['summary']))
                for doc in r['documents']:
                    print('  - [%s](%s)' % (doc['title'].replace('[', '').replace(']', ''), quote(doc['path'])))
            print('\n匹配 %s / %s 个归档任务。' % (len(found), len(all_records)))
        for warning in warnings:
            print('提醒: ' + warning, file=sys.stderr)
        return 1 if warnings else 0
    except (ValueError, OSError) as exc:
        print('错误: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
