from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()
engine = create_engine('sqlite:///debits.db')
Session = sessionmaker(bind=engine)


class UserDebit(Base):
    __tablename__ = 'user_debits'

    id = Column(Integer, primary_key=True)
    user = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    link = Column(String)
    workspace = Column(String, nullable=False)

    def __repr__(self):
        return f"<UserDebit(user='{self.user}', amount='{self.amount}', link='{self.link}', workspace='{self.workspace}')>"


Base.metadata.create_all(engine)


def record_debit(user_id, workspace_id, amount, link=None):
    session = Session()
    existing_debit = session.query(UserDebit).filter_by(user=user_id, workspace=workspace_id).first()

    if existing_debit:
        previous_amount = existing_debit.amount
        existing_debit.amount += amount
        current_amount = existing_debit.amount
    else:
        previous_amount = 0.0
        new_debit = UserDebit(user=user_id, workspace=workspace_id, amount=amount, link=link)
        session.add(new_debit)
        current_amount = amount

    session.commit()
    session.close()

    return previous_amount, amount, current_amount


def remove_debit(user_id, workspace_id, amount, link=None):
    global previous_amount, current_amount
    session = Session()
    existing_debit = session.query(UserDebit).filter_by(user=user_id, workspace=workspace_id).first()

    if existing_debit:
        previous_amount = existing_debit.amount
        if existing_debit.amount >= amount:
            existing_debit.amount -= amount
            current_amount = existing_debit.amount
            if link:
                existing_debit.link = link
        else:
            session.delete(existing_debit)

    session.commit()
    session.close()

    return previous_amount, amount, current_amount


def get_single_user(user_id, workspace_id):
    session = Session()
    user_data = session.query()

def get_all_points(workspace_id):
    session = Session()
    existing_debit = session.query(UserDebit).filter_by(workspace=workspace_id)
    print(existing_debit)
    session.commit()
    session.close()

