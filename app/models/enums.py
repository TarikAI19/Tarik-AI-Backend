from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MUSEUM_ADMIN = "MUSEUM_ADMIN"
    CURATOR = "CURATOR"


class ExhibitStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class Language(str, Enum):
    EN = "EN"
    AM = "AM"
    OM = "OM"
    AR = "AR"


class Persona(str, Enum):
    HISTORIAN = "HISTORIAN"
    KID_FRIENDLY = "KID_FRIENDLY"
    GHOST_MODE = "GHOST_MODE"


class ContentStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
