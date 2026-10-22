"""Use the same environment-derived connection configuration as the API."""
from alembic import context

from app.config import get_settings
from app.database import Base, get_engine

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
