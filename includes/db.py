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
    reset_mode = Column(String, nullable=False)
    workspace = Column(String, nullable=False)

    def __repr__(self):
        return f"<ResetMode(reset_mode='{self.reset_mode}', workspace='{self.workspace}')>"


class ReportSchedule(Base):
    __tablename__ = 'reports_schedule'

    id = Column(Integer, primary_key=True)
    day = Column(String, nullable=False)
    hour = Column(Integer, nullable=False)
    workspace = Column(String, nullable=False)

    def __repr__(self):
        return f"<ReportSchedule(day='{self.day}', hour='{self.hour}', workspace='{self.workspace}')>"


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


def remove_debit(user_id: str, workspace_id: str, amount: int, link=None) -> tuple:
    previous_amount = current_amount = None
    try:
        with Session() as session:
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
            return previous_amount, amount, current_amount
    except Exception as e:
        print(f"An error occurred while removing debit: {e}")
        return None, None, None


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


def set_reset_mode(workspace_id: str, mode: str) -> None:
    try:
        with Session() as session:
            reset_data = session.query(ResetMode).filter_by(workspace=workspace_id).first()
            if reset_data:
                reset_data.reset_mode = mode
            else:
                new_reset_data = ResetMode(reset_mode=mode, workspace=workspace_id)
                session.add(new_reset_data)
            session.commit()
            session.close()
    except Exception as e:
        print(f"An error occurred while trying to update reset: {e}")


def get_reset_mode():
    try:
        with Session() as session:
            reset_modes = session.query(ResetMode).all()
            if reset_modes:
                return reset_modes
    except Exception as e:
        print(f"An error occurred while trying to retrieve reset mode: {e}")


def reset_debits_table(workspace_id: str) -> None:
    try:
        with Session() as session:
            deleted_rows = session.query(UserDebit).filter_by(workspace=workspace_id).delete(synchronize_session=False)
            session.commit()
            print(f"{deleted_rows} rows deleted from the user_debits table for workspace {workspace_id}")
    except Exception as e:
        print(f"An error occurred while trying to reset the database: {e}")


def set_report_daytime(workspace_id: str, day: str, hour: int) -> None:
    try:
        with Session() as session:
            report_schedule = session.query(ReportSchedule).filter_by(workspace=workspace_id).first()
            if report_schedule:
                report_schedule.day = day
                report_schedule.hour = hour
            else:
                new_report_schedule = ReportSchedule(day=day, hour=hour, workspace=workspace_id)
                session.add(new_report_schedule)

            session.commit()
            session.close()
    except Exception as e:
        print(f"An error occurred while trying to set a new report time: {e}")


def get_report_daytime():
    try:
        with Session() as session:
            report_schedules = session.query(ReportSchedule).all()
            if report_schedules:
                return report_schedules
    except Exception as e:
        print(f"An error occurred while trying to retrieve report schedules: {e}")
