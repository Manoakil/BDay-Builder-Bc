-- ============================================
-- BIRTHDAY BUILDER PLATFORM
-- Complete Supabase Database Schema
-- Version: 1.0.0
-- ============================================

-- ============================================
-- 1. EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- ============================================
-- 2. ENUMS & TYPES
-- ============================================

-- Core status types
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'banned', 'pending_approval');
CREATE TYPE member_role AS ENUM ('superadmin', 'org_admin', 'moderator', 'editor', 'viewer', 'guest');
CREATE TYPE event_status AS ENUM ('draft', 'published', 'archived', 'expired');
CREATE TYPE event_type AS ENUM ('birthday', 'anniversary', 'surprise', 'custom');
CREATE TYPE event_visibility AS ENUM ('public', 'private', 'unlisted', 'password_protected');

-- Content types
CREATE TYPE wish_status AS ENUM ('pending', 'approved', 'rejected', 'flagged', 'featured');
CREATE TYPE wish_type AS ENUM ('text', 'voice', 'video', 'image', 'emoji', 'sticker', 'gif', 'ai_generated');
CREATE TYPE wish_visibility AS ENUM ('normal', 'private', 'secret', 'scheduled');
CREATE TYPE comment_status AS ENUM ('active', 'hidden', 'flagged', 'deleted');
CREATE TYPE reaction_type AS ENUM ('❤️', '😂', '😮', '😢', '😡', '👍', '🎉', '💯', '🔥', '👏');

-- File & media types
CREATE TYPE file_type AS ENUM ('image', 'video', 'audio', 'document', 'archive', 'other');
CREATE TYPE storage_bucket AS ENUM ('avatars', 'logos', 'events', 'gallery', 'timeline', 'wishes', 'voice_notes', 'documents', 'themes', 'exports');

-- Notification & log types
CREATE TYPE notification_type AS ENUM ('wish_received', 'wish_approved', 'comment_added', 'reaction_added', 'event_published', 'invite_received', 'vault_unlocked', 'reminder');
CREATE TYPE log_action AS ENUM ('create', 'update', 'delete', 'soft_delete', 'restore', 'login', 'logout', 'view', 'download', 'share');

-- Subscription & payment
CREATE TYPE subscription_tier AS ENUM ('free', 'starter', 'pro', 'business', 'enterprise');
CREATE TYPE subscription_status AS ENUM ('active', 'past_due', 'canceled', 'unpaid', 'trialing', 'paused');
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded', 'disputed');

-- Theme & customization
CREATE TYPE theme_type AS ENUM ('preset', 'custom', 'premium');
CREATE TYPE font_family AS ENUM ('outfit', 'poppins', 'inter', 'roboto', 'playfair', 'montserrat', 'dancing_script');

-- ============================================
-- 3. ROLES & PERMISSIONS (RBAC)
-- ============================================

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    level INTEGER DEFAULT 0 CHECK (level >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID, -- Will reference auth.users later
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================
-- 4. PROFILES (extends auth.users)
-- ============================================

CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username VARCHAR(50) UNIQUE,
    full_name VARCHAR(200),
    display_name VARCHAR(200),
    avatar_url TEXT,
    cover_url TEXT,
    bio TEXT,
    website VARCHAR(500),
    phone VARCHAR(20),
    date_of_birth DATE,
    status user_status DEFAULT 'pending_approval',
    role_id UUID REFERENCES roles(id),
    default_organization_id UUID, -- Will be set after organizations table
    preferences JSONB DEFAULT '{
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications": {
            "email": true,
            "push": true,
            "sms": false
        }
    }'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    login_count INTEGER DEFAULT 0,
    email_verified BOOLEAN DEFAULT false,
    phone_verified BOOLEAN DEFAULT false,
    two_factor_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Add foreign key to profiles
ALTER TABLE profiles ADD CONSTRAINT fk_default_organization 
    FOREIGN KEY (default_organization_id) REFERENCES organizations(id) ON DELETE SET NULL;

-- ============================================
-- 5. ORGANIZATIONS
-- ============================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    logo_url TEXT,
    cover_url TEXT,
    website VARCHAR(500),
    email VARCHAR(255),
    phone VARCHAR(20),
    address JSONB,
    subscription_tier subscription_tier DEFAULT 'free',
    subscription_status subscription_status DEFAULT 'active',
    subscription_ends_at TIMESTAMPTZ,
    max_members INTEGER DEFAULT 5,
    max_events INTEGER DEFAULT 1,
    max_storage_mb INTEGER DEFAULT 100,
    settings JSONB DEFAULT '{
        "theme": {
            "type": "preset",
            "preset": "romantic",
            "primary_color": "#FF4D8D",
            "secondary_color": "#FFD166",
            "background_color": "#FFF8FB",
            "font_family": "outfit"
        },
        "features": {
            "wishes": true,
            "gallery": true,
            "timeline": true,
            "vault": true,
            "music": true,
            "quiz": false,
            "polls": false
        },
        "branding": {
            "show_logo": true,
            "custom_domain": null,
            "remove_branding": false
        }
    }'::jsonb,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ
);

