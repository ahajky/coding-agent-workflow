import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta

SOURCE = Path(__file__).resolve().parents[2]


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo 空格'
        self.root.mkdir()
        self.cmd('git', 'init', '-b', 'main')
        self.cmd('git', 'config', 'user.name', 'Test')
        self.cmd('git', 'config', 'user.email', 'test@example.invalid')
        self.script('init-project.sh', str(self.root))
        self.script('init-task.sh', '.agent/work/active/20261112-test', '--title', 'A&B / C|D')
        self.task = self.root / '.agent/work/active/20261112-test'
        self.handoff = self.task / 'handoff.md'
        self.handoff.write_text(self.handoff.read_text().replace('owner: <负责人：人 或 agent>', 'owner: tester'))
        (self.root / 'README.md').write_text('test\n')
        (self.root / 'code.txt').write_text('code\n')
        self.cmd('git', 'add', '.gitignore', 'README.md', 'code.txt')

    def cmd(self, *args, code=0, cwd=None):
        env = os.environ.copy()
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        result = subprocess.run(args, cwd=cwd or self.root, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def script(self, name, *args, code=0, cwd=None):
        return self.cmd('bash', str(SOURCE / 'scripts' / name), *args, code=code, cwd=cwd)

    def check(self, code=0):
        return self.script('check-project.sh', str(self.root), '--strict', code=code)

    def hooks(self):
        self.script('install-git-hooks.sh', str(self.root), cwd=Path(self.temp.name))

    def test_real_commit_message_and_forced_workflow_staging(self):
        self.hooks()
        self.cmd('git', 'commit', '-m', 'bad msg', code=1)
        self.cmd('git', 'commit', '-m', 'feat(test): valid')
        self.cmd('git', 'add', '-f', '.agent/work/active/20261112-test/handoff.md')
        self.assertIn('已被 Git 跟踪', self.cmd('git', 'commit', '-m', 'feat(test): forced', code=1))
        self.cmd('git', 'rm', '--cached', '.agent/work/active/20261112-test/handoff.md')
        (self.root / 'code.txt').write_text('next\n')
        self.cmd('git', 'add', 'code.txt')
        self.cmd('git', 'commit', '-m', 'fix(test): next')
        self.cmd('git', 'commit', '--allow-empty', '-m', 'bad again', code=1)

    def test_shared_agents_is_explicit(self):
        self.cmd('git', 'add', '-f', 'AGENTS.md')
        self.assertIn('workflow_shared_agents', self.check(code=1))
        file = self.root / 'AGENTS.md'
        file.write_text(file.read_text().replace('workflow_root:', 'workflow_shared_agents: true\nworkflow_root:', 1))
        self.check(code=1)  # un-staged permission cannot authorize staged shared rules
        self.cmd('git', 'add', '-f', 'AGENTS.md')
        self.check()

    def test_hook_path_failure_and_preflight_nonoverwrite(self):
        hooks = self.root / '.git/hooks'
        (hooks / 'commit-msg').write_text('#!/bin/sh\nexit 0\n')
        self.script('install-git-hooks.sh', str(self.root), code=1)
        self.assertFalse((hooks / 'pre-commit').exists())
        (hooks / 'commit-msg').unlink()
        self.hooks()
        self.cmd('git', 'config', 'codingAgentWorkflow.scripts', '/missing/skill')
        self.assertIn('阻止提交', self.cmd('git', 'commit', '-m', 'feat(test): missing', code=1))

    def test_custom_hookspath_outside_calling_cwd(self):
        self.cmd('git', 'config', 'core.hooksPath', '.custom-hooks')
        self.hooks()
        self.assertTrue((self.root / '.custom-hooks/pre-commit').exists())
        self.cmd('git', 'commit', '-m', 'invalid', code=1)
        self.cmd('git', 'commit', '-m', '2.0.5: valid')

    def test_required_files_and_lifecycle(self):
        self.check()
        (self.task / 'brief.md').unlink()
        self.assertIn('brief.md', self.check(code=1))
        (self.task / 'brief.md').write_text('brief')
        self.handoff.write_text(self.handoff.read_text().replace('status: planned', 'status: done'))
        self.assertIn('仍留在 active', self.check(code=1))
        self.handoff.write_text(self.handoff.read_text().replace('phase: discover', 'phase: close'))
        archived = self.root / '.agent/work/archive/20261112-test'
        self.task.rename(archived)
        self.check()
        file = archived / 'handoff.md'
        file.write_text(file.read_text().replace('status: done', 'status: in_progress'))
        self.assertIn('归档任务必须', self.check(code=1))

    def test_quotes_crlf_future_time_and_empty_fields(self):
        original = self.handoff.read_text()
        text = original.replace('status: planned', 'status: "planned"').replace('phase: discover', "phase: 'discover'")
        self.handoff.write_bytes(text.replace('\n', '\r\n').encode())
        self.check()
        future = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M')
        lines = original.splitlines()
        self.handoff.write_text('\n'.join('updated: '+future if l.startswith('updated:') else l for l in lines))
        self.assertIn('未来时间', self.check(code=1))
        self.handoff.write_text(original.replace('owner: tester', 'owner:').replace('branch: main', 'branch: <pending>'))
        self.assertIn('负责人未填', self.check(code=1))

    def test_remote_branch_and_missing_entry(self):
        self.cmd('git', 'commit', '-m', '2.0.5: init')
        self.cmd('git', 'update-ref', 'refs/remotes/origin/fix/test', 'HEAD')
        self.handoff.write_text(self.handoff.read_text().replace('branch: main', 'branch: fix/test'))
        self.assertNotIn('找不到', self.check())
        (self.root / 'AGENTS.md').unlink()
        output = self.check(code=1)
        self.assertIn('缺少必需项', output)
        self.assertNotIn('awk:', output)

    def test_paths_and_literal_titles(self):
        self.assertIn('A&B / C|D', (self.task / 'brief.md').read_text())
        self.assertTrue((self.task / 'scratch').is_dir())
        self.script('init-project.sh', str(self.root), '--workflow-root', '../escape', code=2)
        self.assertFalse((self.root.parent / 'escape').exists())
        source = self.root / 'ref.txt'
        source.write_text('source')
        self.script('import-reference.sh', str(source), '--root', str(self.root), '--name', '../../escape', code=2)
        outside = self.root.parent / 'outside'
        outside.mkdir()
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        self.script('init-project.sh', str(self.root), '--workflow-root', 'linked', code=2)
        self.assertFalse(list(outside.iterdir()))
        self.script('import-reference.sh', str(source), '--root', str(self.root), '--name', 'good')
        self.assertEqual((self.root / '.agent/references/good').read_text(), 'source')

    def test_linked_worktree_hook_installation(self):
        self.cmd('git', 'commit', '-m', '2.0.5: base')
        worktree = self.root.parent / 'linked-worktree'
        self.cmd('git', 'worktree', 'add', '-b', 'feature', str(worktree))
        self.script('init-project.sh', str(worktree))
        self.script('install-git-hooks.sh', str(worktree), cwd=self.root.parent)
        self.cmd('git', 'commit', '--allow-empty', '-m', 'invalid', code=1, cwd=worktree)
        self.cmd('git', 'commit', '--allow-empty', '-m', 'feat(test): worktree', cwd=worktree)

    def test_root_scalars_duplicates_and_dangling_links(self):
        source = self.root / 'ref.txt'
        source.write_text('source')
        target = self.root / '.agent/references/dangling'
        target.symlink_to(self.root.parent / 'missing')
        self.script('import-reference.sh', str(source), '--root', str(self.root), '--name', 'dangling', code=2)
        file = self.root / 'AGENTS.md'
        original = file.read_text()
        file.write_text(original.replace('workflow_root: .agent', 'workflow_root: ".agent"'))
        self.check()
        file.write_text(original.replace('workflow_root: .agent', 'workflow_root: .agent\nworkflow_root: other'))
        self.check(code=1)

    def test_failed_branch_leaves_no_task(self):
        self.script('init-task.sh', '.agent/work/active/20261112-bad', '--branch', 'bad branch', code=128)
        self.assertFalse((self.root / '.agent/work/active/20261112-bad').exists())


if __name__ == '__main__':
    unittest.main()
