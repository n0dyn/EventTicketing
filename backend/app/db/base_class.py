import uuid
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, String


class Base(DeclarativeBase):
    __allow_unmapped__ = True
    
    # Generate tablename automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Common columns for all models
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) 