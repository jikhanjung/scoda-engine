"""
Backward-compatibility shim.
All core functionality has moved to scoda_engine_core.scoda_package.
"""
import scoda_engine_core.scoda_package as _core_module
import sys
sys.modules[__name__] = _core_module
