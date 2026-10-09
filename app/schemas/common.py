from enum import Enum

class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    banned = "banned"
    pending_approval = "pending_approval"

class MemberRole(str, Enum):
    super_admin = "super_admin"
    org_admin = "org_admin"
    wisher = "wisher"
    bday_person = "bday_person"
    viewer = "viewer"

class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"
    expired = "expired"

class EventType(str, Enum):
    birthday = "birthday"
    anniversary = "anniversary"
    surprise = "surprise"
    custom = "custom"

class EventVisibility(str, Enum):
    public = "public"
    private = "private"
    unlisted = "unlisted"
    password_protected = "password_protected"

class WishStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    flagged = "flagged"
    featured = "featured"

class WishType(str, Enum):
    text = "text"
    voice = "voice"
    video = "video"
    image = "image"
    emoji = "emoji"
    sticker = "sticker"
    gif = "gif"
    ai_generated = "ai_generated"

class WishVisibility(str, Enum):
    normal = "normal"
    private = "private"
    secret = "secret"
    scheduled = "scheduled"

class CommentStatus(str, Enum):
    active = "active"
    hidden = "hidden"
    flagged = "flag"
    deleted = "deleted"

class ReactionType(str, Enum):
    heart = "❤️"
    laugh = "😂"
    surprise = "😮"
    sad = "😢"
    angry = "😡"
    thumbs_up = "👍"
    party_popper = "🎉"
    hundred = "💯"
    fire = "🔥"
    clapping = "👏"

class FileType(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"
    archive = "archive"
    other = "other"

class StorageBucket(str, Enum):
    avatars = "avatars"
    logos = "logos"
    events = "events"
    gallery = "gallery"
    timeline = "timeline"
    wishes = "wishes"
    voice_notes = "voice_notes"
    documents = "documents"
    themes = "themes"
    exports = "exports"

class NotificationType(str, Enum):
    wish_received = "wish_received"
    wish_approved = "wish_approved"
    comment_added = "comment_added"
    reaction_added = "reaction_added"
    event_published = "event_published"
    invite_received = "invite_received"
    vault_unlocked = "vault_unlocked"
    reminder = "reminder"

class LogAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    soft_delete = "soft_delete"
    restore = "restore"
    login = "login"
    logout = "logout"
    view = "view"
    download = "download"
    share = "share"

class SubscriptionTier(str, Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"

class SubscriptionStatus(str, Enum):
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    trialing = "trialing"
    paused = "paused"

class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    disputed = "disputed"

class ThemeType(str, Enum):
    preset = "preset"
    custom = "custom"
    premium = "premium"

class FontFamily(str, Enum):
    outfit = "outfit"
    poppins = "poppins"
    inter = "inter"
    roboto = "roboto"
    playfair = "playfair"
    montserrat = "montserrat"
    dancing_script = "dancing_script"
