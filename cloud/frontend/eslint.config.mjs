import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  { ignores: ["playwright-report/**", "test-results/**"] },
  ...nextVitals,
  ...nextTypescript,
];

export default eslintConfig;
