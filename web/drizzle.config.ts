import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  // Only introspect the catalog schema (pipeline-owned data tables).
  // The web schema is managed by Drizzle migrations separately.
  // Without this filter, introspection would pull web.* tables into
  // the generated schema, breaking the ownership boundary (ADR-011).
  schemaFilter: ["catalog"],
  out: "./src/lib/db",
});