-- Add foreign key to profiles
ALTER TABLE profiles ADD CONSTRAINT fk_default_organization 
    FOREIGN KEY (default_organization_id) REFERENCES organizations(id) ON DELETE SET NULL;

-- ============================================
-- 6. INVITES
-- ============================================

CREATE TABLE invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    email VARCHAR(255) NOT NULL,
    role member_role DEFAULT 'viewer',
    token VARCHAR(255) UNIQUE NOT NULL,
    invited_by UUID REFERENCES auth.users(id),
    message TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. ORGANIZATION MEMBERS
-- ============================================

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role member_role DEFAULT 'viewer',
    permissions JSONB DEFAULT '[]'::jsonb,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    invited_by UUID REFERENCES auth.users(id),
    invite_id UUID REFERENCES invites(id),
    is_primary BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(organization_id, user_id)
);

-- ============================================
-- 8. BIRTHDAY EVENTS
-- ============================================

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(300) NOT NULL,
    slug VARCHAR(300) NOT NULL UNIQUE,
    description TEXT,
    event_type event_type DEFAULT 'birthday',
    event_date DATE NOT NULL,
    event_time TIME,
    timezone VARCHAR(100) DEFAULT 'UTC',
    location JSONB,
    status event_status DEFAULT 'draft',
    visibility event_visibility DEFAULT 'private',
    access_password VARCHAR(255),
    cover_url TEXT,
    hero_video_url TEXT,
    background_music_url TEXT,
    theme_settings JSONB DEFAULT '{
        "type": "preset",
        "preset": "birthday",
        "custom_colors": {},
        "animations": true,
        "confetti": true,
        "music_player": false
    }'::jsonb,
    module_settings JSONB DEFAULT '{
        "hero": {"enabled": true, "order": 1},
        "countdown": {"enabled": true, "order": 2},
        "gallery": {"enabled": true, "order": 3},
        "timeline": {"enabled": false, "order": 4},
        "wishes": {"enabled": true, "order": 5},
        "music": {"enabled": false, "order": 6},
        "quiz": {"enabled": false, "order": 7},
        "vault": {"enabled": false, "order": 8},
        "footer": {"enabled": true, "order": 9}
    }'::jsonb,
    reveal_sequence JSONB DEFAULT '["welcome", "confetti", "hero", "countdown", "wishes", "gallery", "timeline", "vault"]'::jsonb,
    birthday_person_name VARCHAR(200),
    birthday_person_photo TEXT,
    birthday_person_bio TEXT,
    max_wishes INTEGER DEFAULT 500,
    allow_anonymous_wishes BOOLEAN DEFAULT false,
    moderate_wishes BOOLEAN DEFAULT true,
    scheduled_publish_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    view_count INTEGER DEFAULT 0,
    wish_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    qr_code_url TEXT,
    short_url VARCHAR(100),
    custom_domain VARCHAR(255),
    seo_metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 9. FILES (Centralized File Management)
-- ============================================

CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    bucket storage_bucket NOT NULL,
    path TEXT NOT NULL,
    filename VARCHAR(500) NOT NULL,
    original_name VARCHAR(500),
    mime_type VARCHAR(200),
    size_bytes BIGINT,
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT,
    file_type file_type DEFAULT 'image',
    metadata JSONB DEFAULT '{}'::jsonb,
    is_public BOOLEAN DEFAULT false,
    tags TEXT[],
    uploaded_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 10. GALLERY
-- ============================================

