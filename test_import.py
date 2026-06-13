import os
import sys

_archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_archive")
print("Archive dir exists:", os.path.exists(_archive_dir))
sys.path.insert(0, _archive_dir)
print("Sys path:", sys.path)

try:
    from _archive.enrich_all import PHASE1_SUBJECTS
    print("SUCCESS importing enrich_all!")
except Exception as e:
    import traceback
    traceback.print_exc()
