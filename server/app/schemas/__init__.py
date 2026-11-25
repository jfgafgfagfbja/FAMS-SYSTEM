"""Schema Pydantic theo module. Giu `from app import schemas; schemas.X` nhu ban goc."""
from app.modules.m01_auth.schemas import *  # noqa: F401,F403  (MOD-01)
from app.schemas.organization import *  # noqa: F401,F403
from app.schemas.locations import *  # noqa: F401,F403
from app.schemas.lecturers import *  # noqa: F401,F403
from app.schemas.classes import *  # noqa: F401,F403
from app.schemas.schedules import *  # noqa: F401,F403
from app.schemas.students import *  # noqa: F401,F403
from app.schemas.parents import *  # noqa: F401,F403
from app.schemas.faces import *  # noqa: F401,F403
from app.schemas.attendance import *  # noqa: F401,F403
from app.schemas.leaves import *  # noqa: F401,F403
from app.schemas.reports import *  # noqa: F401,F403
from app.schemas.notifications import *  # noqa: F401,F403
from app.schemas.audit_logs import *  # noqa: F401,F403
