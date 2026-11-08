# Engineering workflow installation

Installed six project-local skills from [mattpocock/skills](https://github.com/mattpocock/skills) at revision `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` using Codex's skill-installer helper:

- `tdd`: test-first behavior changes.
- `diagnosing-bugs`: reproduce, investigate and verify fixes.
- `codebase-design`: simple interfaces around substantial functionality.
- `domain-modeling`: shared terminology and domain assumptions.
- `code-review`: review behavior against requirements and code standards.
- `writing-for-agents`: maintain useful project instructions.

They live under `.agents/skills/` and will be available on the next turn. These are editable project-local copies; this is not an auto-updating global plugin installation. The original MIT license is retained as `.agents/skills/MATT-POCOCK-LICENSE.txt`. Referenced supporting files within each selected skill are included.

FinPilot-specific conventions live in `AGENTS.md`, terminology in `GLOSSARY.md`, and integration contracts in `docs/api-contracts.md`. This setup uses local documentation rather than creating external issues or requiring a tracker. It does not run the upstream interactive setup workflow or claim to install the entire upstream collection.

Run the existing checks with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

These workflows help expose assumptions and catch mistakes. They do not guarantee correctness, replace meaningful tests or change the trained spending models.
