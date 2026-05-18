from enum import Enum


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Category(str, Enum):
    FLOOD = "FLOOD"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    CYBER = "CYBER"
    PUBLIC_SAFETY = "PUBLIC_SAFETY"
    PUBLIC_SERVICES = "PUBLIC_SERVICES"
    UTILITIES = "UTILITIES"
    OTHER = "OTHER"


class IncidentStatus(str, Enum):
    PENDING = "PENDING"
    CLASSIFIED = "CLASSIFIED"
    ANALYZING = "ANALYZING"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"


class SpecialistStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
