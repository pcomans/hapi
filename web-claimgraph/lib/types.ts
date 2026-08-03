// Types for the baked claim-graph artifact (data/claim-graph.json), produced by the
// Python generator (pipeline/pipeline/authority/claimgraph). Field names are snake_case
// inside records (Python dataclass asdict) and camelCase for the top-level containers.

export interface RulerNode {
  id: string;
  source_id: string;
  local_id: string;
  display_name: string;
  dynasty: number | null;
  dynasty_label: string | null;
  reign_start_bce: number | null;
  reign_end_bce: number | null;
  stage_group: string | null;
}

export interface Claim {
  id: string;
  subject_id: string;
  predicate: string;
  value_text: string;
  value_translit: string | null;
  is_variant: boolean;
  scholar_id: string;
  scholar_name: string;
  publication_id: string;
  publication_citation: string;
  cited_page: number | null;
  cited_pdf_page: string | null;
}

export interface IntraSourceIdentity {
  subject_id: string;
  object_id: string;
  scholar_name: string;
  publication_citation: string;
}

export interface MatchEdge {
  candidate_id: string;
  a_id: string;
  b_id: string;
  a_source: string;
  b_source: string;
  a_name: string;
  b_name: string;
  basis: string;
  shared_prenomen_keys: string[];
  reason: string;
  reviewer: string;
}

export interface Escalation {
  candidate_id: string;
  a_id: string;
  b_id: string;
  a_source: string;
  b_source: string;
  a_name: string;
  b_name: string;
  basis: string;
  reason: string;
  homonym_trap: string | null;
  reviewer: string;
}

export interface IdentityCluster {
  id: string;
  member_ids: string[];
  sources: string[];
  source_count: number;
  label: string;
  edges: Array<{ a_id: string; b_id: string; basis: string }>;
}

export interface ClaimGraphMeta {
  generatedNote: string;
  reviewer: "llm" | "deterministic";
  model: string | null;
  partial: boolean;
  sources: Record<string, { label: string; rulers: number }>;
  stats: {
    rulers: number;
    claims: number;
    candidates: number;
    approvedLinks: number;
    escalations: number;
    intraSourceIdentities: number;
    clusters: number;
    multiSourceClusters: number;
  };
}

export interface ClaimGraphArtifact {
  meta: ClaimGraphMeta;
  rulers: RulerNode[];
  claims: Claim[];
  intraSourceIdentities: IntraSourceIdentity[];
  approvedEdges: MatchEdge[];
  escalations: Escalation[];
  clusters: IdentityCluster[];
}

export const SOURCE_ORDER = [
  "leprohon",
  "beckerath",
  "kitchen",
  "pharaoh_se",
  "ryholt",
] as const;

export const SOURCE_SHORT: Record<string, string> = {
  leprohon: "Leprohon",
  beckerath: "Beckerath",
  kitchen: "Kitchen",
  pharaoh_se: "pharaoh.se",
  ryholt: "Ryholt",
};

export const PREDICATE_LABEL: Record<string, string> = {
  "hapi:display_name": "display name",
  "hapi:prenomen": "throne name (prenomen)",
  "hapi:horus_name": "Horus name",
  "hapi:nomen": "birth name (nomen)",
  "hapi:in_dynastic_period": "dynasty",
};
