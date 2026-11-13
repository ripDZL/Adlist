"""Exact-name source overlap and review candidates. No removals or DNS queries."""
from collections import Counter
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import io
import json

from pipeline_core import BuildError, read_bounded

AUDIT_FILES = ('coverage-audit.json','source-overlap.csv','domain-review.csv.gz')
MAX_AUDIT_BYTES = 256*1048576
# Exact names to review if present, not a global allowlist or a safety verdict.
REVIEW_EXACT = {
    'google.com','www.google.com','youtube.com','www.youtube.com',
    'googlevideo.com','gstatic.com','cloudfront.net','amazonaws.com',
    'akamaized.net','github.com','raw.githubusercontent.com','githubusercontent.com',
    'microsoft.com','windowsupdate.com','login.live.com','login.microsoftonline.com',
    'apple.com','icloud.com','amazon.com','chatgpt.com','openai.com','api.openai.com',
    'steamcommunity.com','steampowered.com','store.steampowered.com',
}


def csv_bytes(rows):
    out = io.StringIO(newline='')
    csv.writer(out).writerows(rows)
    return out.getvalue().encode('utf-8')


def file_metadata(files):
    return {name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items()}


class Coverage:
    def __init__(self,source_ids):
        self.ids = list(source_ids)
        if not self.ids or len(set(self.ids))!=len(self.ids) or len(self.ids)>64:
            raise BuildError('Invalid audit source IDs')
        self.masks = {}
        self.values = {}
        self.accepted = []

    def add(self,index,names):
        if index!=len(self.accepted) or index>=len(self.ids):
            raise BuildError('Audit source order mismatch')
        bit = 1<<index
        for name in names:
            value = self.masks.get(name,0)|bit
            self.masks[name] = self.values.setdefault(value,value)
        self.accepted.append(len(names))

    def reports(self,names,custom,sources,*,snapshot_sha256,generated_utc):
        if len(self.accepted)!=len(self.ids) or [s['id'] for s in sources]!=self.ids:
            raise BuildError('Incomplete source coverage audit')
        custom_bit = 1<<len(self.ids)
        histogram = Counter(self.masks.get(n,0)|(custom_bit if n in custom else 0) for n in names)
        if histogram.get(0):
            raise BuildError('A final domain has no source or custom provenance')
        retained = [0]*len(self.ids)
        exclusive = [0]*len(self.ids)
        pairwise = [[0]*len(self.ids) for _ in self.ids]
        source_histogram = Counter()
        for mask,count in histogram.items():
            members = [i for i in range(len(self.ids)) if mask&(1<<i)]
            source_histogram[len(members)]+=count
            for i in members:
                retained[i]+=count
                if mask==(1<<i): exclusive[i]+=count
                for j in members: pairwise[i][j]+=count
        rows = []
        for i,source in enumerate(sources):
            if source['domains']!=self.accepted[i]:
                raise BuildError('Audit parsed count mismatch')
            rows.append({'id':self.ids[i],'accepted_names':self.accepted[i],
                'retained_final_names':retained[i], 'exclusive_final_names':exclusive[i],
                'covered_by_other_inputs':retained[i]-exclusive[i],
                'removed_by_final_allowlist':self.accepted[i]-retained[i],
                'duplicate_rules_in_source':source.get('duplicate_names',0),
                'source_sha256':source['sha256']})
        overlap = [['source_a','source_b','shared_final_names','a_final_names','b_final_names']]
        for i in range(len(self.ids)):
            for j in range(i+1,len(self.ids)):
                overlap.append([self.ids[i],self.ids[j],pairwise[i][j],retained[i],retained[j]])
        report,review = review_names(names,self.ids,self.masks,custom)
        report.update(source_overlap_available=True,source_count=len(self.ids),sources=rows,
            input_domain_memberships=sum(self.accepted),final_source_memberships=sum(k*v for k,v in source_histogram.items()),
            repeated_source_memberships_removed=sum((k-1)*v for k,v in source_histogram.items() if k>1),
            final_names_in_multiple_sources=sum(v for k,v in source_histogram.items() if k>1),
            source_membership_histogram={str(k):v for k,v in sorted(source_histogram.items())},
            custom_only_names=histogram.get(custom_bit,0),
            note='Exclusive counts are independent of source order. Zero exclusive names means one input can be omitted for this snapshot; do not remove multiple such inputs simultaneously without recomputing. Pinned custom names count as another input. Review flags are not automatic exclusions.')
        return finish(report,review,overlap,snapshot_sha256,generated_utc)


