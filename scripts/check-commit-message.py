#!/usr/bin/env python3
"""Validate the message Git is about to commit, never the previous commit."""
from pathlib import Path
import re
import sys

try:
    lines = Path(sys.argv[1]).read_text().splitlines()
    subject = next((line for line in lines if line.strip() and not line.startswith('#')), '')
    valid = re.fullmatch(r'(?:[a-z]+\([^()]+\)|[0-9]+\.[0-9]+\.[0-9]+): \S.*', subject)
    # Git-generated merge/revert subjects keep normal integration usable.
    generated = re.fullmatch(r'(?:Merge (?:branch|remote-tracking branch|pull request) .+|Revert ".+")', subject)
    if not (valid or generated):
        sys.exit('提交信息不符合约定：<type>(<任务或模块>): <说明>，或 <版本>: <说明>')
except (OSError, IndexError) as exc:
    sys.exit('无法读取本次提交信息: ' + str(exc))