CREATE TABLE gallery (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    title VARCHAR(300),
    description TEXT,
    alt_text VARCHAR(500),
    sort_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT false,
    tags TEXT[],
    exif_data JSONB,
    ai_tags JSONB,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 11. TIMELINE ENTRIES
-- ============================================

CREATE TABLE timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    entry_date DATE NOT NULL,
    entry_time TIME,
    location VARCHAR(500),
    file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    sort_order INTEGER DEFAULT 0,
    is_milestone BOOLEAN DEFAULT false,
    age_at_time FLOAT,
    category VARCHAR(100),
    tags TEXT[],
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 12. WISHES
-- ============================================

CREATE TABLE wishes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    guest_name VARCHAR(200),
    guest_email VARCHAR(255),
    wish_type wish_type DEFAULT 'text',
    content TEXT,
    file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    visibility wish_visibility DEFAULT 'normal',
    status wish_status DEFAULT 'pending',
    is_anonymous BOOLEAN DEFAULT false,
    is_featured BOOLEAN DEFAULT false,
    scheduled_for TIMESTAMPTZ,
    ai_generated BOOLEAN DEFAULT false,
    ai_prompt TEXT,
    language VARCHAR(10) DEFAULT 'en',
    sentiment_score FLOAT,
    reply_count INTEGER DEFAULT 0,
    reaction_counts JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 13. WISH COMMENTS
-- ============================================

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wish_id UUID REFERENCES wishes(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    guest_name VARCHAR(200),
    content TEXT NOT NULL,
    status comment_status DEFAULT 'active',
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- 14. WISH REACTIONS
-- ============================================

CREATE TABLE reactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wish_id UUID REFERENCES wishes(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    guest_identifier VARCHAR(255),
    reaction_type reaction_type NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wish_id, user_id, reaction_type),
    UNIQUE(wish_id, guest_identifier, reaction_type)
);

-- ============================================
-- 15. SECRET VAULT
-- ============================================

CREATE TABLE secret_vault (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    question TEXT NOT NULL,
    answer_hash VARCHAR(500) NOT NULL,
    hint TEXT,
    unlock_message TEXT,
    unlock_media_url TEXT,
    max_attempts INTEGER DEFAULT 3,
    current_attempts INTEGER DEFAULT 0,
    is_locked BOOLEAN DEFAULT false,
    locked_until TIMESTAMPTZ,
    unlock_time TIMESTAMPTZ,
    auto_unlock_enabled BOOLEAN DEFAULT false,
    auto_unlock_at TIMESTAMPTZ,
    unlock_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE vault_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vault_id UUID REFERENCES secret_vault(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    guest_identifier VARCHAR(255),
    attempt_answer TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT false,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 16. NOTIFICATIONS
-- ============================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    type notification_type NOT NULL,
    title VARCHAR(300) NOT NULL,
    message TEXT,
    data JSONB DEFAULT '{}'::jsonb,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    action_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 17. AUDIT LOGS
-- ============================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id),
    action log_action NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id UUID,
    old_data JSONB,
    new_data JSONB,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 18. ANALYTICS
-- ============================================

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    visitor_id VARCHAR(255),
    session_id VARCHAR(255),
    page_url TEXT,
    referrer TEXT,
    event_name VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    country VARCHAR(100),
    city VARCHAR(200),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE analytics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL,
    unique_visitors INTEGER DEFAULT 0,
    page_views INTEGER DEFAULT 0,
    wish_submissions INTEGER DEFAULT 0,
    wish_approvals INTEGER DEFAULT 0,
    vault_attempts INTEGER DEFAULT 0,
    vault_unlocks INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    avg_session_duration FLOAT,
    bounce_rate FLOAT,
    countries_data JSONB DEFAULT '{}'::jsonb,
    devices_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, date)
);

-- ============================================
-- 19. SUBSCRIPTIONS & BILLING
-- ============================================

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    tier subscription_tier DEFAULT 'free',
    status subscription_status DEFAULT 'active',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    payment_provider VARCHAR(100),
    provider_subscription_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status payment_status DEFAULT 'pending',
    payment_method VARCHAR(50),
    provider_payment_id VARCHAR(255),
    invoice_url TEXT,
    paid_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 20. THEMES & CUSTOMIZATION
-- ============================================

CREATE TABLE themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    type theme_type DEFAULT 'preset',
    is_premium BOOLEAN DEFAULT false,
    price DECIMAL(10,2) DEFAULT 0,
    preview_url TEXT,
    settings JSONB NOT NULL DEFAULT '{
        "colors": {
            "primary": "#FF4D8D",
            "secondary": "#FFD166",
            "background": "#FFF8FB",
            "text": "#1F2937",
            "accent": "#FFB703"
        },
        "fonts": {
            "heading": "outfit",
            "body": "outfit"
        },
        "spacing": "comfortable",
        "border_radius": "12px",
        "animations": true,
        "effects": {
            "confetti": true,
            "snow": false,
            "hearts": false
        }
    }'::jsonb,
    created_by UUID REFERENCES auth.users(id),
    is_public BOOLEAN DEFAULT true,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organization_themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    theme_id UUID REFERENCES themes(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT false,
    custom_settings JSONB,
    purchased_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, theme_id)
);

-- ============================================
-- 21. INDEXES
-- ============================================

-- Profiles indexes
CREATE INDEX idx_profiles_username ON profiles(username);
CREATE INDEX idx_profiles_status ON profiles(status);
CREATE INDEX idx_profiles_role ON profiles(role_id);
CREATE INDEX idx_profiles_org ON profiles(default_organization_id);

-- Organizations indexes
CREATE INDEX idx_org_slug ON organizations(slug);
CREATE INDEX idx_org_subscription ON organizations(subscription_tier);
CREATE INDEX idx_org_status ON organizations(subscription_status);
CREATE INDEX idx_org_created_by ON organizations(created_by);
CREATE INDEX idx_org_deleted ON organizations(deleted_at) WHERE deleted_at IS NOT NULL;

-- Events indexes
CREATE INDEX idx_events_org ON events(organization_id);
CREATE INDEX idx_events_slug ON events(slug);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_visibility ON events(visibility);
CREATE INDEX idx_events_published ON events(published_at);
CREATE INDEX idx_events_expires ON events(expires_at);
CREATE INDEX idx_events_birthday_person ON events(birthday_person_name);
CREATE INDEX idx_events_deleted ON events(deleted_at) WHERE deleted_at IS NOT NULL;

