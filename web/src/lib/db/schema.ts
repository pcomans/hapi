import { pgTable, pgSchema, varchar, index, text, integer, serial } from "drizzle-orm/pg-core"
import { sql } from "drizzle-orm"

export const catalog = pgSchema("catalog");


export const alembicVersionInCatalog = catalog.table("alembic_version", {
	versionNum: varchar("version_num", { length: 32 }).primaryKey().notNull(),
});

export const artifactsInCatalog = catalog.table("artifacts", {
	id: varchar().primaryKey().notNull(),
	sourceMuseum: varchar("source_museum").notNull(),
	sourceUrl: text("source_url").notNull(),
	sourceId: varchar("source_id"),
	title: text(),
	description: text(),
	objectType: varchar("object_type"),
	materials: varchar().array(),
	dimensions: text(),
	period: varchar(),
	dynasty: varchar(),
	rulerId: varchar("ruler_id"),
	rulerDisplayName: varchar("ruler_display_name"),
	dateStart: integer("date_start"),
	dateEnd: integer("date_end"),
	dateDisplay: varchar("date_display"),
	originSiteId: varchar("origin_site_id"),
	originSiteDisplayName: varchar("origin_site_display_name"),
	originSiteRaw: text("origin_site_raw"),
	originCertainty: varchar("origin_certainty"),
	excavationId: varchar("excavation_id"),
	tombTempleId: varchar("tomb_temple_id"),
	currentLocation: varchar("current_location"),
	accessionNumber: varchar("accession_number"),
	creditLine: text("credit_line"),
	imageUrl: text("image_url"),
	thumbnailUrl: text("thumbnail_url"),
	license: varchar().notNull(),
	wikidataId: varchar("wikidata_id"),
}, (table) => [
	index("ix_catalog_artifacts_dynasty").using("btree", table.dynasty.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_excavation_id").using("btree", table.excavationId.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_object_type").using("btree", table.objectType.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_origin_site_id").using("btree", table.originSiteId.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_period").using("btree", table.period.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_ruler_id").using("btree", table.rulerId.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_source_museum").using("btree", table.sourceMuseum.asc().nullsLast().op("text_ops")),
	index("ix_catalog_artifacts_tomb_temple_id").using("btree", table.tombTempleId.asc().nullsLast().op("text_ops")),
]);

export const fuzzyMatchReviewsInCatalog = catalog.table("fuzzy_match_reviews", {
	id: serial().primaryKey().notNull(),
	artifactId: varchar("artifact_id").notNull(),
	field: varchar().notNull(),
	rawValue: text("raw_value").notNull(),
	matchedId: varchar("matched_id"),
	status: varchar().notNull(),
	reviewedBy: varchar("reviewed_by"),
	reviewNotes: text("review_notes"),
});

export const rawBrooklynInCatalog = catalog.table("raw_brooklyn", {
	objectId: varchar("object_id").primaryKey().notNull(),
	data: text().notNull(),
});

export const rawHarvardInCatalog = catalog.table("raw_harvard", {
	objectId: varchar("object_id").primaryKey().notNull(),
	data: text().notNull(),
});

export const rawMetInCatalog = catalog.table("raw_met", {
	objectId: varchar("object_id").primaryKey().notNull(),
	data: text().notNull(),
});
