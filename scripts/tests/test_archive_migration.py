import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[2]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'项目 空格';self.root.mkdir()
        template=(SOURCE/'scripts/tests/fixtures/agents-1.2.2.md').read_text()
        (self.root/'AGENTS.md').write_text(template+'\n## 项目补充\n保留自定义命令。\n')
        task=self.root/'work/archive/20260101-auth';task.mkdir(parents=True)
        self.handoff=task/'handoff.md'
        self.handoff.write_text('''---
task: 20260101-auth
status: done
phase: close
owner: tester
updated: 2026-01-01 12:00
branch: fix/auth
---
# 登录调查
## Goal
解释令牌刷新与失效场景。
## References
- [指南](../../../docs/guides/auth.md#refresh)
- [正式手册](../../../docs/manual.md)
''')
        (task/'brief.md').write_text('# 登录问题\nToken refresh\n')
        (task/'plan.md').write_text('done')
        (task/'scratch').mkdir();(task/'scratch/noise.md').write_text('discard-secret-search')
        guides=self.root/'docs/guides';guides.mkdir(parents=True)
        (guides/'auth.md').write_text('# 令牌刷新\n[任务](../../work/archive/20260101-auth/handoff.md)\n[手册](../manual.md)\n![图](auth.png)\n')
        (guides/'auth.png').write_bytes(b'image-bytes')
        (self.root/'docs/manual.md').write_text('团队正式文档不移动')
        self.cmd('git','init','-b','main')

    def cmd(self,*args,code=0):
        p=subprocess.run(args,cwd=self.root,text=True,capture_output=True)
        self.assertEqual(p.returncode,code,p.stdout+p.stderr)
        return p.stdout

    def tool(self,name,*args,code=0):
        return self.cmd(sys.executable,str(SOURCE/'scripts'/name),str(self.root),*args,code=code)

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}

    def migrate(self):
        return self.tool('migrate-project.py','--personal-doc','docs/guides','--apply')

    def test_preview_moves_links_state_and_search(self):
        (self.root/'docs/manual.md').write_text('团队正式文档不移动\n[历史任务](../work/archive/20260101-auth/handoff.md)')
        before=self.snapshot()
        preview=self.tool('migrate-project.py','--personal-doc','docs/guides')
        self.assertIn('外部入链需人工核对',preview)
        self.assertEqual(before,self.snapshot())
        self.migrate()
        self.assertFalse(self.handoff.exists())
        migrated=self.root/'.agent/work/archive/20260101-auth/handoff.md'
        self.assertIn('../../../docs/guides/auth.md#refresh',migrated.read_text())
        self.assertIn('../../../../docs/manual.md',migrated.read_text())
        guide=self.root/'.agent/docs/guides/auth.md'
        self.assertIn('../../../docs/manual.md',guide.read_text())
        self.assertEqual((guide.parent/'auth.png').read_bytes(),b'image-bytes')
        self.assertIn('团队正式文档不移动', (self.root/'docs/manual.md').read_text())
        agents=(self.root/'AGENTS.md').read_text()
        self.assertIn('workflow_root: .agent',agents)
        self.assertIn('保留自定义命令',agents)
        self.assertNotIn('把 `handoff.md` 一并提交',agents)
        self.tool('update-project.py','--check')
        result=json.loads(self.tool('archive-index.py','--query','刷新 Token','--json'))
        self.assertEqual(len(result),1)
        self.assertTrue(any(d['path'].endswith('brief.md') for d in result[0]['documents']))
        self.assertEqual(json.loads(self.tool('archive-index.py','--query','discard-secret-search','--json')),[])
        before_query=self.snapshot()
        self.tool('archive-index.py','--query','令牌')
        self.assertEqual(before_query,self.snapshot())
        self.tool('archive-index.py','--write')
        index=self.root/'.agent/.workflow/archive-index.json'
        self.assertEqual(len(json.loads(index.read_text())['tasks']),1)
        migrated.write_text(migrated.read_text().replace('令牌刷新','全新描述'))
        self.assertEqual(len(json.loads(self.tool('archive-index.py','--query','全新描述','--json'))),1)
        self.tool('migrate-project.py','--apply',code=1)

    def test_unselected_docs_and_custom_target(self):
        self.tool('migrate-project.py','--workflow-root','agent-work','--apply')
        self.assertTrue((self.root/'docs/guides/auth.md').exists())
        h=self.root/'agent-work/work/archive/20260101-auth/handoff.md'
        self.assertIn('../../../../docs/guides/auth.md#refresh',h.read_text())
        self.tool('update-project.py','--check')

    def test_conflict_existing_target_and_invalid_personal_selection_zero_write(self):
        before=self.snapshot()
        self.tool('migrate-project.py','--personal-doc','docs','--apply',code=1)
        self.assertEqual(before,self.snapshot())
        file=self.root/'AGENTS.md'
        file.write_text(file.read_text().replace('以下四条不可省略：','以下四条不可省略：\n定制规则。'))
        before=self.snapshot()
        self.tool('migrate-project.py','--apply',code=1)
        self.assertEqual(before,self.snapshot())
        (self.root/'.agent').mkdir()
        self.tool('migrate-project.py','--apply',code=1)

    def test_task_and_doc_symlinks_refused(self):
        (self.handoff.parent/'link').symlink_to(self.root/'docs/manual.md')
        before=self.snapshot()
        self.tool('migrate-project.py','--apply',code=1)
        self.assertEqual(before,self.snapshot())

    def test_archive_missing_handoff_reports_incomplete(self):
        self.migrate()
        (self.root/'.agent/work/archive/bad').mkdir()
        self.tool('archive-index.py','--json',code=1)

    def test_custom_legacy_paths(self):
        file=self.root/'AGENTS.md'
        file.write_text(file.read_text().replace('tasks_root: work','tasks_root: tasks').replace('docs_root: docs','docs_root: knowledge').replace('work/','tasks/').replace('docs/','knowledge/'))
        (self.root/'work').rename(self.root/'tasks')
        (self.root/'docs').rename(self.root/'knowledge')
        self.tool('migrate-project.py','--personal-doc','knowledge/guides','--apply')
        self.tool('update-project.py','--check')


if __name__=='__main__':
    unittest.main()
