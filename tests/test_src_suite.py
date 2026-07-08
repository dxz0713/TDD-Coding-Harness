"""Compatibility entry point for running ``pytest tests/``.

The project keeps its tests next to the source package under ``src/tests``.
This module re-exports that suite for users or CI jobs that expect a top-level
``tests`` directory.
"""

from tests.test_analyzer import *  # noqa: F401,F403
from tests.test_cli import *  # noqa: F401,F403
from tests.test_config import *  # noqa: F401,F403
from tests.test_context import *  # noqa: F401,F403
from tests.test_credential_manager import *  # noqa: F401,F403
from tests.test_feedback_engine import *  # noqa: F401,F403
from tests.test_guardrail import *  # noqa: F401,F403
from tests.test_loop import *  # noqa: F401,F403
from tests.test_loop_integration import *  # noqa: F401,F403
from tests.test_memory import *  # noqa: F401,F403
from tests.test_models import *  # noqa: F401,F403
from tests.test_providers import *  # noqa: F401,F403
from tests.test_stop_condition import *  # noqa: F401,F403
from tests.test_tools import *  # noqa: F401,F403
