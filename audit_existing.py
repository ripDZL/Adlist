#!/usr/bin/env python3
"""Audit a verified completed build without downloading or changing its names."""
import argparse
import json
from pathlib import Path
import sys

import build_adlist as b
from coverage_audit import legacy_reports, AUDIT_FILES, verify_files


def audit_existing(source,output):
    source = source.resolve(strict=True)
    output = output.resolve()
    if source==output or source in output.parents or output in source.parents:
        raise b.BuildError('Use a separate audit output folder outside the completed build')
    output.mkdir(parents=True,exist_ok=True)
    with b.build_lock(source), b.build_lock(output):
        cfg = b.config_at(source/'sources.json')
        checked = b.verify_output(source,cfg)
        report = json.loads(b.decode(b.read_bounded(source/'stats.json',1048576)))
        if report.get('coverage_audit') is not None:
            result = verify_files(source,report)
            files = {name:b.read_bounded(source/name,b.MAX_OUTPUT) for name in AUDIT_FILES}
        else:
            data = b.read_bounded(source/'merged_hosts.txt',cfg['max_output_bytes'])
            names,_ = b.parse_hosts(b.decode(data),cfg['max_domains'])
            files = legacy_reports(names,report)
            result = json.loads(files['coverage-audit.json'])
        b.recover_transaction(output)
        b.publish_files(output,files)
        return {'verified':True,'domains':checked['domains'],'duplicates':0,
                'review_candidates':result['review_candidate_domains'],
                'source_overlap_available':result['source_overlap_available'],
                'reports_folder':str(output),
                'note':'Review candidates require investigation; no names or router settings were changed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-folder',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=b.ROOT/'domain-audit')
    args = parser.parse_args()
    try:
        result = audit_existing(args.build_folder,args.output)
        print(json.dumps(result,indent=2))
        return 0
    except (b.BuildError,OSError,ValueError,KeyError,TypeError) as exc:
        print(f'Audit failed: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
