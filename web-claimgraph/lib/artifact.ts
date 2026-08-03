import "server-only";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ClaimGraphArtifact } from "./types";

// Read the baked artifact from disk at module load rather than importing the JSON, so
// tsc doesn't infer a multi-megabyte literal type. The file is force-included in the
// serverless bundle via `outputFileTracingIncludes` in next.config.ts.
const path = join(process.cwd(), "data", "claim-graph.json");

export const artifact = JSON.parse(readFileSync(path, "utf8")) as ClaimGraphArtifact;