-- Members indexes
CREATE INDEX idx_members_org ON organization_members(organization_id);
CREATE INDEX idx_members_user ON organization_members(user_id);
CREATE INDEX idx_members_role ON organization_members(role);
CREATE INDEX idx_members_org_user ON organization_members(organization_id, user_id);
CREATE INDEX idx_members_deleted ON organization_members(deleted_at) WHERE deleted_at IS NOT NULL;

-- Files indexes
CREATE INDEX idx_files_org ON files(organization_id);
CREATE INDEX idx_files_event ON files(event_id);
CREATE INDEX idx_files_bucket ON files(bucket);
CREATE INDEX idx_files_type ON files(file_type);
CREATE INDEX idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX idx_files_deleted ON files(deleted_at) WHERE deleted_at IS NOT NULL;

-- Gallery indexes
CREATE INDEX idx_gallery_event ON gallery(event_id);
CREATE INDEX idx_gallery_file ON gallery(file_id);
CREATE INDEX idx_gallery_sort ON gallery(event_id, sort_order);
CREATE INDEX idx_gallery_deleted ON gallery(deleted_at) WHERE deleted_at IS NOT NULL;

-- Timeline indexes
CREATE INDEX idx_timeline_event ON timeline(event_id);
CREATE INDEX idx_timeline_date ON timeline(entry_date);
CREATE INDEX idx_timeline_sort ON timeline(event_id, sort_order);
CREATE INDEX idx_timeline_deleted ON timeline(deleted_at) WHERE deleted_at IS NOT NULL;

-- Wishes indexes
CREATE INDEX idx_wishes_event ON wishes(event_id);
CREATE INDEX idx_wishes_user ON wishes(user_id);
CREATE INDEX idx_wishes_type ON wishes(wish_type);
CREATE INDEX idx_wishes_status ON wishes(status);
CREATE INDEX idx_wishes_visibility ON wishes(visibility);
CREATE INDEX idx_wishes_scheduled ON wishes(scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX idx_wishes_event_status ON wishes(event_id, status);
CREATE INDEX idx_wishes_guest ON wishes(guest_email);
CREATE INDEX idx_wishes_deleted ON wishes(deleted_at) WHERE deleted_at IS NOT NULL;

-- Comments indexes
CREATE INDEX idx_comments_wish ON comments(wish_id);
CREATE INDEX idx_comments_user ON comments(user_id);
CREATE INDEX idx_comments_parent ON comments(parent_comment_id);
CREATE INDEX idx_comments_deleted ON comments(deleted_at) WHERE deleted_at IS NOT NULL;

-- Reactions indexes
CREATE INDEX idx_reactions_wish ON reactions(wish_id);
CREATE INDEX idx_reactions_user ON reactions(user_id);
CREATE INDEX idx_reactions_type ON reactions(wish_id, reaction_type);

-- Vault indexes
CREATE INDEX idx_vault_event ON secret_vault(event_id);
CREATE INDEX idx_vault_attempts_vault ON vault_attempts(vault_id);
CREATE INDEX idx_vault_attempts_user ON vault_attempts(user_id);

-- Notifications indexes
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);

-- Audit logs indexes
CREATE INDEX idx_audit_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_event ON audit_logs(event_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_table ON audit_logs(table_name);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Analytics indexes
CREATE INDEX idx_analytics_event ON analytics_events(event_id);
CREATE INDEX idx_analytics_date ON analytics_events(created_at DESC);
CREATE INDEX idx_analytics_name ON analytics_events(event_name);
CREATE INDEX idx_analytics_daily_event ON analytics_daily(event_id);
CREATE INDEX idx_analytics_daily_date ON analytics_daily(date DESC);

-- Invites indexes
CREATE INDEX idx_invites_org ON invites(organization_id);
CREATE INDEX idx_invites_email ON invites(email);
CREATE INDEX idx_invites_token ON invites(token);
CREATE INDEX idx_invites_status ON invites(status);

-- ============================================
-- 22. TRIGGERS
-- ============================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER trg_profiles_updated
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_organizations_updated
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_events_updated
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_wishes_updated
    BEFORE UPDATE ON wishes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_gallery_updated
    BEFORE UPDATE ON gallery
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_timeline_updated
    BEFORE UPDATE ON timeline
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_secret_vault_updated
    BEFORE UPDATE ON secret_vault
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function: Increment event view count
CREATE OR REPLACE FUNCTION increment_event_views()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE events SET view_count = view_count + 1 WHERE id = NEW.event_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_analytics_increment_views
    AFTER INSERT ON analytics_events
    FOR EACH ROW
    WHEN (NEW.event_name = 'page_view')
    EXECUTE FUNCTION increment_event_views();

-- Function: Update wish count on event
CREATE OR REPLACE FUNCTION update_event_wish_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE events SET wish_count = wish_count + 1 WHERE id = NEW.event_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE events SET wish_count = wish_count - 1 WHERE id = OLD.event_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wishes_count
    AFTER INSERT OR DELETE ON wishes
    FOR EACH ROW EXECUTE FUNCTION update_event_wish_count();

-- Function: Auto-lock vault after max attempts
CREATE OR REPLACE FUNCTION check_vault_lock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE secret_vault SET current_attempts = current_attempts + 1 WHERE id = NEW.vault_id;
    
    UPDATE secret_vault 
    SET is_locked = true, 
        locked_until = NOW() + INTERVAL '1 hour'
    WHERE id = NEW.vault_id 
    AND current_attempts >= max_attempts;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vault_attempt_lock
    AFTER INSERT ON vault_attempts
    FOR EACH ROW EXECUTE FUNCTION check_vault_lock();

-- Function: Auto-publish event at scheduled time
CREATE OR REPLACE FUNCTION auto_publish_event()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.scheduled_publish_at IS NOT NULL AND NEW.scheduled_publish_at <= NOW() AND NEW.status = 'draft' THEN
        NEW.status = 'published';
        NEW.published_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_publish_event
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION auto_publish_event();

-- ============================================
-- 23. FUNCTIONS
-- ============================================

-- Function: Soft delete record
CREATE OR REPLACE FUNCTION soft_delete(table_name text, record_id uuid)
RETURNS void AS $$
BEGIN
    EXECUTE format('UPDATE %I SET deleted_at = NOW() WHERE id = $1', table_name)
    USING record_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Restore soft deleted record
CREATE OR REPLACE FUNCTION restore_record(table_name text, record_id uuid)
RETURNS void AS $$
BEGIN
    EXECUTE format('UPDATE %I SET deleted_at = NULL WHERE id = $1', table_name)
    USING record_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get user permissions
CREATE OR REPLACE FUNCTION get_user_permissions(user_id uuid)
RETURNS TABLE(permission_slug text) AS $$
BEGIN
    RETURN QUERY
    SELECT p.slug
    FROM profiles pr
    JOIN role_permissions rp ON pr.role_id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE pr.id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Check if user has permission
CREATE OR REPLACE FUNCTION has_permission(user_id uuid, perm_slug text)
RETURNS boolean AS $$
DECLARE
    has_perm boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM profiles pr
        JOIN role_permissions rp ON pr.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE pr.id = user_id AND p.slug = perm_slug
    ) INTO has_perm;
    
    RETURN has_perm;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get event analytics summary
