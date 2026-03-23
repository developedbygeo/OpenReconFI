import uuid

from sqlalchemy import Enum, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import BillingCycle


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    aliases: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True, default=list
    )
    default_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_vat_rate: Mapped[float | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle", native_enum=True),
        nullable=False,
        default=BillingCycle.monthly,
    )
