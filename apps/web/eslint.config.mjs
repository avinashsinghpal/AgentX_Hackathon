import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    rules: {
      "@next/next/no-img-element": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/purity": "off",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "public/**"],
  },
];

export default config;
