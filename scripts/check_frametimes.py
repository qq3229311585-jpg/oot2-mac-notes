# Usage: python -I check_frametimes.py <nxnative log>
# Prints: number of segments with p50>34ms, segments with p95>40ms, GPU p50, lowest game-time/real-time ratio.
import re, sys
rows = []; steps = []
for ln in open(sys.argv[1], errors='replace'):
    if 'timing up to frame' in ln:
        m = re.search(r'frame (\d+): frame time p50 ([\d.]+) / p95 ([\d.]+).*?submit\+present p50 ([\d.]+).*?GPU p50 ([\d.]+) / p95 ([\d.]+)', ln)
        if m: rows.append([float(x) for x in m.groups()])
    elif 'frame step: game time' in ln:
        m = re.search(r'\(([\d.]+) of real time\)', ln)
        if m: steps.append(float(m.group(1)))
play = [r for r in rows if r[0] >= 1500]
slow = [r for r in play if r[1] > 34.0]
spiky = [r for r in play if r[1] <= 34.0 and r[2] > 40.0]
gp = sorted(r[4] for r in play)
print('段数', len(play), '| p50>34ms 的段', len(slow), '| p50 正常但 p95>40ms 的段', len(spiky))
print('GPU p50 中位 %.1f / 最大 %.1f ms' % (gp[len(gp)//2], gp[-1]))
print('游戏时间/真实时间 最低', min(steps) if steps else '无')
for r in slow[:12]: print('  慢段 帧%d p50 %.1f p95 %.1f sub %.1f GPU %.1f' % tuple(r[:5]))
