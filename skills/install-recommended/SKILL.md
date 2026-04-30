<!-- SCOPE: both -->
---
name: install-recommended
description: Detect project stack and recommend relevant skills to install
invoke: /install-recommended
version: 1.0.0
audience: project
triggers: ["/install-recommended", "/recommend-skills", "/stack-skills"]
platforms: ["claude-code"]
prerequisites: []
---

# /install-recommended

> Detect your project's technology stack and recommend skills to install.

## What It Does

Scans the project root for technology indicators (package.json, go.mod, pyproject.toml, config files, Dockerfile, etc.), identifies the stack, and recommends skills that match the detected technologies. Supports individual technology skills, combo detection (React + TypeScript), and multiple skill sources (cos-builtin, skills.sh, community).

## Usage

```
/install-recommended            # Detect stack and show recommendations
/install-recommended --install  # Detect and install recommended skills
```

## Steps

1. **Detect project stack**
   - Run `StackSkillRecommender.detect_stack(project_path)` from `lib/stack_skill_recommender.py`
   - Report detected technologies to the user

2. **Generate recommendations**
   - Run `StackSkillRecommender.recommend(project_path)`
   - Includes individual technology skills and combo skills
   - Deduplicates and sorts by priority (recommended > optional > suggested)

3. **Show recommendations**
   - Display formatted recommendations with priority tags
   - Group by source: cos-builtin (invoke directly) vs external (install command)
   - Show install commands for external skills

4. **Install selected skills** (if --install or user confirms)
   - For cos-builtin skills: inform the user they are available via invoke command
   - For skills.sh skills: run the `npx skills add ...` command
   - Report installation results

## Detection Coverage

| Technology | Detection Signal |
|------------|-----------------|
| Go | `go.mod` |
| TypeScript | `tsconfig.json` |
| Python | `pyproject.toml`, `setup.py`, `requirements.txt` |
| Rust | `Cargo.toml` |
| Java | `build.gradle`, `pom.xml` |
| React | `react` in package.json dependencies |
| Next.js | `next.config.*` or `next` in package.json |
| Vue | `vue` in package.json |
| Angular | `@angular/core` in package.json |
| Svelte | `svelte.config.js` or `svelte` in package.json |
| NestJS | `@nestjs/core` in package.json |
| Express | `express` in package.json |
| FastAPI | `fastapi` in pyproject.toml/requirements.txt |
| Django | `django` in pyproject.toml/requirements.txt |
| Flask | `flask` in pyproject.toml/requirements.txt |
| Docker | `Dockerfile`, `docker-compose.yml` |
| Tailwind | `tailwind.config.*` |
| Supabase | `supabase/` directory or `@supabase/supabase-js` |
| Prisma | `prisma/schema.prisma` or `prisma` in package.json |
| Terraform | `main.tf`, `terraform.tf` |

## Combo Detection

When multiple technologies are detected together, more specific skills are recommended:

| Combo | Recommended Skill |
|-------|------------------|
| React + TypeScript | react-typescript |
| Next.js + Supabase | nextjs-supabase |
| Next.js + Tailwind | nextjs-tailwind |
| Python + FastAPI | fastapi-full |
| Go + Docker | go-docker |

## Success Criteria

- [ ] Stack detection runs without errors
- [ ] At least one technology detected (or empty message for bare projects)
- [ ] Recommendations sorted by priority
- [ ] Install commands are valid and executable

## Verification

```bash
python3 -c "
from lib.stack_skill_recommender import StackSkillRecommender
r = StackSkillRecommender()
recs = r.recommend('.')
print(r.format_recommendations(recs))
"
```
