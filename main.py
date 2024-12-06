import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from models import Base, Person
from sqlalchemy import delete, select, func, or_


app = FastAPI()


DATABASE_URL = "sqlite+aiosqlite:///./genealogy.db"  # Используем асинхронный SQLite

# Создание асинхронного движка и сессии
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Pydantic модели для валидации
class PersonIn(BaseModel):
    full_name: str
    gender: str = None  # optional
    father_id: int = None  # optional
    mother_id: int = None  # optional


class PersonOut(BaseModel):
    id: int
    full_name: str
    gender: str = None
    father_id: int = None
    mother_id: int = None


@app.post("/persons/", response_model=PersonOut, summary="Создание человека")
async def create_person(person: PersonIn, db: AsyncSession = Depends(get_db)):
    db_person = Person(**person)
    db.add(db_person)
    await db.commit()
    await db.refresh(db_person)
    return db_person, {"succes": True}


@app.delete("/persons/{person_id}", summary="Удалить человека по id")
async def delete_person(person_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Человека не существует")

    await db.execute(delete(Person).where(Person.id == person_id))
    await db.commit()
    return {"success": True}


@app.get("/persons/", response_model=list[PersonOut], summary="Список людей")
async def read_persons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Person))
    return result.scalars().all()


@app.get(
    "/persons/count",
    summary="Приблизительное количество членов семьи (родители, дети, братья/сестры).",
)
async def get_family_size(person_id: int, db: AsyncSession = Depends(get_db)):
    count = await db.execute(
        select(func.count()).filter(
            or_(
                Person.id == person_id,
                Person.father_id == person_id,
                Person.mother_id == person_id,
            )
        )
    )
    return {"count": count.scalar()}


@app.get(
    "/persons/gen",
    summary="Приблизительное количество поколений (только по отцовской линии).",
)
async def get_approximate_generations(
    person_id: int, db: AsyncSession = Depends(get_db)
):
    person = await db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    generations = 0
    current_person = person

    while current_person.father_id is not None:
        current_person = await db.get(Person, current_person.father_id)
        if current_person is None:  # Добавлена проверка на None
            break
        generations += 1

    return generations + 1


@app.get("/persons/male_count", summary="Количество мужчин в семье")
async def get_male_count(person_id: int, db: AsyncSession = Depends(get_db)):
    family_members = await get_family_members(db, person_id)
    females_count = await db.execute(
        select(func.count())
        .where(Person.gender == "Male")
        .filter(Person.id.in_([member.id for member in family_members]))
    )
    return females_count.scalar()


@app.get("/persons/female_count", summary="Количество женщин в семье")
async def get_female_count(person_id: int, db: AsyncSession = Depends(get_db)):
    family_members = await get_family_members(db, person_id)
    females_count = await db.execute(
        select(func.count())
        .where(Person.gender == "Female")
        .filter(Person.id.in_([member.id for member in family_members]))
    )
    return females_count.scalar()


async def get_family_members(db: AsyncSession, person_id: int):
    person = await db.get(Person, person_id)
    if person is None:
        return []

    # Узнать всех членов семьи
    father_id = person.father_id
    mother_id = person.mother_id

    query = select(Person).where(
        or_(
            Person.id == person_id,
            Person.father_id == person_id,
            Person.mother_id == person_id,
            Person.id.in_([father_id] if father_id is not None else []),
            Person.id.in_([mother_id] if mother_id is not None else []),
        )
    )

    result = await db.execute(query)
    return result.scalars().all()


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
