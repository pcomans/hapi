-- Create Postgres schemas for pipeline and web ownership separation.
-- Pipeline tables live in 'pipeline.*', web app tables live in 'web.*'.
-- Both share the same database. See ADR-011.

CREATE SCHEMA IF NOT EXISTS pipeline;
CREATE SCHEMA IF NOT EXISTS web;
