from loguru import logger

from persistence.database import get_session
from persistence.models import Feedback


def save_feedback(report_type, description, contact):
    try:
        with get_session() as session:
            feed = Feedback(
                report_type=report_type, description=description, contact=contact
            )
            session.add(feed)
    except Exception as e:
        logger.error(e)
        raise
