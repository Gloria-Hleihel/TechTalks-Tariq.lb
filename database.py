from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime


# STEP 1: Create the engine (connection to the database file)
engine = create_engine("sqlite:///reports.db", echo=True)


# STEP 2: Create the Base (foundation all tables are built on)
Base = declarative_base()


# STEP 3: Define the Report model (this becomes a table in the database)
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Report id={self.id} title='{self.title}'>"


# STEP 4: Create the actual table in the database file
Base.metadata.create_all(engine)


# STEP 5: Test it
with Session(engine) as session:

    test_report = Report(
        title="First Report",
        content="This is a test to confirm the database is working."
    )

    session.add(test_report)
    session.commit()

    all_reports = session.query(Report).all()
    print("\n--- Reports in database ---")
    for report in all_reports:
        print(report)