import { sqliteTable, text, integer, primaryKey, uniqueIndex, index, check } from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';

export const promptRecords = sqliteTable('prompt_records', {
  ownerId: text('owner_id').notNull(), id: text('id').notNull(), requestKey: text('request_key').notNull(),
  original: text('original').notNull(), improved: text('improved').notNull(), mode: text('mode').notNull(),
  version: text('version').notNull(), createdAt: text('created_at').notNull(), archived: integer('archived').notNull().default(0),
}, table => [primaryKey({ columns: [table.ownerId, table.id] }), uniqueIndex('prompt_records_owner_request').on(table.ownerId, table.requestKey), index('prompt_records_owner_history').on(table.ownerId, table.archived, table.createdAt, table.id), check('prompt_records_archived_check', sql`${table.archived} IN (0, 1)`)]);