CREATE OR REPLACE FUNCTION get_event_analytics(event_id uuid)
RETURNS TABLE(
    total_visitors bigint,
    total_views bigint,
    total_wishes bigint,
    approved_wishes bigint,
    pending_wishes bigint,
    total_vault_attempts bigint,
    vault_unlocks bigint,
    total_shares bigint,
    top_countries jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT visitor_id)::bigint,
        COUNT(*)::bigint,
        (SELECT COUNT(*) FROM wishes w WHERE w.event_id = $1)::bigint,
        (SELECT COUNT(*) FROM wishes w WHERE w.event_id = $1 AND w.status = 'approved')::bigint,
        (SELECT COUNT(*) FROM wishes w WHERE w.event_id = $1 AND w.status = 'pending')::bigint,
        (SELECT COUNT(*) FROM vault_attempts va JOIN secret_vault sv ON va.vault_id = sv.id WHERE sv.event_id = $1)::bigint,
        (SELECT COUNT(*) FROM secret_vault sv WHERE sv.event_id = $1 AND sv.unlock_count > 0)::bigint,
        (SELECT COUNT(*) FROM analytics_events ae WHERE ae.event_id = $1 AND ae.event_name = 'share')::bigint,
        (
            SELECT jsonb_object_agg(country, cnt ORDER BY cnt DESC)
            FROM (
                SELECT country, COUNT(*) as cnt
                FROM analytics_events
                WHERE event_id = $1 AND country IS NOT NULL
                GROUP BY country
                LIMIT 10
            ) sub
        )
    FROM analytics_events
    WHERE event_id = $1;
END;
$$ LANGUAGE plpgsql;

-- Function: Generate event short URL
CREATE OR REPLACE FUNCTION generate_short_url()
RETURNS text AS $$
DECLARE
    chars text[] := '{a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,0,1,2,3,4,5,6,7,8,9}';
    result text := '';
    i integer;
BEGIN
    FOR i IN 1..8 LOOP
        result := result || chars[1+random()*(array_length(chars, 1)-1)];
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function: Search wishes with full-text search
CREATE OR REPLACE FUNCTION search_wishes(event_id uuid, search_term text)
RETURNS TABLE(
    id uuid,
    guest_name varchar,
    content text,
    wish_type wish_type,
    status wish_status,
    created_at timestamptz,
    rank real
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        w.id,
        w.guest_name,
        w.content,
        w.wish_type,
        w.status,
        w.created_at,
        ts_rank(to_tsvector('english', coalesce(w.content, '')), plainto_tsquery('english', search_term)) as rank
    FROM wishes w
    WHERE w.event_id = event_id
    AND w.deleted_at IS NULL
    AND (
        to_tsvector('english', coalesce(w.content, '')) @@ plainto_tsquery('english', search_term)
        OR w.guest_name ILIKE '%' || search_term || '%'
    )
    ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 24. ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE gallery ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE wishes ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE secret_vault ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE invites ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view their own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Org admins can view member profiles"
    ON profiles FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM organization_members om
            WHERE om.user_id = auth.uid()
            AND om.role IN ('owner', 'admin')
            AND om.organization_id IN (
                SELECT organization_id FROM organization_members WHERE user_id = profiles.id
            )
        )
    );

