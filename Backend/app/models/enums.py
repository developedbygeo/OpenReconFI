import enum


class InvoiceSource(str, enum.Enum):
    gmail = "gmail"
    portal = "portal"
    manual = "manual"


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    unmatched = "unmatched"
    flagged = "flagged"


class TransactionStatus(str, enum.Enum):
    unmatched = "unmatched"
    matched = "matched"
    no_invoice = "no_invoice"
    withholding = "withholding"


class ConfirmedBy(str, enum.Enum):
    llm = "llm"
    user = "user"
    deterministic = "deterministic"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    annual = "annual"
    one_off = "one_off"


class JobType(str, enum.Enum):
    gmail_sync = "gmail_sync"
    portal_scrape = "portal_scrape"
    reconcile = "reconcile"


class JobStatus(str, enum.Enum):
    running = "running"
    done = "done"
    failed = "failed"


class TriggeredBy(str, enum.Enum):
    user = "user"


class TimeframeType(str, enum.Enum):
    single_month = "single_month"
    quarter = "quarter"
    ytd = "ytd"
    full_year = "full_year"
    custom = "custom"


class ReportFormat(str, enum.Enum):
    pdf = "pdf"
    excel = "excel"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
