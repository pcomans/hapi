-- Create Postgres schemas for data and web ownership separation.
-- Catalog tables (artifacts, raw data) live in 'catalog.*'.
-- Web app tables (users, settings) live in 'web.*'.
-- Both share the same database. See ADR-011.

CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS web;