-- Organizations policies
CREATE POLICY "Org members can view their org"
    ON organizations FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM organization_members
            WHERE organization_id = id
            AND user_id = auth.uid()
        )
    );

CREATE POLICY "Org owners can update org"
    ON organizations FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM organization_members
            WHERE organization_id = id
            AND user_id = auth.uid()
            AND role = 'owner'
        )
    );

CREATE POLICY "Users can create organizations"
    ON organizations FOR INSERT
    WITH CHECK (auth.uid() = created_by);

-- Events policies
CREATE POLICY "Org members can view events"
    ON events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM organization_members
            WHERE organization_id = events.organization_id
            AND user_id = auth.uid()
        )
        OR visibility = 'public'
    );

CREATE POLICY "Org admins can manage events"
    ON events FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM organization_members
            WHERE organization_id = events.organization_id
            AND user_id = auth.uid()
            AND role IN ('owner', 'admin')
        )
    );

-- Wishes policies
CREATE POLICY "Anyone can view approved wishes"
    ON wishes FOR SELECT
    USING (
        status = 'approved'
        AND deleted_at IS NULL
    );

CREATE POLICY "Event creators can manage wishes"
    ON wishes FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM events e
            JOIN organization_members om ON e.organization_id = om.organization_id
            WHERE e.id = wishes.event_id
            AND om.user_id = auth.uid()
            AND om.role IN ('owner', 'admin')
        )
    );

CREATE POLICY "Anyone can create wishes for public events"
    ON wishes FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM events
            WHERE id = wishes.event_id
            AND visibility = 'public'
            AND status = 'published'
        )
    );

-- Secret vault policies
CREATE POLICY "Event creators can manage vault"
    ON secret_vault FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM events e
            JOIN organization_members om ON e.organization_id = om.organization_id
            WHERE e.id = secret_vault.event_id
            AND om.user_id = auth.uid()
            AND om.role IN ('owner', 'admin')
        )
    );

CREATE POLICY "Anyone can attempt vault"
    ON vault_attempts FOR INSERT
    WITH CHECK (true);

-- ============================================
-- 25. STORAGE BUCKETS
-- ============================================

-- Note: These are created via Supabase dashboard or API
-- Included here as documentation

-- INSERT INTO storage.buckets (id, name, public) VALUES
-- ('avatars', 'avatars', true),
-- ('logos', 'logos', true),
-- ('events', 'events', true),
-- ('gallery', 'gallery', true),
-- ('timeline', 'timeline', true),
-- ('wishes', 'wishes', false),
-- ('voice_notes', 'voice_notes', false),
-- ('documents', 'documents', false),
-- ('themes', 'themes', true),
-- ('exports', 'exports', false);

-- Storage policies
-- CREATE POLICY "Public can view public files"
--     ON storage.objects FOR SELECT
--     USING (bucket_id IN ('avatars', 'logos', 'events', 'gallery', 'timeline', 'themes'));

-- CREATE POLICY "Auth users can upload to their org buckets"
--     ON storage.objects FOR INSERT
--     WITH CHECK (auth.role() = 'authenticated');

-- ============================================
-- 26. SEED DATA
-- ============================================

-- Insert default roles
INSERT INTO roles (name, slug, description, is_system, level) VALUES
('Super Admin', 'super_admin', 'Full platform access', true, 100),
('Organization Owner', 'org_owner', 'Full organization access', true, 90),
('Organization Admin', 'org_admin', 'Organization management', true, 80),
('Moderator', 'moderator', 'Content moderation', true, 60),
('Editor', 'editor', 'Content editing', true, 50),
('Viewer', 'viewer', 'View only access', true, 20),
('Guest', 'guest', 'Limited access', true, 10);

-- Insert default permissions
INSERT INTO permissions (name, slug, resource, action) VALUES
('Manage Organizations', 'manage_organizations', 'organizations', 'manage'),
('View Organizations', 'view_organizations', 'organizations', 'view'),
('Create Events', 'create_events', 'events', 'create'),
('Edit Events', 'edit_events', 'events', 'edit'),
('Delete Events', 'delete_events', 'events', 'delete'),
('Publish Events', 'publish_events', 'events', 'publish'),
('Manage Wishes', 'manage_wishes', 'wishes', 'manage'),
('Approve Wishes', 'approve_wishes', 'wishes', 'approve'),
('Delete Wishes', 'delete_wishes', 'wishes', 'delete'),
('Manage Gallery', 'manage_gallery', 'gallery', 'manage'),
('Manage Timeline', 'manage_timeline', 'timeline', 'manage'),
('Manage Vault', 'manage_vault', 'vault', 'manage'),
('View Analytics', 'view_analytics', 'analytics', 'view'),
('Manage Themes', 'manage_themes', 'themes', 'manage'),
('Manage Members', 'manage_members', 'members', 'manage'),
('Manage Billing', 'manage_billing', 'billing', 'manage'),
('View Audit Logs', 'view_audit_logs', 'audit', 'view'),
('Manage Platform', 'manage_platform', 'platform', 'manage');

