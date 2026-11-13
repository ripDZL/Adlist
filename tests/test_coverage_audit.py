"""Source exclusivity must be independent of order and must preserve DNS coverage."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import coverage_audit as a


class CoverageTests(unittest.TestCase):
    def build_reports(self,ids=('a','b','c')):
        feeds = {'a':{'shared.vendor.net','a.vendor.net','parent.vendor.net','child.parent.vendor.net'},
                 'b':{'shared.vendor.net','b.vendor.net'},'c':{'b.vendor.net','c.vendor.net'}}
        tracker = a.Coverage(ids)
        sources = []
        for i,ident in enumerate(ids):
            tracker.add(i,feeds[ident])
            sources.append({'id':ident,'domains':len(feeds[ident]),'sha256':ident*64})
        names = set().union(*feeds.values())
        # Local allow removes c; pin keeps a even if feed a is individually removed.
        names.remove('c.vendor.net')
        custom = {'a.vendor.net','pin.vendor.net'}
        names.update(custom)
        files = tracker.reports(names,custom,sources,snapshot_sha256='0'*64,generated_utc='2026-10-18T00:00:00+00:00')
        return json.loads(files['coverage-audit.json']),files,names

    def test_true_exclusive_counts_are_independent_of_input_order(self):
        first,files,names = self.build_reports()
        second,_,_ = self.build_reports(('c','b','a'))
        def comparable(report): return {r['id']:(r['retained_final_names'],r['exclusive_final_names'],r['removed_by_final_allowlist']) for r in report['sources']}
        self.assertEqual(comparable(first),comparable(second))
        self.assertEqual(comparable(first),{'a':(4,2,0),'b':(2,0,0),'c':(1,0,1)})
        self.assertEqual(first['final_domains'],len(names))
        self.assertEqual(first['custom_only_names'],1)
        self.assertEqual(first['final_names_in_multiple_sources'],2)
        self.assertEqual(first['repeated_source_memberships_removed'],2)

    def test_pairwise_counts_and_parent_child_entries_are_preserved(self):
        report,files,names = self.build_reports()
        rows = list(csv.DictReader(io.StringIO(files['source-overlap.csv'].decode())))
        counts = {(r['source_a'],r['source_b']):int(r['shared_final_names']) for r in rows}
        self.assertEqual(counts,{('a','b'):1,('a','c'):0,('b','c'):1})
        self.assertEqual(report['children_with_listed_parent'],1)
        self.assertIn('parent.vendor.net',names)
        self.assertIn('child.parent.vendor.net',names)
        self.assertEqual(report['automatic_domain_removals'],0)

    def test_video_review_uses_label_boundary_and_does_not_remove(self):
        names = {'r1.video.googlevideo.com','evilgooglevideo.com','googlevideo.com','chatgpt.com'}
        report,raw = a.review_names(names)
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        flagged = {r['domain'] for r in rows}
        self.assertEqual(flagged,{'r1.video.googlevideo.com','googlevideo.com','chatgpt.com'})
        self.assertEqual(report['review_reason_counts']['video_delivery_domain_review_playback'],2)
        self.assertEqual(report['dns_lookups_performed'],0)
        self.assertEqual(report['automatic_domain_removals'],0)
        self.assertEqual(len(names),4)

    def test_review_attributes_every_flagged_domain_to_its_actual_sources(self):
        tracker = a.Coverage(['a','b'])
        tracker.add(0,{'r1.googlevideo.com'})
        tracker.add(1,{'r1.googlevideo.com','r2.googlevideo.com'})
        sources = [{'id':'a','domains':1,'sha256':'a'*64},{'id':'b','domains':2,'sha256':'b'*64}]
        files = tracker.reports(set(tracker.masks),set(),sources,snapshot_sha256='0'*64,generated_utc='old')
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(files['domain-review.csv.gz']).decode())))
        self.assertEqual({r['domain']:r['sources'] for r in rows},{'r1.googlevideo.com':'a;b','r2.googlevideo.com':'b'})

    def test_missing_source_and_unknown_final_provenance_fail(self):
        tracker = a.Coverage(['a','b'])
        tracker.add(0,{'a.vendor.net'})
        with self.assertRaises(a.BuildError):
            tracker.reports({'a.vendor.net'},set(),[{'id':'a','domains':1}],snapshot_sha256='x',generated_utc='x')
        tracker.add(1,{'b.vendor.net'})
        sources = [{'id':'a','domains':1},{'id':'b','domains':1}]
        with self.assertRaises(a.BuildError):
            tracker.reports({'missing.vendor.net'},set(),sources,snapshot_sha256='x',generated_utc='x')

    def test_legacy_report_does_not_invent_exclusive_counts(self):
        report = {'source_count':1,'sources':[{'id':'a','domains':5,'new_names_at_merge':5,'sha256':'a'*64}],
                  'sha256':'0'*64,'generated_utc':'original-build-time'}
        files = a.legacy_reports({'r1.googlevideo.com'},report)
        audit = json.loads(files['coverage-audit.json'])
        self.assertFalse(audit['source_overlap_available'])
        self.assertIsNone(audit['sources'][0]['exclusive_final_names'])
        self.assertEqual(audit['snapshot_generated_utc'],'original-build-time')
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(files['domain-review.csv.gz']).decode())))
        self.assertEqual(rows[0]['sources'],'unavailable-in-legacy-build')

    def test_report_hashes_and_snapshot_identity_are_checked(self):
        audit,files,_ = self.build_reports()
        report = {'sha256':audit['snapshot_sha256'],'domains':audit['final_domains'],
                  'sources':audit['sources'],'coverage_audit':a.file_metadata(files)}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            for name,raw in files.items(): (output/name).write_bytes(raw)
            self.assertTrue(a.verify_files(output,report)['source_overlap_available'])
            (output/'source-overlap.csv').write_bytes(b'wrong')
            with self.assertRaises(a.BuildError): a.verify_files(output,report)
            (output/'source-overlap.csv').write_bytes(files['source-overlap.csv'])
            report['sha256']='f'*64
            with self.assertRaises(a.BuildError): a.verify_files(output,report)


if __name__=='__main__': unittest.main()
