from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    gender = Column(String, nullable=True)
    father_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    mother_id = Column(Integer, ForeignKey("persons.id"), nullable=True)

    father = relationship(
        "Person", remote_side=[id], foreign_keys=[father_id], backref="children_father"
    )
    mother = relationship(
        "Person", remote_side=[id], foreign_keys=[mother_id], backref="children_mother"
    )