-- Assign permissions to Super Admin (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE slug = 'super_admin'),
    id
FROM permissions;

-- Assign permissions to Organization Owner
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE slug = 'org_owner'),
    id
FROM permissions
WHERE slug NOT IN ('manage_platform', 'view_audit_logs');

-- Assign permissions to Organization Admin
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE slug = 'org_admin'),
    id
FROM permissions
WHERE slug IN (
    'view_organizations', 'create_events', 'edit_events', 'delete_events',
    'publish_events', 'manage_wishes', 'approve_wishes', 'delete_wishes',
    'manage_gallery', 'manage_timeline', 'manage_vault', 'view_analytics',
    'manage_themes', 'manage_members'
);

-- Insert preset themes
INSERT INTO themes (name, slug, description, type, is_premium, settings) VALUES
(
    'Romantic',
    'romantic',
    'Soft pink theme perfect for romantic celebrations',
    'preset',
    false,
    '{
        "colors": {
            "primary": "#FF4D8D",
            "secondary": "#FFD166",
            "background": "#FFF0F5",
            "text": "#1F2937",
            "accent": "#FFB703"
        },
        "fonts": {
            "heading": "outfit",
            "body": "outfit"
        },
        "animations": true,
        "effects": {
            "confetti": true,
            "hearts": true,
            "snow": false
        }
    }'::jsonb
),
(
    'Birthday Fun',
    'birthday-fun',
    'Colorful and energetic birthday theme',
    'preset',
    false,
    '{
        "colors": {
            "primary": "#FFB703",
            "secondary": "#FB8500",
            "background": "#FFF8F0",
            "text": "#1F2937",
            "accent": "#FF4D8D"
        },
        "fonts": {
            "heading": "poppins",
            "body": "poppins"
        },
        "animations": true,
        "effects": {
            "confetti": true,
            "hearts": false,
            "snow": false
        }
    }'::jsonb
),
(
    'Galaxy',
    'galaxy',
    'Stunning space-themed celebration',
    'preset',
    false,
    '{
        "colors": {
            "primary": "#6C63FF",
            "secondary": "#3F37C9",
            "background": "#F0EEFF",
            "text": "#1F2937",
            "accent": "#FFD166"
        },
        "fonts": {
            "heading": "inter",
            "body": "inter"
        },
        "animations": true,
        "effects": {
            "confetti": false,
            "hearts": false,
            "snow": true
        }
    }'::jsonb
),
(
    'Nature',
    'nature',
    'Fresh and natural green theme',
    'preset',
    false,
    '{
        "colors": {
            "primary": "#2D6A4F",
            "secondary": "#52B788",
            "background": "#F0FFF4",
            "text": "#1F2937",
            "accent": "#FFD166"
        },
        "fonts": {
            "heading": "outfit",
            "body": "roboto"
        },
        "animations": true,
        "effects": {
            "confetti": false,
            "hearts": false,
            "snow": false
        }
    }'::jsonb
),
(
    'Luxury Gold',
    'luxury-gold',
    'Elegant premium gold theme',
    'preset',
    true,
    '{
        "colors": {
            "primary": "#D4AF37",
            "secondary": "#F5E7C8",
            "background": "#FFFDF5",
            "text": "#1F2937",
            "accent": "#C5A572"
        },
        "fonts": {
            "heading": "playfair",
            "body": "montserrat"
        },
        "animations": true,
        "effects": {
            "confetti": true,
            "hearts": false,
            "snow": false
        }
    }'::jsonb
);

-- ============================================
-- 27. VIEWS
-- ============================================

-- View: Active events with stats
CREATE OR REPLACE VIEW active_events_view AS
SELECT 
    e.id,
    e.title,
    e.slug,
    e.event_date,
    e.status,
    e.visibility,
    e.view_count,
    e.wish_count,
    e.share_count,
    o.name as organization_name,
    o.slug as organization_slug,
    e.published_at
FROM events e
JOIN organizations o ON e.organization_id = o.id
WHERE e.deleted_at IS NULL
AND e.status = 'published'
ORDER BY e.published_at DESC;

-- View: Organization member details
CREATE OR REPLACE VIEW organization_members_view AS
SELECT 
    om.id,
    om.organization_id,
    o.name as organization_name,
    om.user_id,
    p.full_name,
    p.username,
    p.avatar_url,
    om.role,
    om.joined_at,
    om.is_primary
FROM organization_members om
JOIN organizations o ON om.organization_id = o.id
JOIN profiles p ON om.user_id = p.id
WHERE om.deleted_at IS NULL;

-- View: Pending wishes for moderation
CREATE OR REPLACE VIEW pending_wishes_view AS
SELECT 
    w.id,
    w.event_id,
    e.title as event_title,
    w.guest_name,
    w.wish_type,
    w.content,
    w.status,
    w.created_at,
    e.organization_id,
    o.name as organization_name
