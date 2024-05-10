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


class ResetMode(Base):
    __tablename__ = 'reset_mode'

    id = Column(Integer, primary_key=True)
    reset_date = Column(Integer, nullable=False)
    reset_mode = Column(String, nullable=False)
    workspace = Column(String, nullable=False)

    def __repr__(self):
        return f"<ResetMode(reset_date='{self.reset_date}', mode='{self.reset_mode}', workspace='{self.workspace}')>"


Base.metadata.create_all(engine)


def record_debit(user_id: str, workspace_id: str, amount: str | int, link=None):
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


def remove_debit(user_id: str, workspace_id: str, amount: str | int, link=None):
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


def get_single_user(user_id: str, workspace_id: str) -> tuple:
    try:
        with Session() as session:
            user_data = session.query(UserDebit).filter_by(user=user_id, workspace=workspace_id).first()
            if user_data:
                user = user_data.user
                amount = user_data.amount
                return user, amount
            else:
                return None, None
    except Exception as e:
        print(f"An error occurred while retrieving single user data: {e}")
        return None, None


def get_all_points(workspace_id: str) -> list:
    try:
        with Session() as session:
            existing_debit = session.query(UserDebit).filter_by(workspace=workspace_id).order_by(
                UserDebit.amount.desc()).all()
            return existing_debit
    except Exception as e:
        print(f"An error occurred while retrieving points data: {e}")
        return []


def set_reset_mode(workspace_id: str, day: int, mode: str):
    try:
        with Session() as session:
            reset_data = session.query(ResetMode).filter_by(workspace=workspace_id).first()
            if reset_data:
                reset_data.reset_mode = mode
                reset_data.day = day
            else:
                new_reset_data = ResetMode(reset_date=day, reset_mode=mode, workspace=workspace_id)
                session.add(new_reset_data)

        session.commit()
        session.close()
    except Exception as e:
        print(f"An error occurred while trying to update reset {e}")