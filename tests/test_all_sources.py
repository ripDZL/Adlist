"""Coverage/completeness semantics and real publication safety, without network."""
import argparse
import contextlib
import copy
import gzip
import hashlib
from datetime import datetime,timezone,timedelta
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import audit_existing

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('all31_builder',ROOT/'build_adlist.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class AllSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root/'inputs'
        self.inputs.mkdir()
        self.output = self.root/'output'
        self.config = self.root/'sources.json'
        self.allow = self.root/'allowlist.txt'
        self.block = self.root/'blocklist.txt'
        self.allow.write_text('')
        self.block.write_text('')
        self.cfg = json.loads((ROOT/'sources.json').read_text())
        self.cfg.update(min_domains=1,max_domains=1000)
        stamp = datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')
        for i,source in enumerate(self.cfg['sources']):
            source.update(min_domains=1,max_domains=100)
            header = f'! Last modified: {stamp}\n! Number of entries: 2\n' if source['format']=='abp' else ''
            entries = [f'source{i}.vendor.net','shared.vendor.net']
            raw = header+''.join((f'||{name}^\n' if source['format']=='abp' else f'0.0.0.0 {name}\n') for name in entries)
            (self.inputs/(source['id']+'.txt')).write_text(raw)
        self.save_config()
        self.args = argparse.Namespace(config=self.config,output=self.output,
            allowlist=self.allow,blocklist=self.block,input_dir=self.inputs,
            dry_run=False,accept_large_change=False)

    def save_config(self):
        self.config.write_text(json.dumps(self.cfg))

    def build(self):
        with contextlib.redirect_stderr(io.StringIO()):
            return b.run(self.args)

    def snapshot(self):
        return {p.relative_to(self.output).as_posix():p.read_bytes() for p in self.output.rglob('*') if p.is_file() and p.name!='.build.lock'}

    def test_all_31_sources_contribute_and_shared_names_are_deduplicated(self):
        result = self.build()
        self.assertEqual(result['source_count'],31)
        self.assertEqual(result['domains'],32)
        self.assertTrue(result['all_configured_sources_succeeded'])
        self.assertTrue(all(s['domains']==2 for s in result['sources']))
        self.assertTrue(b.verify_output(self.output,self.cfg)['verified'])
        actual,_ = b.parse_hosts((self.output/'merged_hosts.txt').read_text(),1000)
        self.assertTrue(all(f'source{i}.vendor.net' in actual for i in range(31)))
        audit = json.loads((self.output/'coverage-audit.json').read_text())
        self.assertTrue(audit['source_overlap_available'])
        self.assertEqual(audit['final_domains'],32)
        self.assertEqual(audit['source_membership_histogram'],{'1':31,'31':1})
        self.assertTrue(all(s['exclusive_final_names']==1 for s in audit['sources']))

    def test_missing_last_required_source_preserves_the_entire_publication(self):
        self.build()
        before = self.snapshot()
        last = self.cfg['sources'][-1]
        (self.inputs/(last['id']+'.txt')).unlink()
        with self.assertRaises(OSError):
            self.build()
        self.assertEqual(before,self.snapshot())

    def test_source_cannot_be_removed_without_manifest_failure(self):
        self.cfg['sources'].pop()
        self.save_config()
        with self.assertRaises(b.BuildError):
            b.config_at(self.config)

    def test_an_exception_in_one_feed_does_not_unblock_another_feeds_name(self):
        source = self.cfg['sources'][0]
        path = self.inputs/(source['id']+'.txt')
        path.write_text(path.read_text()+'@@||shared.vendor.net^\n')
        result = self.build()
        self.assertEqual(result['domains'],32)
        self.assertEqual(result['sources'][0]['domains'],1)
        self.assertIn('0.0.0.0 shared.vendor.net\n',(self.output/'merged_hosts.txt').read_text())

    def test_per_source_regression_is_caught_even_if_union_count_barely_changes(self):
        self.build()
        before = self.snapshot()
        # A 50% loss from one source barely changes the 32-name union.
        source = self.cfg['sources'][0]
        (self.inputs/(source['id']+'.txt')).write_text('||shared.vendor.net^\n')
        with self.assertRaises(b.BuildError):
            self.build()
        self.assertEqual(before,self.snapshot())

    def test_hosts_aliases_are_all_retained(self):
        source = {'id':'test','format':'hosts','max_domains':100}
        names,roots,stats = b.parse_feed('0.0.0.0 one.vendor.net two.vendor.net # comment\n',source)
        self.assertEqual(names,{'one.vendor.net','two.vendor.net'})
        self.assertFalse(roots)
        self.assertEqual(stats['hosts_names'],2)

    def test_browser_rules_are_not_promoted_to_whole_domain_blocks(self):
        source = {'id':'test','format':'abp','max_domains':100}
        text = ('||ads.vendor.net^\n||cdn.vendor.net/file.js\n||conditional.vendor.net^$third-party\n'
                'news.vendor.net##.ad\n/regex.vendor.net/\n@@||safe.vendor.net^$domain=news.vendor.net\n')
        names,roots,stats = b.parse_feed(text,source)
        self.assertEqual(names,{'ads.vendor.net'})
        self.assertEqual(roots,names)
        self.assertEqual(sum(stats['skipped'].values()),5)

    def test_source_exceptions_and_badfilter_are_respected(self):
        source = {'id':'test','format':'abp','max_domains':100}
        text = ('||blocked.vendor.net^\n||child.blocked.vendor.net^\n@@||blocked.vendor.net^\n'
                '||disabled.vendor.net^\n||disabled.vendor.net^$badfilter\n'
                '||important.vendor.net^$important\n@@||important.vendor.net^\n')
        names,_,stats = b.parse_feed(text,source)
        self.assertEqual(names,{'important.vendor.net'})
        self.assertEqual(stats['badfilter_rules'],1)

    def test_browser_platform_conditionals_are_not_flattened(self):
        source = {'id':'test','format':'abp','max_domains':100}
        names,_,stats = b.parse_feed('!#if adguard_app_android\n||conditional.vendor.net^\n!#endif\n||ads.vendor.net^\n',source)
        self.assertEqual(names,{'ads.vendor.net'})
        self.assertEqual(stats['skipped']['conditional_block'],1)
        with self.assertRaises(b.BuildError):
            b.parse_feed('!#if unknown\n||bad.vendor.net^\n',source)

    def test_hagezi_declared_count_detects_truncated_feed(self):
        source = {'id':'test','require_entry_count':True}
        with self.assertRaises(b.BuildError):
            b.source_metadata('! Number of entries: 100\n',source,99)

    def test_freshness_checks_work_for_abp_and_hosts_headers(self):
        source = {'id':'test','max_age_hours':72}
        for prefix in ('!','#'):
            stamp = datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')
            self.assertIn('upstream_modified_utc',b.source_metadata(prefix+' Last modified: '+stamp+'\n',source,2))
        for delta in (timedelta(days=-4),timedelta(days=1)):
            stamp = (datetime.now(timezone.utc)+delta).strftime('%d %b %Y %H:%M UTC')
            with self.assertRaises(b.BuildError):
                b.source_metadata('! Last modified: '+stamp+'\n',source,2)

    def test_router_budget_corruption_is_detected(self):
        self.build()
        path = self.output/'stats.json'
        report = json.loads(path.read_text())
        report['router']['cache_mib']+=16
        path.write_text(json.dumps(report))
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output,self.cfg)

    def test_missing_current_version_audit_manifest_is_detected(self):
        self.build()
        path = self.output/'stats.json'
        report = json.loads(path.read_text())
        report.pop('coverage_audit')
        path.write_text(json.dumps(report))
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output,self.cfg)

    def test_compressed_payload_must_match_the_full_hosts_file(self):
        self.build()
        bad = gzip.compress(b'0.0.0.0 wrong.vendor.net\n',mtime=0)
        (self.output/'merged_hosts.txt.gz').write_bytes(bad)
        path = self.output/'stats.json'
        report = json.loads(path.read_text())
        report.update(gzip_bytes=len(bad),gzip_sha256=hashlib.sha256(bad).hexdigest())
        path.write_text(json.dumps(report))
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output,self.cfg)

    def test_oversized_router_list_is_kept_in_full_and_installer_refuses(self):
        source = copy.deepcopy(self.cfg['sources'][2])
        source.update(id='test',format='hosts',max_domains=100000,min_domains=1)
        self.cfg.pop('original_sources_sha256')
        self.cfg.update(sources=[source],max_domains=100000)
        self.cfg['router'].update(max_cache_mib=32,bytes_per_name_budget=256)
        self.save_config()
        (self.inputs/'test.txt').write_text(''.join(f'0.0.0.0 n{i}.vendor.net\n' for i in range(70000)))
        result = self.build()
        self.assertEqual(result['domains'],70000)
        self.assertFalse(result['router']['eligible'])
        self.assertTrue(b.verify_output(self.output,self.cfg)['verified'])
        script = (self.output/'router-ready/install-rb5009-local.rsc').read_text()
        self.assertIn(':local eligible false',script)
        self.assertIn('DEPLOYMENT BLOCKED',(self.output/'router-ready/INSTALL.txt').read_text())
        self.assertEqual((self.output/'merged_hosts.txt').read_text().count('0.0.0.0 '),70000)

    def prepare_reuse_fixture(self):
        self.cfg['router']['max_cache_mib'] = 256
        self.save_config()
        self.block.write_text('custom.vendor.net\n')
        report = self.build()
        report['builder_version'] = '3.0.0'
        report.pop('coverage_audit')
        for name in b.AUDIT_FILES:
            (self.output/name).unlink()
        (self.output/'stats.json').write_text(json.dumps(report))
        for rel,data in b.router_files((self.output/'merged_hosts.txt').read_bytes(),report['domains'],self.cfg,builder_version='3.0.0').items():
            (self.output/rel).write_bytes(data)
        (self.output/'sources.json').write_text(json.dumps(self.cfg))
        (self.output/'allowlist.txt').write_bytes(self.allow.read_bytes())
        (self.output/'blocklist.txt').write_bytes(self.block.read_bytes())
        self.cfg['router']['max_cache_mib'] = 384
        self.save_config()
        return argparse.Namespace(reuse_build=self.output,output=self.root/'update',config=self.config)

    def test_reported_3210777_names_get_336_mib_with_592_mib_free_requirement(self):
        plan = b.router_plan(3210777,100*b.MIB,self.cfg)
        self.assertTrue(plan['eligible'])
        self.assertEqual((plan['cache_mib'],plan['required_free_mib']),(336,592))
        old = copy.deepcopy(self.cfg)
        old['router']['max_cache_mib'] = 256
        self.assertFalse(b.router_plan(3210777,100*b.MIB,old)['eligible'])

    def test_larger_profile_retains_hard_cache_ceiling_and_memory_floor(self):
        for key,value in (('max_cache_mib',385),('min_free_mib',255)):
            cfg = copy.deepcopy(self.cfg)
            cfg['router'][key] = value
            self.config.write_text(json.dumps(cfg))
            with self.assertRaises(b.BuildError):
                b.config_at(self.config)

    def test_reuse_old_build_preserves_names_rules_source_evidence_and_original(self):
        args = self.prepare_reuse_fixture()
        before = self.snapshot()
        old_report = json.loads((self.output/'stats.json').read_text())
        with mock.patch.object(b,'download',side_effect=AssertionError('Reuse must never download')):
            result = b.reuse_build(args)
        self.assertEqual(before,self.snapshot())
        self.assertEqual(result['generated_utc'],old_report['generated_utc'])
        self.assertEqual(result['sources'],old_report['sources'])
        self.assertEqual(result['reused_from_builder_version'],'3.0.0')
        for name in ('merged_hosts.txt','merged_hosts.txt.gz','source-audit.csv','suffix_domains.txt','allowlist.txt','blocklist.txt'):
            self.assertEqual((args.output/name).read_bytes(),(self.output/name).read_bytes())
        self.assertTrue(b.verify_output(args.output,self.cfg)['verified'])
        audit = json.loads((args.output/'coverage-audit.json').read_text())
        self.assertFalse(audit['source_overlap_available'])
        self.assertEqual(audit['snapshot_generated_utc'],old_report['generated_utc'])

    def test_existing_build_audit_does_not_download_or_change_original(self):
        args = self.prepare_reuse_fixture()
        before = self.snapshot()
        with mock.patch.object(b,'download',side_effect=AssertionError('No download')):
            result = audit_existing.audit_existing(self.output,self.root/'audit-reports')
        self.assertEqual(before,self.snapshot())
        self.assertEqual(result['domains'],33)
        self.assertFalse(result['source_overlap_available'])
        self.assertEqual(result['duplicates'],0)

    def test_full_refresh_upgrades_legacy_audit_even_when_names_and_sources_match(self):
        args = self.prepare_reuse_fixture()
        b.reuse_build(args)
        before = (args.output/'merged_hosts.txt').read_bytes()
        self.args.output = args.output
        self.build()
        self.assertEqual(before,(args.output/'merged_hosts.txt').read_bytes())
        audit = json.loads((args.output/'coverage-audit.json').read_text())
        self.assertTrue(audit['source_overlap_available'])
        self.assertEqual(audit['source_membership_histogram'],{'0':1,'1':31,'31':1})

    def test_reuse_rejects_damaged_source_without_publishing(self):
        args = self.prepare_reuse_fixture()
        (self.output/'merged_hosts.txt.gz').write_bytes(b'corrupt')
        before = self.snapshot()
        with self.assertRaises(b.BuildError):
            b.reuse_build(args)
        self.assertEqual(before,self.snapshot())
        self.assertFalse((args.output/'merged_hosts.txt').exists())

    def test_reuse_refuses_existing_destination_and_source_configuration_drift(self):
        args = self.prepare_reuse_fixture()
        args.output.mkdir()
        target = args.output/'merged_hosts.txt'
        target.write_bytes(b'preserve existing build')
        with self.assertRaises(b.BuildError):
            b.reuse_build(args)
        self.assertEqual(target.read_bytes(),b'preserve existing build')
        args.output = self.root/'another-update'
        self.cfg['protected_exact'].append('extra.vendor.net')
        self.save_config()
        with self.assertRaises(b.BuildError):
            b.reuse_build(args)
        self.assertFalse((args.output/'merged_hosts.txt').exists())

    def test_reuse_publication_failure_restores_user_rules_and_leaves_source_intact(self):
        args = self.prepare_reuse_fixture()
        args.output.mkdir()
        (args.output/'allowlist.txt').write_bytes(b'original.vendor.net\n')
        (args.output/'blocklist.txt').write_bytes(b'other.vendor.net\n')
        before = self.snapshot()
        real_replace = b.os.replace
        failed = False
        def fail_once(src,dst):
            nonlocal failed
            if Path(dst)==args.output/'stats.json' and not failed:
                failed = True
                raise OSError('simulated publication failure')
            return real_replace(src,dst)
        with mock.patch.object(b.os,'replace',side_effect=fail_once):
            with self.assertRaises(OSError):
                b.reuse_build(args)
        self.assertTrue(failed)
        self.assertEqual(before,self.snapshot())
        self.assertEqual((args.output/'allowlist.txt').read_bytes(),b'original.vendor.net\n')
        self.assertEqual((args.output/'blocklist.txt').read_bytes(),b'other.vendor.net\n')
        self.assertFalse((args.output/'merged_hosts.txt').exists())
        self.assertFalse((args.output/'.adlist-transaction').exists())


if __name__=='__main__':
    unittest.main()
