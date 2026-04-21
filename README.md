# liulei53/skills

Hermes skills collection.

## Available skills

- `daily-earnings-briefing` — A股+美股每日财报自动扫描与 AI 分析推送系统
- `tech-earnings-deepdive` — 科技股财报深度分析与多视角投资备忘录
- `project-deployer`
- `english-learner-for-programmers`
- `pdf`

## Install a skill manually

Clone the repo and copy the target skill directory into your Hermes skills folder.

### Example: install `daily-earnings-briefing`

```bash
git clone https://github.com/liulei53/skills.git /tmp/liulei53-skills
mkdir -p ~/.hermes/skills/finance
cp -r /tmp/liulei53-skills/daily-earnings-briefing ~/.hermes/skills/finance/
```

Then in Hermes, load it with:

```text
skill_view(name="daily-earnings-briefing")
```

## Notes

- Some skills include scripts or reference files; copy the whole directory, not just `SKILL.md`.
- After copying, restart Hermes only if your environment caches skill listings. Usually not required.
- For `daily-earnings-briefing`, also read the included `scripts/earnings_scanner.py` and follow the deployment steps in `SKILL.md`.
