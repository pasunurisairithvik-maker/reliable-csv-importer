"""Repeatable local benchmark, with fresh databases and identical reuploads."""
import json, platform, tempfile, time
from pathlib import Path
from app.importer import import_csv
results=[]
for count in (1000,10000):
    raw=("product_id,name,price,quantity\n"+"".join(f"P{i},Product {i},12.50,2\n" for i in range(count))).encode()
    runs=[]
    for repeat in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'inventory.db'
            start=time.perf_counter(); first=import_csv(raw,db); duration=time.perf_counter()-start
            start=time.perf_counter(); second=import_csv(raw,db); duplicate_duration=time.perf_counter()-start
            assert first['accepted']==count and second['skipped']==count
            runs.append({'fresh_seconds':round(duration,4),'reupload_seconds':round(duplicate_duration,4)})
    results.append({'rows':count,'runs':runs})
Path('results').mkdir(exist_ok=True)
report={'python':platform.python_version(),'platform':platform.platform(),'processor':platform.processor(),'results':results,'note':'Local import function timings; excludes HTTP/network overhead. Not production load testing.'}
Path('results/benchmark.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
