from datetime import datetime
from typing import Annotated

import msgspec
from msgspec import UNSET, Meta, UnsetType

Title = Annotated[str, Meta(min_length=1, max_length=200)]
Content = Annotated[str, Meta(min_length=1)]
Author = Annotated[str, Meta(min_length=1, max_length=100)]
Category = Annotated[str, Meta(max_length=50)]


class BookCreate(msgspec.Struct, forbid_unknown_fields=True):
    title: Title
    content: Content
    author: Author
    category: Category | None = None


class BookUpdate(msgspec.Struct, forbid_unknown_fields=True):
    """Partial update: omitted fields are left alone; `category: null` clears the category."""

    title: Title | UnsetType = UNSET
    content: Content | UnsetType = UNSET
    author: Author | UnsetType = UNSET
    category: Category | None | UnsetType = UNSET

    def changes(self) -> dict[str, str | None]:
        values = {name: getattr(self, name) for name in self.__struct_fields__}
        return {name: value for name, value in values.items() if value is not UNSET}


class BookSummary(msgspec.Struct):
    """List shape: omits `content` (can get large) and `updated_at`."""

    id: int
    title: str
    author: str
    category: str | None
    servername: str
    created_at: datetime


class BookRead(msgspec.Struct):
    id: int
    title: str
    content: str
    author: str
    category: str | None
    servername: str
    created_at: datetime
    updated_at: datetime
