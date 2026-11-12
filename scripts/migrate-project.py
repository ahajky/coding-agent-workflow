#!/usr/bin/env python3
"""Preview and migrate a 1.x local layout; explicitly select personal documents."""
import argparse
import base64
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit, urlunsplit
import importlib.util

from workflow_io import fields, contained
spec = importlib.util.spec_from_file_location('workflow_update', Path(__file__).with_name('update-project.py'))
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)
SOURCE = Path(__file__).resolve().parent.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(root, args):
    agents = root / 'AGENTS.md'
    if agents.is_symlink() or not agents.is_file():
        raise ValueError('需要真实 AGENTS.md')
    original = agents.read_bytes()
    text = original.decode()
    meta = fields(agents)
    if meta.get('workflow_root'):
        raise ValueError('已经使用 workflow_root；请使用 update-project.py 同步规则')
    tasks_name = args.tasks_root or meta.get('tasks_root')
    docs_name = args.docs_root or meta.get('docs_root')
    if not tasks_name or not docs_name:
        raise ValueError('无法确定旧路径；请显式指定 --tasks-root 与 --docs-root')
    tasks = contained(root, tasks_name)
    docs = contained(root, docs_name)
    destination = contained(root, args.workflow_root)
    if destination.exists():
        raise ValueError('目标工作流目录已存在，拒绝合并或覆盖；请先核对或换 --workflow-root')
    if any(a == b or a in b.parents or b in a.parents for a,b in [(tasks, docs), (tasks, destination), (docs, destination)]):
        raise ValueError('旧任务、旧文档与目标目录不可互相嵌套')
    files = {}
    directories = {}
    # Only task subtrees whose immediate task directories have handoff are eligible.
    for category in ('active', 'archive'):
        folder = tasks / category
        contained(root, str(folder.relative_to(root)))
        if not folder.exists():
            continue
        directories[folder] = destination / 'work' / category
        for task in folder.iterdir():
            if task.is_symlink() or not task.is_dir() or not (task / 'handoff.md').is_file():
                raise ValueError('旧任务子树有无法识别的内容，需先整理: ' + str(task))
            for file in task.rglob('*'):
                if '.git' in file.relative_to(task).parts:
                    raise ValueError('任务含嵌套 Git 仓库，需先单独处理: '+str(file))
                if file.is_symlink():
                    raise ValueError('迁移内容包含符号链接: ' + str(file))
                if file.is_file():
                    files[file] = destination / 'work' / category / file.relative_to(folder)
    if not files:
        raise ValueError('没有可识别的旧任务，拒绝猜测迁移范围')
    for selection in args.personal_doc:
        selected = contained(root, selection)
        if not selected.is_relative_to(docs) or selected == docs or not selected.exists():
            raise ValueError('--personal-doc 必须指定旧 docs_root 内实际存在的文件或子目录')
        candidates = [selected] if selected.is_file() else list(selected.rglob('*'))
        if selected.is_dir():
            directories[selected] = destination / 'docs' / selected.relative_to(docs)
        for file in candidates:
            if file.is_symlink():
                raise ValueError('个人文档包含符号链接: ' + str(file))
            if file.is_file():
                files[file] = destination / 'docs' / file.relative_to(docs)

    def mapped(path):
        if path in files:
            return files[path]
        for old,new in sorted(directories.items(), key=lambda pair: len(str(pair[0])), reverse=True):
            if path == old or path.is_relative_to(old):
                return new / path.relative_to(old)
        return path

    def links(value, old_file, new_file):
        def target(raw):
            angle = raw.startswith('<') and raw.endswith('>')
            url = raw[1:-1] if angle else raw
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/'):
                return raw
            old_target = (old_file.parent / unquote(parts.path)).resolve()
            new_target = mapped(old_target)
            new_path = os.path.relpath(new_target, new_file.parent).replace(os.sep,'/')
            result = urlunsplit(('', '', quote(new_path, safe='/._-~'), parts.query, parts.fragment))
            return '<'+result+'>' if angle else result
        # Inline links/images and reference definitions, with optional title suffix.
        value = re.sub(r'(\]\()(<[^>]+>|[^)\s]+)([^)]*\))',
                       lambda m: m[1]+target(m[2])+m[3], value)
        value = re.sub(r'(^[ \t]*\[[^\]]+\]:[ \t]*)(<[^>]+>|\S+)',
                       lambda m: m[1]+target(m[2]), value, flags=re.M)
        def code(m):
            path = m[1]
            for old,new in sorted(directories.items(), key=lambda pair: len(str(pair[0])), reverse=True):
                relative = old.relative_to(root).as_posix()
                if path == relative or path.startswith(relative+'/'):
                    return '`'+new.relative_to(root).as_posix()+path[len(relative):]+'`'
            for old,new in files.items():
                if path == old.relative_to(root).as_posix():
                    return '`'+new.relative_to(root).as_posix()+'`'
            return m[0]
        return re.sub(r'`([^`\n]+)`', code, value)

    local_sections = update.sections(text)
    template = (SOURCE / 'templates/AGENTS.md').read_text().replace('.agent/', args.workflow_root+'/')
    target_sections = update.sections(template)
    legacy = json.loads((SOURCE / 'references/legacy-layout-rules.json').read_text())
    replacements = []
    for title in ('工作流铁律（必须遵守）', 'Git 约定'):
        current = local_sections.get(title)
        expected = {snapshot[title].replace('work/',tasks_name+'/').replace('docs/',docs_name+'/').strip()
                    for snapshot in legacy.values() if title in snapshot}
        target = target_sections[title][2]
        if not current or (current[2].strip() not in expected and current[2].strip() != target.strip()):
            raise ValueError('旧通用章节有自定义或无法识别，请先与新版模板人工合并该节: '+title)
        replacements.append((current[0],current[1],target))
    if '文档写入前检查' in local_sections:
        if local_sections['文档写入前检查'][2].strip() != target_sections['文档写入前检查'][2].strip():
            raise ValueError('已有自定义文档写入前检查，请先人工合并该节')
    else:
        replacements.append((len(text),len(text),'\n'+target_sections['文档写入前检查'][2]))
    for start,end,value in sorted(replacements,reverse=True):
        text=text[:start]+value+text[end:]
    text=links(text,agents,agents)
    fm=re.match(r'\A---\s*\n(.*?)\n---',text,re.S)
    if fm:
        body=re.sub(r'^(?:tasks_root|docs_root):.*\n?', '', fm[1],flags=re.M)
        text='---\n'+body.rstrip()+'\nworkflow_root: '+args.workflow_root+'\n---'+text[fm.end():]
    else:
        text='---\nworkflow_root: '+args.workflow_root+'\n---\n'+text
    text+='\n## 迁移后的个人工作区\n\n个人任务、知识、交付草稿、外部工作副本分别位于 `'+args.workflow_root+'/work/`、`'+args.workflow_root+'/docs/`、`'+args.workflow_root+'/reports/`、`'+args.workflow_root+'/references/`。旧 docs 中未明确选入迁移的内容、旧 reports/references 保持原位；导航中指向它们的条目仍指向项目资料，不能据此推断已经全部私有化。迁移执行者负责复核正式文档中的外链。\n'
    # Report inbound references without rewriting team-maintained documents.
    inbound = []
    for p in root.rglob('*.md'):
        if p.is_symlink() or '.git' in p.relative_to(root).parts or p == agents or p in files:
            continue
        try:
            value=p.read_text(encoding='utf-8')
            if links(value,p,p) != value:
                inbound.append(p.relative_to(root).as_posix())
        except UnicodeError:
            continue
    writes = {}
    originals = {}
    for old,new in files.items():
        data = old.read_bytes()
        originals[old] = data
        writes[new] = links(data.decode(),old,new).encode() if old.suffix.lower()=='.md' else data
    if (root/'.gitignore').is_symlink():
        raise ValueError('.gitignore 不能是符号链接')
    ignore=root/'.gitignore'
    ignore_before=ignore.read_bytes() if ignore.exists() else None
    ignored=(ignore_before or b'').decode()
    for line in (args.workflow_root+'/', 'AGENTS.md'):
        if line not in ignored.splitlines():
            ignored=ignored.rstrip()+'\n'+line+'\n'
    version=(SOURCE/'VERSION').read_text().strip()
    state={'schema':1,'version':version,'workflow_root':args.workflow_root,
           'sections':{t:update.sections(text)[t][2] for t in update.TITLES}}
    writes[destination/'.workflow/state.json']=(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode()
    return {'original':original,'agents':text.encode(),'files':files,'originals':originals,'writes':writes,
            'ignore_before':ignore_before,'ignore':ignored.encode(),'destination':destination,
            'tasks':tasks,'docs':docs,'inbound':inbound}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',nargs='?',type=Path,default=Path('.'))
    parser.add_argument('--tasks-root')
    parser.add_argument('--docs-root')
    parser.add_argument('--workflow-root',default='.agent')
    parser.add_argument('--personal-doc',action='append',default=[],help='项目相对路径；明确属于个人的文件或子目录，可重复')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:
        root=args.root.resolve()
        args.workflow_root=args.workflow_root.rstrip('/')
        plan=build(root,args)
        print('迁移清单（未选中的项目文档不动）：')
        for old,new in plan['files'].items():
            print(str(old.relative_to(root))+' -> '+str(new.relative_to(root)))
        print(''.join(difflib.unified_diff(plan['original'].decode().splitlines(True),plan['agents'].decode().splitlines(True),fromfile='AGENTS.md（旧）',tofile='AGENTS.md（新）')),end='')
        if plan['inbound']:
            print('外部入链需人工核对（不会自动改正式文档）：'+', '.join(plan['inbound']))
        tracked=subprocess.run(['git','-C',str(root),'ls-files','-z'],capture_output=True).stdout.split(b'\0')
        tracked=[p.relative_to(root).as_posix() for p in plan['files'] if os.fsencode(p.relative_to(root)) in tracked]
        if tracked:
            print('提醒：迁移涉及已跟踪文件；索引不改写，迁移后需审查并提交旧路径删除：'+', '.join(tracked))
        if not args.apply:
            print('仅预览，未写入；确认个人文档选择后使用 --apply。')
            return 0
        if (root/'AGENTS.md').read_bytes()!=plan['original'] or any(p.read_bytes()!=data for p,data in plan['originals'].items()):
            raise ValueError('规划期间原件发生变化，请重试')
        ignore=root/'.gitignore'
        if (ignore.read_bytes() if ignore.exists() else None)!=plan['ignore_before']:
            raise ValueError('规划期间 .gitignore 发生变化')
        journal=plan['destination']/'.workflow/migration.json'
        saved={str(p.relative_to(root)):base64.b64encode(data).decode() for p,data in plan['originals'].items()}
        saved['AGENTS.md']=base64.b64encode(plan['original']).decode()
        manifest={'schema':1,'before':saved,'gitignore_before':base64.b64encode(plan['ignore_before']).decode() if plan['ignore_before'] is not None else None,
                  'moves':{str(p.relative_to(root)):str(n.relative_to(root)) for p,n in plan['files'].items()}}
        # Keep migration originals for recovery; this is not a general workspace backup service.
        update.atomic(journal,(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
        for name in ('docs/product','docs/architecture','docs/decisions','docs/guides','reports','references','work/active','work/archive'):
            (plan['destination']/name).mkdir(parents=True,exist_ok=True)
        try:
            for p,data in plan['writes'].items():
                update.atomic(p,data)
            update.atomic(root/'AGENTS.md',plan['agents'])
            update.atomic(ignore,plan['ignore'])
            # Delete originals only after all destination writes and last-minute byte checks.
            for old,data in plan['originals'].items():
                if old.read_bytes()!=data:
                    raise ValueError('原件发生变化，停止删除：'+str(old))
            for old in plan['originals']:
                old.unlink()
        except (OSError,ValueError):
            # Best-effort rollback of source bytes; retain destination and journal for inspection.
            for old,data in plan['originals'].items():
                if not old.exists():
                    update.atomic(old,data)
            update.atomic(root/'AGENTS.md',plan['original'])
            if plan['ignore_before'] is None:
                if ignore.exists(): ignore.unlink()
            else:
                update.atomic(ignore,plan['ignore_before'])
            raise
        print('迁移完成；旧空目录保留，未改 Git 索引。迁移原件记录：'+str(journal))
        print('请运行 check-project.sh --strict，并核对项目正式文档中指向旧位置的链接。')
        return 0
    except (OSError,ValueError,KeyError) as exc:
        print('错误: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
