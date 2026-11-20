#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix network_discovery.py for Windows - replace get_rtt."""

with open('data/network_discovery.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = 0
for i, line in enumerate(lines):
    if line.strip().startswith('def get_rtt(ip):'):
        new_lines.append(line)
        new_lines.append('    try:\n')
        new_lines.append('        r = subprocess.run(["ping","-n","3","-w","2000",ip],\n')
        new_lines.append('                           capture_output=True, text=True, timeout=12)\n')
        new_lines.append('        out = r.stdout\n')
        new_lines.append('        m = re.search(r"min/avg/max/mdev = [\\d.]+/([\\d.]+)/\\d+/\\d+", out)\n')
        new_lines.append('        if m: return m.group(1)\n')
        new_lines.append('        m = re.search(r"Время\\s*=\\s*([\\d.]+)", out)\n')
        new_lines.append('        if m: return m.group(1)\n')
        new_lines.append('        m = re.search(r"time=([\\d.]+)", out)\n')
        new_lines.append('        if m: return m.group(1)\n')
        new_lines.append('    except Exception:\n')
        new_lines.append('        pass\n')
        new_lines.append('    return "-"\n')
        new_lines.append('\n')
        skip = 7
        continue
    if skip > 0:
        skip -= 1
        continue
    new_lines.append(line)

with open('data/network_discovery.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('UPDATED')