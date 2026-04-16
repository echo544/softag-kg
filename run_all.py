# runs every stage in order and reports pass/fail per step, overwrites existing files

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPTS = ROOT / "scripts"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok = True)

results = {}

def run(label, script): # returns True if successful
    print(label)
    print()
    start = time.time()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        cwd=str(ROOT),
    )
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"\n{label} PASSED, time elapsed: {elapsed:.1f}s")
        return True
    else:
        print(f"\n{label} FAILED with exit code {result.returncode}")
        return False

print("SOFTagKG")
print(f"Root: {str(ROOT)}")
print(f"Output: {str(OUTPUT)}")
print()

# build the KG
ok = run("Step 1/6 — Build graph (build_graph.py)", "build_graph.py")
results["build_graph"] = ok
if not ok:
    print("\n  unable to proceed (build_graph.py must succeed before continuing)")
    sys.exit(1)

# verify the KG
ok = run("Step 2/6 — Verify graph (verify_graph.py)", "verify_graph.py")
results["verify"] = ok
if not ok:
    print("\n  issues with verifying graph")

# run quality assessment (metrics)
ok = run("Step 3/6 — Quality assessment (quality_assessment.py)", "quality_assessment.py")
results["quality"] = ok

# create graphs/visuals (png files for report)
ok = run("Step 4/6 — Visualisations (visualise.py)", "visualise.py")
results["visualise"] = ok
if not ok:
    print("\n  visualise.py failed, affects report.pdf")

# run SPARQL queries
ok = run("Step 5/6 — SPARQL queries (queries.py)", "queries.py")
results["queries"] = ok

# build report file (PDF output)
ok = run("Step 6/6 — Build report (build_report.py)", "build_report.py")
results["report"] = ok

# print summary
print()
print("SUMMARY")
print()
step_labels = {
    "build_graph": "Build graph        (softagkg.ttl)",
    "verify":      "Verify graph       (verify_graph.py)",
    "quality":     "Quality assessment (quality_assessment.py)",
    "visualise":   "Visualisations     (3 png output figures)",
    "queries":     "SPARQL queries     (12 queries)",
    "report":      "Report             (report.pdf)",
}
all_pass = True
for key, label in step_labels.items():
    status = "PASS" if results.get(key) else "FAIL"
    if not results.get(key):
        all_pass = False
    print(f"{status} — {label}")

# list produced files
print()
print(f"Output directory: {str(OUTPUT)}")
for f in sorted(OUTPUT.glob("*")):
    print(f"  {f.name:<40} ")

if all_pass:
    print()
    print("All steps passed.")
else:
    print()
    print("Some steps failed — check above.")
sys.exit(0 if all_pass else 1)