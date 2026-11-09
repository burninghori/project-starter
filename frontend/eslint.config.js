import js from "@eslint/js"
import jsxA11y from "eslint-plugin-jsx-a11y"
import reactHooks from "eslint-plugin-react-hooks"
import globals from "globals"
import tseslint from "typescript-eslint"

// 데이터 호출은 fetchJson 한 경로로만 한다(기조 1·2). 화면이 fetch 를 직접 부르면 오류 계약·요청 ID 처리가 빠진다.
const RAW_FETCH_BAN = {
  selector: "CallExpression[callee.name='fetch']",
  message: "fetch 를 직접 부르지 않는다 — @/api/transport 의 fetchJson 을 쓴다.",
}

// 모양은 app-* 클래스와 토큰으로만 그린다. 인라인 style 은 계산된 위치·크기(드래그 등)에만 쓴다.
const INLINE_STYLE_BAN = {
  selector: "JSXAttribute[name.name='style'] > JSXExpressionContainer > ObjectExpression",
  message: "인라인 style 객체 대신 app-* 클래스나 Tailwind 배치 유틸을 쓴다(frontend/CLAUDE.md 「스타일」).",
}

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**", "docs/design/mockups/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser },
    },
    plugins: { "react-hooks": reactHooks, "jsx-a11y": jsxA11y },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      "no-restricted-syntax": ["error", RAW_FETCH_BAN, INLINE_STYLE_BAN],
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
  {
    // fetch 를 실제로 부르는 유일한 자리와 그 테스트
    files: ["src/api/transport.ts", "src/api/transport.test.ts"],
    rules: { "no-restricted-syntax": ["error", INLINE_STYLE_BAN] },
  },
  {
    files: ["scripts/**/*.mjs", "*.config.{js,ts}"],
    languageOptions: { globals: { ...globals.node } },
  },
)
