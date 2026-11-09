/**
 * 스타일 단일 출처 검사 — 모양(색·라운드·그림자)은 src/styles/app/ 의 토큰·클래스로만 그린다.
 *
 * 막는 것
 *   - src/styles/app/ 밖의 .css 파일
 *   - .ts/.tsx 안의 색 리터럴(#hex · rgb() · hsl())
 *   - Tailwind 기본 팔레트 색 클래스(bg-red-500 등)와 임의값 색·라운드(bg-[#fff] · rounded-[6px])
 * 배치(flex·grid·gap·padding)는 Tailwind 유틸을 그대로 쓴다.
 *
 * 실행: npm run lint:styles   (npm run verify 에 포함)
 */
import { readdirSync, readFileSync, statSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const SRC = path.join(ROOT, "src")
const STYLE_DIR = path.join(SRC, "styles", "app")

const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white"
const RULES = [
  { name: "색 리터럴", pattern: /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/ },
  {
    name: "Tailwind 기본 팔레트 색",
    pattern: new RegExp(
      `\\b(?:bg|text|border|ring|fill|stroke|outline|from|to|via)-(?:${PALETTE})(?:-\\d{2,3})?\\b`,
    ),
  },
  { name: "Tailwind 임의값 색·라운드", pattern: /\b(?:bg|text|border|ring|fill|stroke)-\[#|\brounded-\[/ },
]

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })
}

const problems = []
for (const file of walk(SRC)) {
  const rel = path.relative(ROOT, file)
  if (file.endsWith(".css") && !file.startsWith(STYLE_DIR + path.sep)) {
    problems.push(`${rel}: src/styles/app/ 밖의 CSS 파일`)
    continue
  }
  if (!/\.(ts|tsx)$/.test(file) || /\.test\.tsx?$/.test(file)) continue
  readFileSync(file, "utf8")
    .split("\n")
    .forEach((line, index) => {
      for (const rule of RULES) {
        if (rule.pattern.test(line)) problems.push(`${rel}:${index + 1}: ${rule.name} — ${line.trim()}`)
      }
    })
}

if (problems.length > 0) {
  console.error(
    "스타일 규칙 위반 (frontend/CLAUDE.md 「스타일」):\n" + problems.map((p) => `  ${p}`).join("\n"),
  )
  process.exit(1)
}
console.log("check-styles: 위반 없음")
