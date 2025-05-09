import datetime
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

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


class Checklist(Base):
    __tablename__ = 'checklists'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    workspace = Column(String, nullable=False)
    creator = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<Checklist(name='{self.name}', workspace='{self.workspace}', creator='{self.creator}')>"


class ChecklistItem(Base):
    __tablename__ = 'checklist_items'

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<ChecklistItem(checklist_id='{self.checklist_id}', text='{self.text}', order='{self.order}')>"


class ChecklistInstance(Base):
    __tablename__ = 'checklist_instances'

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, nullable=False)
    channel = Column(String, nullable=False)
    message_ts = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=False)
    is_complete = Column(Integer, default=0)  # 0 = incomplete, 1 = complete
    
    def __repr__(self):
        return f"<ChecklistInstance(checklist_id='{self.checklist_id}', channel='{self.channel}')>"


class ChecklistItemStatus(Base):
    __tablename__ = 'checklist_item_status'

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, nullable=False)
    item_id = Column(Integer, nullable=False)
    is_checked = Column(Integer, default=0)  # 0 = unchecked, 1 = checked
    checked_by = Column(String, nullable=True)
    checked_at = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<ChecklistItemStatus(instance_id='{self.instance_id}', item_id='{self.item_id}', is_checked='{self.is_checked}')>"



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


def create_checklist(name, workspace_id, creator, items):
    """Create a new checklist with the given name and items"""
    try:
        with Session() as session:
            timestamp = datetime.datetime.now().isoformat()
            new_checklist = Checklist(
                name=name,
                workspace=workspace_id,
                creator=creator,
                created_at=timestamp
            )
            session.add(new_checklist)
            session.flush()  # Flush to get the ID
            
            # Add items
            for i, item_text in enumerate(items):
                item = ChecklistItem(
                    checklist_id=new_checklist.id,
                    text=item_text,
                    order=i
                )
                session.add(item)
            
            session.commit()
            return True
    except Exception as e:
        print(f"Error creating checklist: {e}")
        return False


def get_checklist_by_name(name, workspace_id):
    """Get a checklist by name"""
    try:
        with Session() as session:
            checklist = session.query(Checklist).filter_by(
                name=name,
                workspace=workspace_id
            ).first()
            
            if not checklist:
                return None
                
            # Get items
            items = session.query(ChecklistItem).filter_by(
                checklist_id=checklist.id
            ).order_by(ChecklistItem.order).all()
            
            return {
                "id": checklist.id,
                "name": checklist.name,
                "creator": checklist.creator,
                "created_at": checklist.created_at,
                "items": [(item.id, item.text) for item in items]
            }
    except Exception as e:
        print(f"Error getting checklist: {e}")
        return None


def get_all_checklists(workspace_id):
    """Get all checklists for a workspace"""
    try:
        with Session() as session:
            checklists = session.query(Checklist).filter_by(
                workspace=workspace_id
            ).all()
            
            return [c.name for c in checklists]
    except Exception as e:
        print(f"Error getting checklists: {e}")
        return []


def create_checklist_instance(checklist_id, channel, message_ts):
    """Create a new instance of a checklist in a channel"""
    try:
        with Session() as session:
            # Get all items for the checklist
            items = session.query(ChecklistItem).filter_by(
                checklist_id=checklist_id
            ).all()
            
            if not items:
                return None
                
            # Create the instance
            timestamp = datetime.datetime.now().isoformat()
            instance = ChecklistInstance(
                checklist_id=checklist_id,
                channel=channel,
                message_ts=message_ts,
                created_at=timestamp,
                is_complete=0
            )
            session.add(instance)
            session.flush()  # To get the ID
            
            # Create item statuses
            for item in items:
                status = ChecklistItemStatus(
                    instance_id=instance.id,
                    item_id=item.id,
                    is_checked=0
                )
                session.add(status)
                
            session.commit()
            return instance.id
    except Exception as e:
        print(f"Error creating checklist instance: {e}")
        return None


def update_checklist_item(instance_id, item_id, checked, user_id):
    """Update the status of a checklist item"""
    try:
        with Session() as session:
            item_status = session.query(ChecklistItemStatus).filter_by(
                instance_id=instance_id,
                item_id=item_id
            ).first()
            
            if not item_status:
                return False
                
            item_status.is_checked = 1 if checked else 0
            if checked:
                item_status.checked_by = user_id
                item_status.checked_at = datetime.datetime.now().isoformat()
            else:
                item_status.checked_by = None
                item_status.checked_at = None
                
            # Check if all items are checked
            all_items = session.query(ChecklistItemStatus).filter_by(
                instance_id=instance_id
            ).all()
            
            all_checked = all(item.is_checked == 1 for item in all_items)
            
            # Update instance status if needed
            if all_checked:
                instance = session.query(ChecklistInstance).filter_by(
                    id=instance_id
                ).first()
                if instance:
                    instance.is_complete = 1
                    instance.completed_at = datetime.datetime.now().isoformat()  # Add this line

            session.commit()
            
            return {
                "all_complete": all_checked,
                "checklist_instance": instance_id
            }
    except Exception as e:
        print(f"Error updating checklist item: {e}")
        return False


def get_checklist_instance(instance_id):
    """Get a checklist instance with all items and their statuses"""
    try:
        with Session() as session:
            instance = session.query(ChecklistInstance).filter_by(
                id=instance_id
            ).first()
            
            if not instance:
                return None
                
            # Get the checklist
            checklist = session.query(Checklist).filter_by(
                id=instance.checklist_id
            ).first()
            
            if not checklist:
                return None
                
            # Get all items with their statuses
            items_with_status = session.execute(
                text("""
                    SELECT ci.id, ci.text, cis.is_checked, cis.checked_by, cis.checked_at
                    FROM checklist_items ci
                    JOIN checklist_item_status cis ON ci.id = cis.item_id
                    WHERE cis.instance_id = :instance_id
                    ORDER BY ci."order"
                """),
                {"instance_id": instance_id}
            ).fetchall()
            
            return {
                "instance_id": instance.id,
                "checklist_id": checklist.id,
                "name": checklist.name,
                "channel": instance.channel,
                "is_complete": instance.is_complete,
                "completed_at": instance.completed_at,  # Add this line
                "items": [
                    {
                        "id": item[0],
                        "text": item[1],
                        "is_checked": item[2],
                        "checked_by": item[3],
                        "checked_at": item[4]
                    }
                    for item in items_with_status
                ]
            }
    except Exception as e:
        print(f"Error getting checklist instance: {e}")
        return None


def delete_checklist(name, workspace_id):
    """Delete a checklist by name"""
    try:
        with Session() as session:
            checklist = session.query(Checklist).filter_by(
                name=name,
                workspace=workspace_id
            ).first()

            if not checklist:
                return False

            # Get all items
            items = session.query(ChecklistItem).filter_by(
                checklist_id=checklist.id
            ).all()

            # Get all instances
            instances = session.query(ChecklistInstance).filter_by(
                checklist_id=checklist.id
            ).all()

            # Delete all item statuses for all instances
            for instance in instances:
                session.query(ChecklistItemStatus).filter_by(
                    instance_id=instance.id
                ).delete()

            # Delete instances
            session.query(ChecklistInstance).filter_by(
                checklist_id=checklist.id
            ).delete()

            # Delete items
            session.query(ChecklistItem).filter_by(
                checklist_id=checklist.id
            ).delete()

            # Delete checklist
            session.query(Checklist).filter_by(
                id=checklist.id
            ).delete()

            session.commit()
            return True
    except Exception as e:
        print(f"Error deleting checklist: {e}")
        return False