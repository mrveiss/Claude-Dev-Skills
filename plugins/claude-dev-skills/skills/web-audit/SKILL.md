---
name: web-audit
description: Full security, SEO, and AI-friendliness audit for any website. Runs multi-pass checks covering HTTP headers, DNS/subdomain recon, port scan, TLS, CORS, email spoofing, exposed admin panels, plugin CVEs, open resolvers, FTP, per-page SEO, performance, and compromise indicators. Outputs a self-contained HTML report.
---

# Web Audit

Invoke as `/claude-dev-skills:web-audit <workflow> [args]`; first argument selects the row; no argument → pick the row from the situation.

| Workflow | When | Reference |
|---|---|---|
| `web-audit` | Auditing a website (`/claude-dev-skills:web-audit https://example.com`): security, SEO, AI-friendliness, HTML report | `references/web-audit.md` |
