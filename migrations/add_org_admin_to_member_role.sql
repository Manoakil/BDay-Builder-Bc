-- ============================================
-- MIGRATION: Add 'org_admin' to member_role ENUM
-- ============================================
-- Purpose: The application's organization creation flow
-- (organization_service.create_organization_from_db) inserts a member row
-- with role = 'org_admin'. The member_role ENUM did not include this value,
-- causing a PostgreSQL error that rolled back the organization insert and
-- made org creation fail with "Organization creation failed".
--
-- This migration adds the missing enum value so the application code does
-- not need to change.
-- ============================================

ALTER TYPE member_role ADD VALUE IF NOT EXISTS 'org_admin';
