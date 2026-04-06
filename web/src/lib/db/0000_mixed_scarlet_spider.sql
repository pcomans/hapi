-- Current sql file was generated after introspecting the database
-- If you want to run this migration please uncomment this code before executing migrations
/*
CREATE SCHEMA "catalog";
--> statement-breakpoint
CREATE TABLE "catalog"."alembic_version" (
	"version_num" varchar(32) PRIMARY KEY NOT NULL
);
--> statement-breakpoint
CREATE TABLE "catalog"."artifacts" (
	"id" varchar PRIMARY KEY NOT NULL,
	"source_museum" varchar NOT NULL,
	"source_url" text NOT NULL,
	"source_id" varchar,
	"title" text,
	"description" text,
	"object_type" varchar,
	"materials" varchar[],
	"dimensions" text,
	"period" varchar,
	"dynasty" varchar,
	"ruler_id" varchar,
	"ruler_display_name" varchar,
	"date_start" integer,
	"date_end" integer,
	"date_display" varchar,
	"origin_site_id" varchar,
	"origin_site_display_name" varchar,
	"origin_site_raw" text,
	"origin_certainty" varchar,
	"excavation_id" varchar,
	"tomb_temple_id" varchar,
	"current_location" varchar,
	"accession_number" varchar,
	"credit_line" text,
	"image_url" text,
	"thumbnail_url" text,
	"license" varchar NOT NULL,
	"wikidata_id" varchar
);
--> statement-breakpoint
CREATE TABLE "catalog"."fuzzy_match_reviews" (
	"id" serial PRIMARY KEY NOT NULL,
	"artifact_id" varchar NOT NULL,
	"field" varchar NOT NULL,
	"raw_value" text NOT NULL,
	"matched_id" varchar,
	"status" varchar NOT NULL,
	"reviewed_by" varchar,
	"review_notes" text
);
--> statement-breakpoint
CREATE TABLE "catalog"."raw_brooklyn" (
	"object_id" varchar PRIMARY KEY NOT NULL,
	"data" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "catalog"."raw_harvard" (
	"object_id" varchar PRIMARY KEY NOT NULL,
	"data" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "catalog"."raw_met" (
	"object_id" varchar PRIMARY KEY NOT NULL,
	"data" text NOT NULL
);
--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_dynasty" ON "catalog"."artifacts" USING btree ("dynasty" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_excavation_id" ON "catalog"."artifacts" USING btree ("excavation_id" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_object_type" ON "catalog"."artifacts" USING btree ("object_type" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_origin_site_id" ON "catalog"."artifacts" USING btree ("origin_site_id" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_period" ON "catalog"."artifacts" USING btree ("period" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_ruler_id" ON "catalog"."artifacts" USING btree ("ruler_id" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_source_museum" ON "catalog"."artifacts" USING btree ("source_museum" text_ops);--> statement-breakpoint
CREATE INDEX "ix_catalog_artifacts_tomb_temple_id" ON "catalog"."artifacts" USING btree ("tomb_temple_id" text_ops);
*/