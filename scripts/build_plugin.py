#!/usr/bin/env python3
"""Build a portable XuanShu Agent Plugin containing all local Skills.

This package has no invented HTTPS MCP endpoint: real remote calculation tools
must be connected separately after the user owns a verified public deployment.
The private skills-only plugin is useful for local workflow discovery, not a
substitute for a live calculator or OAuth login.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / 'xuanshu-chatgpt-plugin-v.0.1.0.zip'
TIMESTAMP = (2026, 10, 9, 0, 0, 0)

MANIFEST = {
    '$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
    'name':'xuanshu',
    'version':'0.1.0',
    'description':'Independent Chinese calendar, BaZi, Zi Wei and Qimen cultural calculation skills. A separately authenticated XuanShu MCP endpoint is required for live tool calls.',
    'license':'AGPL-3.0-only',
    'keywords':['chinese-calendar','bazi','ziwei','qimen','audit'],
    'extensions':{'com.openai':{'interface':{
        'displayName':'玄枢 XuanShu',
        'shortDescription':'中国历法与术数计算工作流',
        'longDescription':'独立的历法、八字、紫微和奇门传统计算说明与审计工作流。真实计算工具需要另外连接玄枢 MCP 服务器；不包含在线登录或第三方平台接口。',
        'developerName':'XuanShu',
    }}},
}


def build(output: Path = OUTPUT) -> Path:
    skills = sorted((ROOT/'skills').glob('*/SKILL.md'))
    if len(skills) != 18:
        raise ValueError(f'Expected exactly 18 frozen-version Skills; found {len(skills)}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        entries = {'plugin.json': json.dumps(MANIFEST,ensure_ascii=False,indent=2).encode('utf-8') + b'\n'}
        for path in skills:
            data=path.read_bytes()
            if not data.startswith(b'---\n') or path.stat().st_size > 256*1024:
                raise ValueError(f'Invalid plugin Skill: {path.name}')
            entries[f'skills/{path.parent.name}/SKILL.md']=data
        for name, data in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=TIMESTAMP)
            info.create_system=3
            info.external_attr=(0o100644<<16)
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None and len(z.namelist()) == 19
        assert json.loads(z.read('plugin.json'))['version'] == '0.1.0'
    print(f'Created portable skills-only Plugin: {output} ({output.stat().st_size:,} bytes; 18 skills)')
    return output


if __name__=='__main__':
    build()