def review_names(names,source_ids=(),masks=None,custom=()):
    flags = Counter()
    rows = [['domain','review_reason','sources','custom_pinned']]
    parent_examples = []
    parent_count = 0
    for name in sorted(names):
        reasons = []
        if name=='googlevideo.com' or name.endswith('.googlevideo.com'):
            reasons.append('video_delivery_domain_review_playback')
        if name in REVIEW_EXACT:
            reasons.append('shared_service_exact_name_review_functionality')
        if len(name)>200:
            reasons.append('unusually_long_valid_hostname_review_only')
        for reason in reasons: flags[reason]+=1
        if reasons:
            origin = ';'.join(s for i,s in enumerate(source_ids) if masks.get(name,0)&(1<<i)) if masks is not None else 'unavailable-in-legacy-build'
            rows.append([name,';'.join(reasons),origin,name in custom])
        labels = name.split('.')
        for i in range(1,len(labels)-1):
            parent = '.'.join(labels[i:])
            if parent in names:
                parent_count+=1
                if len(parent_examples)<20: parent_examples.append({'child':name,'parent':parent})
                break
    return {'final_domains':len(names),'exact_duplicate_names_in_published_output':0,
        'review_candidate_domains':len(rows)-1,'review_reason_counts':dict(flags),
        'children_with_listed_parent':parent_count,'parent_child_examples':parent_examples,
        'parent_child_policy':'Keep both: RouterOS adlists match exact names. A listed parent does not replace an explicit child. No suffix pruning was performed.',
        'dns_lookups_performed':0,'automatic_domain_removals':0},csv_bytes(rows)


def finish(report,review,overlap,snapshot_sha256,generated_utc):
    if len(review)>MAX_AUDIT_BYTES:
        raise BuildError('Review CSV exceeds the bounded audit size')
    report.update(schema_version=1,audited_utc=datetime.now(timezone.utc).isoformat(),
        snapshot_sha256=snapshot_sha256,snapshot_generated_utc=generated_utc,
        scope='Entire validated final domain snapshot; source overlap only when full provenance is available',
        necessity='Membership, overlap and syntax do not establish that a domain is harmful or unnecessary. No live DNS/nonresolution pruning or usage-based removals are performed.')
    return {'coverage-audit.json':(json.dumps(report,indent=2)+'\n').encode(),
        'source-overlap.csv':csv_bytes(overlap),
        'domain-review.csv.gz':gzip.compress(review,compresslevel=6,mtime=0)}


def legacy_reports(names,report):
    result,review = review_names(names)
    result.update(source_overlap_available=False,source_count=report['source_count'],
        sources=[{'id':s['id'],'accepted_names':s['domains'],'first_merge_new_names':s['new_names_at_merge'],
                  'exclusive_final_names':None,'source_sha256':s['sha256']} for s in report['sources']],
        note='Legacy output has no per-domain source provenance. Exclusive source contributions cannot be recovered from merge-order counts. Run a new complete build with version 3.0.2 to measure them.')
    return finish(result,review,[['source_a','source_b','shared_final_names','a_final_names','b_final_names']],report['sha256'],report['generated_utc'])


def verify_files(output,report):
    metadata = report.get('coverage_audit')
    if not isinstance(metadata,dict) or set(metadata)!=set(AUDIT_FILES):
        raise BuildError('Invalid coverage audit file manifest')
    for name in AUDIT_FILES:
        raw = read_bounded(output/name,MAX_AUDIT_BYTES)
        if metadata[name]!={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:
            raise BuildError('Coverage audit hash/size mismatch')
    data = json.loads(read_bounded(output/'coverage-audit.json',1048576))
    if (data.get('snapshot_sha256')!=report['sha256'] or data.get('final_domains')!=report['domains']
            or [s['id'] for s in data.get('sources',[])]!=[s['id'] for s in report['sources']]):
        raise BuildError('Coverage audit does not describe this publication')
    return data
