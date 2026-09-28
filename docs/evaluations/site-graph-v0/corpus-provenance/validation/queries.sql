\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on

-- Re-run with:
--   psql "$DATABASE_URL" -f validation/queries.sql > validation/results.json
--
-- The output is one JSON object. Null field counts are descriptive rather than
-- failures: the canonical corpus intentionally preserves sparse source data.

WITH
raw AS (
    SELECT 'met'::text AS museum, object_id FROM catalog.raw_met
    UNION ALL
    SELECT 'brooklyn', object_id FROM catalog.raw_brooklyn
    UNION ALL
    SELECT 'harvard', object_id FROM catalog.raw_harvard
),
artifact_counts AS (
    SELECT jsonb_object_agg(source_museum, row_count ORDER BY source_museum) AS value
    FROM (
        SELECT source_museum, count(*) AS row_count
        FROM catalog.artifacts
        GROUP BY source_museum
    ) counts
),
raw_counts AS (
    SELECT jsonb_object_agg(museum, row_count ORDER BY museum) AS value
    FROM (
        SELECT museum, count(*) AS row_count
        FROM raw
        GROUP BY museum
    ) counts
),
raw_only_counts AS (
    SELECT jsonb_object_agg(museum, row_count ORDER BY museum) AS value
    FROM (
        SELECT r.museum, count(*) FILTER (WHERE a.id IS NULL) AS row_count
        FROM raw r
        LEFT JOIN catalog.artifacts a
          ON a.source_museum = r.museum
         AND a.source_id = r.object_id
        GROUP BY r.museum
    ) counts
),
artifact_columns AS (
    SELECT jsonb_agg(column_name ORDER BY ordinal_position) AS value
    FROM information_schema.columns
    WHERE table_schema = 'catalog'
      AND table_name = 'artifacts'
),
coverage_rows AS (
    SELECT
        source_museum,
        jsonb_build_object(
            'rows', count(*),
            'title', count(title),
            'description', count(description),
            'period', count(period),
            'dynasty', count(dynasty),
            'ruler_id', count(ruler_id),
            'ruler_display_name', count(ruler_display_name),
            'date_start', count(date_start),
            'date_end', count(date_end),
            'date_display', count(date_display),
            'origin_site_id', count(origin_site_id),
            'origin_site_display_name', count(origin_site_display_name),
            'origin_site_raw', count(origin_site_raw),
            'origin_certainty', count(origin_certainty),
            'provenance', count(provenance),
            'excavation_id', count(excavation_id),
            'tomb_temple_id', count(tomb_temple_id)
        ) AS value
    FROM catalog.artifacts
    GROUP BY source_museum
),
coverage AS (
    SELECT jsonb_object_agg(source_museum, value ORDER BY source_museum) AS value
    FROM coverage_rows
),
checks AS (
    SELECT jsonb_build_object(
        'duplicate_artifact_ids', (
            SELECT count(*)
            FROM (
                SELECT id FROM catalog.artifacts GROUP BY id HAVING count(*) > 1
            ) duplicates
        ),
        'duplicate_artifact_source_keys', (
            SELECT count(*)
            FROM (
                SELECT source_museum, source_id
                FROM catalog.artifacts
                GROUP BY source_museum, source_id
                HAVING count(*) > 1
            ) duplicates
        ),
        'malformed_artifact_ids', (
            SELECT count(*)
            FROM catalog.artifacts
            WHERE source_id IS NULL
               OR id IS DISTINCT FROM source_museum || '-' || source_id
        ),
        'canonical_without_raw', (
            SELECT count(*)
            FROM catalog.artifacts a
            LEFT JOIN raw r
              ON r.museum = a.source_museum
             AND r.object_id = a.source_id
            WHERE r.object_id IS NULL
        ),
        'raw_without_canonical_by_museum', (SELECT value FROM raw_only_counts),
        'raw_json_non_objects', jsonb_build_object(
            'met', (
                SELECT count(*) FROM catalog.raw_met
                WHERE jsonb_typeof(data::jsonb) IS DISTINCT FROM 'object'
            ),
            'brooklyn', (
                SELECT count(*) FROM catalog.raw_brooklyn
                WHERE jsonb_typeof(data::jsonb) IS DISTINCT FROM 'object'
            ),
            'harvard', (
                SELECT count(*) FROM catalog.raw_harvard
                WHERE jsonb_typeof(data::jsonb) IS DISTINCT FROM 'object'
            )
        ),
        'raw_internal_id_mismatches', jsonb_build_object(
            'met', (
                SELECT count(*) FROM catalog.raw_met
                WHERE object_id IS DISTINCT FROM data::jsonb->>'objectID'
            ),
            'brooklyn', (
                SELECT count(*) FROM catalog.raw_brooklyn
                WHERE object_id IS DISTINCT FROM data::jsonb->>'sourceId'
            ),
            'harvard', (
                SELECT count(*) FROM catalog.raw_harvard
                WHERE object_id IS DISTINCT FROM data::jsonb->>'id'
            )
        )
    ) AS value
),
logical_fingerprints AS (
    SELECT jsonb_build_object(
        'algorithm', 'md5 of concatenated ordered per-row md5 values',
        'artifacts', (
            SELECT md5(string_agg(md5(row_to_json(a)::text), '' ORDER BY id COLLATE "C"))
            FROM catalog.artifacts a
        ),
        'raw_met', (
            SELECT md5(string_agg(
                md5(length(object_id)::text || ':' || object_id || ':' || length(data)::text || ':' || data),
                '' ORDER BY object_id COLLATE "C"
            ))
            FROM catalog.raw_met
        ),
        'raw_brooklyn', (
            SELECT md5(string_agg(
                md5(length(object_id)::text || ':' || object_id || ':' || length(data)::text || ':' || data),
                '' ORDER BY object_id COLLATE "C"
            ))
            FROM catalog.raw_brooklyn
        ),
        'raw_harvard', (
            SELECT md5(string_agg(
                md5(length(object_id)::text || ':' || object_id || ':' || length(data)::text || ':' || data),
                '' ORDER BY object_id COLLATE "C"
            ))
            FROM catalog.raw_harvard
        )
    ) AS value
)
SELECT jsonb_pretty(jsonb_build_object(
    'canonical_total', (SELECT count(*) FROM catalog.artifacts),
    'canonical_by_museum', (SELECT value FROM artifact_counts),
    'raw_total', (SELECT count(*) FROM raw),
    'raw_by_museum', (SELECT value FROM raw_counts),
    'artifact_column_count', jsonb_array_length((SELECT value FROM artifact_columns)),
    'artifact_columns', (SELECT value FROM artifact_columns),
    'checks', (SELECT value FROM checks),
    'nonnull_field_coverage', (SELECT value FROM coverage),
    'logical_fingerprints', (SELECT value FROM logical_fingerprints)
));
