"""End-to-end migration tests: real files and subprocesses, no external dependencies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / '项目 空格'
        self.root.mkdir()
        self.legacy = json.loads((SOURCE / 'references/legacy-workflow-rules.json').read_text())
        self.old = (SOURCE / 'templates/AGENTS.md').read_text()
        # Replace only generic sections; project-specific text and navigation stay distinct.
        start = self.old.index('## 工作流铁律（必须遵守）')
        end = self.old.index('## 目录导航')
        self.old = self.old[:start] + self.legacy['2.0.2']['工作流铁律（必须遵守）'] + self.old[end:]
        self.old = self.old.replace('.agent', '个人工作').replace('<命令>', 'npm run project-only')
        self.old += '\n## 自定义规则\n\n保留这条项目规则。\n'
        (self.root / 'AGENTS.md').write_text(self.old)
        self.work = self.root / '个人工作'
        (self.work / 'work/active/existing').mkdir(parents=True)
        (self.work / 'work/active/existing/handoff.md').write_text('existing task bytes\n')
        self.state = self.work / '.workflow/state.json'

    def run_tool(self, *args, code=0, source=SOURCE):
        p = subprocess.run([sys.executable, str(source / 'scripts/update-project.py'), str(self.root), *args],
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return p.stdout

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def backup_id(self):
        return sorted((self.work / '.workflow/backups').iterdir())[-1].name

    def test_preview_apply_idempotency_restore(self):
        before = self.snapshot()
        self.assertIn('未知', self.run_tool())
        self.assertEqual(before, self.snapshot())
        self.run_tool('--check', code=3)
        self.assertEqual(before, self.snapshot())
        self.run_tool('--apply')
        text = (self.root / 'AGENTS.md').read_text()
        self.assertIn('个人工作/docs/guides/', text)
        self.assertIn('npm run project-only', text)
        self.assertIn('保留这条项目规则', text)
        self.assertIn('workflow_root: 个人工作', text)
        self.assertEqual((self.work / 'work/active/existing/handoff.md').read_text(), 'existing task bytes\n')
        after = self.snapshot()
        self.run_tool('--apply')
        self.run_tool('--check')
        self.assertEqual(after, self.snapshot())
        self.run_tool('--restore', self.backup_id())
        self.assertEqual((self.root / 'AGENTS.md').read_text(), self.old)
        self.assertFalse(self.state.exists())

    def test_legacy_custom_rules_conflict_without_any_write(self):
        file = self.root / 'AGENTS.md'
        file.write_text(self.old.replace('以下四条不可省略：', '以下四条不可省略：\n项目专用补充。'))
        before = self.snapshot()
        self.run_tool('--apply', code=2)
        self.assertEqual(before, self.snapshot())

    def test_future_update_uses_baseline_and_preserves_other_sections(self):
        self.run_tool('--apply')
        fake = Path(self.temp.name) / 'next-skill'
        for name in ['scripts', 'templates', 'references']:
            shutil.copytree(SOURCE / name, fake / name)
        (fake / 'VERSION').write_text('2.0.5\n')
        template = fake / 'templates/AGENTS.md'
        template.write_text(template.read_text().replace('不可省略：', '不可省略（新版）：'))
        self.run_tool('--sync', source=fake)
        self.assertEqual(json.loads(self.state.read_text())['version'], '2.0.5')
        self.assertIn('不可省略（新版）', (self.root / 'AGENTS.md').read_text())
        self.assertIn('保留这条项目规则', (self.root / 'AGENTS.md').read_text())
        self.run_tool('--check', code=1)  # no silent downgrade
        # Restore the second upgrade, including the previous version state.
        self.run_tool('--restore', self.backup_id(), source=fake)
        self.assertEqual(json.loads(self.state.read_text())['version'], '2.0.4')

    def test_post_upgrade_edit_blocks_update_and_restore(self):
        self.run_tool('--apply')
        backup = self.backup_id()
        file = self.root / 'AGENTS.md'
        file.write_text(file.read_text().replace('不可省略：', '本地自定义：'))
        before = self.snapshot()
        self.run_tool('--apply', code=2)
        self.run_tool('--restore', backup, code=1)
        self.assertEqual(before, self.snapshot())

    def test_state_edit_blocks_restore(self):
        self.run_tool('--apply')
        self.state.write_text(self.state.read_text() + ' ')
        before = self.snapshot()
        self.run_tool('--restore', self.backup_id(), code=1)
        self.assertEqual(before, self.snapshot())

    def test_invalid_mapping_and_old_layout_refused(self):
        file = self.root / 'AGENTS.md'
        for field in ['workflow_root: ../escape', 'tasks_root: work', 'workflow_root: /tmp/escape',
                      'workflow_root: .', 'workflow_root: 个人工作\nworkflow_root: other']:
            with self.subTest(field=field):
                file.write_text(self.old.replace('workflow_root: 个人工作', field))
                before = self.snapshot()
                self.run_tool('--apply', code=1)
                self.assertEqual(before, self.snapshot())

    def test_symlink_escape_refused(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'escape').symlink_to(outside, target_is_directory=True)
        file = self.root / 'AGENTS.md'
        file.write_text(self.old.replace('workflow_root: 个人工作', 'workflow_root: escape'))
        self.run_tool('--apply', code=1)
        self.assertFalse(list(outside.iterdir()))

    def test_duplicate_heading_and_tampered_backup_refused(self):
        file = self.root / 'AGENTS.md'
        file.write_text(self.old + '\n## 文档写入前检查\nA\n## 文档写入前检查\nB\n')
        self.run_tool('--apply', code=1)
        file.write_text(self.old)
        self.run_tool('--apply')
        backup = self.backup_id()
        (self.work / '.workflow/backups' / backup / 'AGENTS.md').write_text('tampered')
        before = self.snapshot()
        self.run_tool('--restore', backup, code=1)
        self.assertEqual(before, self.snapshot())

    def test_203_rules_adopted_and_project_mode_preserved(self):
        file = self.root / 'AGENTS.md'
        start = self.old.index('## 工作流铁律（必须遵守）')
        end = self.old.index('## 目录导航')
        blocks = ''.join(self.legacy['2.0.3'].values()).replace('.agent/', '个人工作/')
        file.write_text(self.old[:start] + blocks + self.old[end:])
        file.chmod(0o640)
        self.run_tool('--apply')
        self.assertEqual(file.stat().st_mode & 0o777, 0o640)
        self.run_tool('--check')

    def test_deleted_managed_section_is_not_silently_recreated(self):
        self.run_tool('--apply')
        file = self.root / 'AGENTS.md'
        text = file.read_text()
        start = text.index('## 工作流铁律（必须遵守）')
        end = text.index('## 目录导航')
        file.write_text(text[:start] + text[end:])
        before = self.snapshot()
        self.run_tool('--apply', code=2)
        self.assertEqual(before, self.snapshot())

    def test_headings_inside_code_fences_are_preserved(self):
        file = self.root / 'AGENTS.md'
        file.write_text(self.old + '\n```markdown\n## 文档写入前检查\n示例，不是规则。\n```\n')
        self.run_tool('--apply')
        self.assertIn('```markdown\n## 文档写入前检查\n示例，不是规则。\n```', file.read_text())
        self.run_tool('--check')

    def test_metadata_symlink_refused(self):
        outside = Path(self.temp.name) / 'metadata-outside'
        outside.mkdir()
        (self.work / '.workflow').symlink_to(outside, target_is_directory=True)
        self.run_tool('--apply', code=1)
        self.assertFalse(list(outside.iterdir()))

    def test_fresh_init_baseline_and_existing_init_nonoverwrite(self):
        root = Path(self.temp.name) / 'fresh'
        root.mkdir()
        def init():
            result = subprocess.run(['bash', str(SOURCE / 'scripts/init-project.sh'), str(root),
                                     '--workflow-root', 'agent-work'], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        init()
        state = root / 'agent-work/.workflow/state.json'
        self.assertEqual(json.loads(state.read_text())['version'], '2.0.4')
        file = root / 'AGENTS.md'
        file.write_text(file.read_text() + '\n## 项目规则\n不能覆盖。\n')
        before = file.read_bytes()
        init()
        self.assertEqual(file.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