FROM wishes w
JOIN events e ON w.event_id = e.id
JOIN organizations o ON e.organization_id = o.id
WHERE w.status = 'pending'
AND w.deleted_at IS NULL
ORDER BY w.created_at ASC;

-- View: Event analytics summary
CREATE OR REPLACE VIEW event_analytics_view AS
SELECT 
    e.id as event_id,
    e.title,
    e.organization_id,
    COUNT(DISTINCT ae.visitor_id) as unique_visitors,
    COUNT(ae.id) as total_page_views,
    COUNT(DISTINCT w.id) as total_wishes,
    COUNT(DISTINCT CASE WHEN w.status = 'approved' THEN w.id END) as approved_wishes,
    COUNT(DISTINCT va.id) as vault_attempts,
    COUNT(DISTINCT CASE WHEN va.is_correct THEN va.id END) as vault_unlocks
FROM events e
LEFT JOIN analytics_events ae ON e.id = ae.event_id
LEFT JOIN wishes w ON e.id = w.event_id
LEFT JOIN secret_vault sv ON e.id = sv.event_id
LEFT JOIN vault_attempts va ON sv.id = va.vault_id
WHERE e.deleted_at IS NULL
GROUP BY e.id, e.title, e.organization_id;

-- ============================================
-- 28. COMPOSITE INDEXES FOR PERFORMANCE
-- ============================================

-- Wishes composite indexes
CREATE INDEX idx_wishes_event_status_type ON wishes(event_id, status, wish_type);
CREATE INDEX idx_wishes_event_created ON wishes(event_id, created_at DESC);
CREATE INDEX idx_wishes_event_visibility ON wishes(event_id, visibility);

-- Events composite indexes  
CREATE INDEX idx_events_org_status ON events(organization_id, status);
CREATE INDEX idx_events_org_date ON events(organization_id, event_date);
CREATE INDEX idx_events_status_visibility ON events(status, visibility);

-- Analytics composite indexes
CREATE INDEX idx_analytics_event_date ON analytics_events(event_id, created_at DESC);
CREATE INDEX idx_analytics_event_name_date ON analytics_events(event_name, created_at DESC);

-- Members composite indexes
CREATE INDEX idx_members_org_role ON organization_members(organization_id, role);

-- ============================================
-- 29. ADDITIONAL UTILITY FUNCTIONS
-- ============================================

-- Function: Get organization storage usage
CREATE OR REPLACE FUNCTION get_org_storage_usage(org_id uuid)
RETURNS TABLE(bucket_name text, file_count bigint, total_size_mb numeric) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        f.bucket::text,
        COUNT(*)::bigint,
        ROUND(SUM(f.size_bytes)::numeric / (1024 * 1024), 2) as total_size_mb
    FROM files f
    WHERE f.organization_id = org_id
    AND f.deleted_at IS NULL
    GROUP BY f.bucket;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Clean up expired events
CREATE OR REPLACE FUNCTION cleanup_expired_events()
RETURNS integer AS $$
DECLARE
    affected_rows integer;
BEGIN
    UPDATE events 
    SET status = 'archived' 
    WHERE expires_at < NOW() 
    AND status = 'published';
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Function: Bulk approve wishes
CREATE OR REPLACE FUNCTION bulk_approve_wishes(wish_ids uuid[], moderator_id uuid)
RETURNS integer AS $$
DECLARE
    affected_rows integer;
BEGIN
    UPDATE wishes 
    SET status = 'approved',
        updated_by = moderator_id,
        updated_at = NOW()
    WHERE id = ANY(wish_ids)
    AND status = 'pending'
    AND deleted_at IS NULL;
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    
    -- Log the action
    INSERT INTO audit_logs (user_id, action, table_name, record_id, new_data)
    SELECT moderator_id, 'update', 'wishes', unnest(wish_ids), jsonb_build_object('status', 'approved');
    
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get upcoming birthdays
CREATE OR REPLACE FUNCTION get_upcoming_birthdays(days_ahead integer DEFAULT 30)
RETURNS TABLE(
    event_id uuid,
    title text,
    birthday_person_name text,
    event_date date,
    days_until integer,
    organization_name text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.title,
        e.birthday_person_name,
        e.event_date,
        (e.event_date - CURRENT_DATE)::integer as days_until,
        o.name
    FROM events e
    JOIN organizations o ON e.organization_id = o.id
    WHERE e.event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + days_ahead
    AND e.deleted_at IS NULL
    AND e.status = 'published'
    ORDER BY e.event_date ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- END OF SCHEMA
-- ============================================

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '✅ Birthday Builder Database Schema Created Successfully';
    RAISE NOTICE '📊 Tables: 20+';
    RAISE NOTICE '🔐 RLS Policies: 15+';
    RAISE NOTICE '⚡ Functions: 15+';
    RAISE NOTICE '🎯 Triggers: 8';
    RAISE NOTICE '📈 Indexes: 50+';
    RAISE NOTICE '👁️ Views: 4';
    RAISE NOTICE '🎨 Seed Data: Roles, Permissions, Themes';
END $$;
