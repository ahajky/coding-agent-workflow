#!/usr/bin/env python3
"""Preview/apply workflow rule updates without replacing project-owned sections."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
from datetime import datetime, timezone

SOURCE = Path(__file__).resolve().parent.parent
TITLES = ('工作流铁律（必须遵守）', '文档写入前检查')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def sections(text):
    # Ignore heading-like text inside fenced code blocks.
    matches = []
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None and line.startswith('## '):
            matches.append((offset, line[3:].strip()))
        offset += len(line)
    result = {}
    for i, (start, title) in enumerate(matches):
        if title in result:
            raise ValueError('重复章节，需手工整理: ' + title)
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        result[title] = (start, end, text[start:end])
    return result


def workflow_root(root, text):
    fm = re.match(r'\A---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not fm:
        raise ValueError('缺少 front-matter；请先明确 workflow_root，1.x 布局需手工迁移')
    fields = re.findall(r'^workflow_root:[ \t]*(.+?)\s*$', fm[1], re.M)
    if len(fields) != 1:
        raise ValueError('workflow_root 必须唯一且非空；旧 tasks_root/docs_root 布局需手工迁移')
    name = fields[0].strip().strip('\"\'')
    path = Path(name)
    if (not name or path.is_absolute() or '..' in path.parts or path == Path('.')
            or any(c in name for c in '\n\r\\')):
        raise ValueError('workflow_root 必须是项目内的相对目录')
    target = root / path
    if not target.resolve().is_relative_to(root) or target.resolve() == root:
        raise ValueError('workflow_root 不能通过符号链接指向项目外或项目根')
    # Metadata must not follow symbolic links, even ones within the project.
    metadata = target / '.workflow'
    if metadata.is_symlink() or any(p.is_symlink() for p in metadata.parents if p != root and root in p.parents):
        raise ValueError('工作流元数据路径不能包含符号链接')
    return name.rstrip('/'), metadata


def read_state(path):
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError('状态文件不能是符号链接')
    state = json.loads(path.read_text())
    if state.get('schema') != 1 or not isinstance(state.get('sections'), dict):
        raise ValueError('不支持的升级状态格式')
    if set(state['sections']) != set(TITLES) or not all(isinstance(v, str) for v in state['sections'].values()):
        raise ValueError('升级基线章节不完整')
    return state


def run(args):
    root = args.root.resolve()
    agents = root / 'AGENTS.md'
    if agents.is_symlink() or not agents.is_file():
        raise ValueError('需要真实 AGENTS.md 文件；新项目先运行 init-project.sh')
    before = agents.read_bytes()
    text = before.decode('utf-8')
    name, meta = workflow_root(root, text)
    state_path = meta / 'state.json'
    state = read_state(state_path)
    prior_state = state_path.read_bytes() if state else None
    version = (SOURCE / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('技能 VERSION 必须是三段数字')
    if state and not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', str(state.get('version', ''))):
        raise ValueError('项目状态版本非法')
    if state and state.get('workflow_root') != name:
        raise ValueError('项目路径映射与升级基线不一致，请先确认目录迁移')
    current = sections(text)
    if state and not args.restore:
        parse = lambda v: tuple(int(n) for n in v.split('.'))
        if parse(state['version']) > parse(version):
            raise ValueError('项目版本比当前技能新，拒绝降级；请更新技能或使用备份回滚')

    if args.restore:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', args.restore):
            raise ValueError('非法备份编号')
        folder = meta / 'backups' / args.restore
        if folder.is_symlink() or (meta / 'backups').is_symlink():
            raise ValueError('备份目录不能是符号链接')
        backup = json.loads((folder / 'backup.json').read_text())
        if backup['after_agents_sha256'] != digest(before) or backup['after_state_sha256'] != digest(prior_state or b''):
            raise ValueError('升级后入口或状态又有修改，拒绝覆盖；请手工对照备份合并')
        original = (folder / 'AGENTS.md').read_bytes()
        original_state = (folder / 'state.before').read_bytes() if backup['had_state'] else None
        if digest(original) != backup['before_agents_sha256'] or digest(original_state or b'') != backup['before_state_sha256']:
            raise ValueError('备份校验失败')
        atomic(agents, original)
        if original_state is None:
            state_path.unlink()
        else:
            atomic(state_path, original_state)
        print('已恢复升级前入口与版本状态；任务与项目文件未变。')
        return 0

    template = (SOURCE / 'templates' / 'AGENTS.md').read_text().replace('.agent/', name + '/')
    wanted = {title: sections(template)[title][2] for title in TITLES}
    legacy = json.loads((SOURCE / 'references' / 'legacy-workflow-rules.json').read_text())
    known = {title: {snapshot[title].replace('.agent/', name + '/').strip()
                     for snapshot in legacy.values() if title in snapshot} for title in TITLES}
    conflicts = []
    edits = []
    for title, target in wanted.items():
        entry = current.get(title)
        local = entry[2] if entry else None
        baseline = state['sections'].get(title) if state else None
        if local is not None and local.strip() == target.strip():
            continue
        if state:
            safe = local == baseline
        else:
            safe = (local is None and title != TITLES[0]) or (local is not None and local.strip() in known[title])
        if not safe:
            conflicts.append(title)
        elif entry:
            edits.append((entry[0], entry[1], target))
        else:
            edits.append((len(text), len(text), '\n' + target))
    print('项目版本:', state['version'] if state else '未知（无升级基线；仅识别历史通用章节，不推断项目版本）')
    print('目标版本:', version, '| workflow_root:', name)
    if conflicts:
        print('冲突章节:', '、'.join(conflicts))
        print('未写入。请将自定义补充移到独立章节，并对照模板手工合并这些通用章节后重试。')
        if args.check:
            return 2
        # Show targets for conflicting sections as well as safe changes.
        for title in conflicts:
            local = current[title][2] if title in current else ''
            print(''.join(difflib.unified_diff(local.splitlines(True), wanted[title].splitlines(True),
                                             fromfile='本地/' + title, tofile='新版/' + title)), end='')
        return 2
    updated = text
    for start, end, replacement in sorted(edits, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    new_state = {'schema': 1, 'version': version, 'workflow_root': name,
                 'sections': {t: sections(updated)[t][2] for t in TITLES}}
    after_state = (json.dumps(new_state, ensure_ascii=False, indent=2) + '\n').encode()
    if updated.encode() == before and state == new_state:
        print('已是当前版本，无需修改。')
        return 0
    if args.check:
        print('有可用更新；运行 update-project.py 预览。')
        return 3
    print(''.join(difflib.unified_diff(text.splitlines(True), updated.splitlines(True),
                                     fromfile='AGENTS.md（当前）', tofile='AGENTS.md（升级后）')), end='')
    print('版本状态将更新到', version)
    if not args.apply:
        print('仅预览，未写入；使用 --apply 应用。')
        return 0
    if agents.read_bytes() != before or (state_path.read_bytes() if state_path.exists() else None) != prior_state:
        raise ValueError('预览期间文件发生变化，请重试')
    backups = meta / 'backups'
    if backups.is_symlink():
        raise ValueError('备份目录不能是符号链接')
    backups.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-'), dir=backups))
    atomic(folder / 'AGENTS.md', before)
    if prior_state is not None:
        atomic(folder / 'state.before', prior_state)
    manifest = {'had_state': prior_state is not None,
                'before_agents_sha256': digest(before), 'before_state_sha256': digest(prior_state or b''),
                'after_agents_sha256': digest(updated.encode()), 'after_state_sha256': digest(after_state)}
    atomic(folder / 'backup.json', (json.dumps(manifest, indent=2) + '\n').encode())
    try:
        atomic(agents, updated.encode())
        atomic(state_path, after_state)
    except OSError:
        atomic(agents, before)
        if prior_state is not None:
            atomic(state_path, prior_state)
        elif state_path.exists():
            state_path.unlink()
        raise
    print('已应用，备份编号:', folder.name)
    print('回滚:', shlex.join(['python3', str(SOURCE / 'scripts' / 'update-project.py'), str(root), '--restore', folder.name]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path('.'))
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='仅检测：0 当前，3 有更新，2 冲突，1 错误')
    action.add_argument('--apply', '--sync', dest='apply', action='store_true', help='同步无冲突规则并保存回滚原件；冲突则不写入')
    action.add_argument('--restore', metavar='BACKUP_ID', help='校验后恢复指定备份')
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('错误:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
