#!/usr/bin/env python3
"""Merge all 31 original feeds on the PC; validate before publishing or deployment.

Python 3.11+, standard library only. SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import argparse
import csv
import gzip
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import sys
import time
import urllib.parse
import urllib.request
import zlib

from pipeline_core import (BuildError, HTTPSRedirectHandler, allowed, atomic_write,
    build_lock, decode, domain, parse_hosts, positive_int, publish_files,
    read_bounded, recover_transaction, user_rules)
from coverage_audit import Coverage, AUDIT_FILES, file_metadata, legacy_reports, verify_files as verify_audit_files

ROOT = Path(__file__).resolve().parent
VERSION = '3.0.2'
MIB = 1048576
MAX_OUTPUT = 256 * MIB
ID = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
SINK_IPS = {'0.0.0.0', '127.0.0.1', '::', '::1'}


def checked_https(url):
    if not isinstance(url, str):
        raise BuildError('Source URL must be a string')
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise BuildError('Source URLs must use credential-free HTTPS')
    return url


def config_at(path):
    cfg = json.loads(decode(read_bounded(path, 131072)))
    if not isinstance(cfg, dict) or cfg.get('schema_version') != 2:
        raise BuildError('Expected configuration schema 2')
    positive_int(cfg['max_domains'], 'max_domains', 8000000)
    positive_int(cfg['min_domains'], 'min_domains', cfg['max_domains'])
    positive_int(cfg['max_output_bytes'], 'max_output_bytes', MAX_OUTPUT)
    fraction = cfg['max_change_fraction']
    if type(fraction) not in (int,float) or not 0 < fraction <= 0.5:
        raise BuildError('max_change_fraction must be above 0 and at most 0.5')
    sources = cfg.get('sources')
    if not isinstance(sources,list) or not 1 <= len(sources) <= 64:
        raise BuildError('Expected 1 to 64 required sources')
    seen = set()
    for source in sources:
        if not isinstance(source,dict):
            raise BuildError('Each source must be an object')
        ident = source['id']
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in seen:
            raise BuildError('Invalid or duplicate source id')
        seen.add(ident)
        checked_https(source['url'])
        checked_https(source.get('original_url',source['url']))
        fallbacks = source.get('fallback_urls',[])
        if not isinstance(fallbacks,list) or len(fallbacks)>3:
            raise BuildError('Use at most three explicit same-publisher fallback URLs')
        for url in fallbacks:
            checked_https(url)
        if source.get('format') not in ('hosts','abp','mixed'):
            raise BuildError('Source format must be hosts, abp or mixed')
        positive_int(source['max_domains'], ident+' max_domains', 5000000)
        positive_int(source['min_domains'], ident+' min_domains', source['max_domains'])
        positive_int(source['max_download_bytes'], ident+' max_download_bytes',128*MIB)
        if 'max_age_hours' in source:
            positive_int(source['max_age_hours'], ident+' max_age_hours',168)
        if type(source.get('require_entry_count',False)) is not bool:
            raise BuildError('require_entry_count must be boolean')
        if not isinstance(source.get('license'),str) or not source['license'].strip():
            raise BuildError('Every source needs an upstream attribution')
    expected = cfg.get('original_sources_sha256')
    if expected is not None:
        urls = [s.get('original_url',s['url']) for s in sources]
        actual = hashlib.sha256(('\n'.join(urls)+'\n').encode()).hexdigest()
        if len(urls)!=31 or actual != expected:
            raise BuildError('The configured original 31-source manifest changed; no publication allowed')
    protected = cfg.get('protected_exact',[])
    if not isinstance(protected,list) or any(not isinstance(n,str) or domain(n)!=n for n in protected):
        raise BuildError('Invalid protected_exact domains')
    router = cfg.get('router')
    if not isinstance(router,dict):
        raise BuildError('Missing router limits')
    positive_int(router['max_cache_mib'],'router max_cache_mib',384)
    positive_int(router['bytes_per_name_budget'],'bytes_per_name_budget',256)
    if router['bytes_per_name_budget'] < 100:
        raise BuildError('Use a name budget of at least 100 bytes')
    positive_int(router['resolver_reserve_mib'],'resolver_reserve_mib',64)
    positive_int(router['min_free_mib'],'min_free_mib',512)
    if router['min_free_mib'] < 256:
        raise BuildError('Retain at least 256 MiB free RAM')
    positive_int(router['max_file_bytes'],'router max_file_bytes',128*MIB)
    return cfg


def download(source):
    """Bounded verified HTTPS with finite retries and no downgrade redirects."""
    failures = []
    for url in [source['url'], *source.get('fallback_urls',[])]:
        for attempt in range(3):
            deadline = time.monotonic()+90
            request = urllib.request.Request(url,headers={
                'User-Agent':f'ripDZL-Adlist/{VERSION}',
                'Accept-Encoding':'identity', 'Accept':'text/plain'})
            try:
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                    HTTPSRedirectHandler())
                with opener.open(request,timeout=15) as response:
                    if response.status!=200:
                        raise BuildError(f'HTTP {response.status}')
                    checked_https(response.url)
                    kind = response.headers.get('Content-Type','').lower()
                    if 'html' in kind or 'json' in kind:
                        raise BuildError('Unexpected document content type')
                    if response.headers.get('Content-Encoding','identity').lower() not in ('','identity'):
                        raise BuildError('Unexpected compressed response')
                    length = response.headers.get('Content-Length')
                    expected = int(length) if length is not None else None
                    if expected is not None and not 0 <= expected <= source['max_download_bytes']:
                        raise BuildError('Source exceeds byte limit')
                    chunks = []
                    total = 0
                    while True:
                        if time.monotonic()>deadline:
                            raise BuildError('Download exceeded its 90-second deadline')
                        part = response.read1(65536)
                        if not part:
                            break
                        total += len(part)
                        if total>source['max_download_bytes']:
                            raise BuildError('Source exceeds byte limit')
                        chunks.append(part)
                    if expected is not None and total!=expected:
                        raise BuildError('Incomplete download')
                    source['_resolved_url'] = response.url
                    return b''.join(chunks)
            except (OSError,http.client.HTTPException,ValueError,BuildError) as exc:
                failures.append(str(exc)[:240])
                if attempt<2:
                    time.sleep(2*(attempt+1))
    raise BuildError(f"{source['id']}: all required download attempts failed: {failures[-1]}")


def parse_feed(text, source):
    """Only unconditional DNS-name rules. Never mine domains from page/URL text."""
    exact = set()
    blocks = set()
    disabled = set()
    exceptions = set()
    important_exceptions = set()
    stats = {'data_lines':0,'invalid_lines':0,'duplicate_names':0,
             'hosts_names':0,'network_rules':0,'exception_rules':0,
             'badfilter_rules':0,'skipped':{},'samples':{}}
    conditional_depth = 0
    def skip(reason,line):
        stats['skipped'][reason] = stats['skipped'].get(reason,0)+1
        samples = stats['samples'].setdefault(reason,[])
        if len(samples)<3:
            samples.append(line[:180])
    for raw in io.StringIO(text):
        line = raw.strip().lstrip('\ufeff')
        if not line:
            continue
        if line.startswith('!#if'):
            conditional_depth += 1
            skip('conditional_directive',line)
            continue
        if line.startswith('!#endif'):
            if not conditional_depth:
                raise BuildError(f"{source['id']}: unmatched conditional end")
            conditional_depth -= 1
            skip('conditional_directive',line)
            continue
        if conditional_depth:
            skip('conditional_block',line)
            continue
        if line.startswith(('!','#','[')):
            continue
        stats['data_lines']+=1
        # This grammar deliberately excludes options, paths, regexes and selectors.
        is_exception = line.startswith('@@')
        pattern = line[2:] if is_exception else line
        if source['format'] in ('abp','mixed') and pattern.startswith('||'):
            match = re.fullmatch(r'\|\|([^\^/$*|]+)\^(?:\$([a-z,-]+))?',pattern)
            if match:
                name = domain(match[1].lower().rstrip('.'))
                options = set(match[2].split(',')) if match[2] else set()
                if name is not None and options <= {'important','badfilter'}:
                    key = (name,'important' in options)
                    if 'badfilter' in options:
                        if is_exception:
                            skip('unsupported_exception_badfilter',line)
                        else:
                            disabled.add(key)
                            stats['badfilter_rules']+=1
                    elif is_exception:
                        (important_exceptions if key[1] else exceptions).add(name)
                        stats['exception_rules']+=1
                    else:
                        if key in blocks:
                            stats['duplicate_names']+=1
                        blocks.add(key)
                        stats['network_rules']+=1
                    if len(exact)+len(blocks)>source['max_domains']*2:
                        raise BuildError(f"{source['id']}: source exceeds domain limit")
                    continue
            skip('conditional_or_url_rule',line)
            continue
        if source['format'] in ('hosts','mixed'):
            clean = re.split(r'\s+#',line,maxsplit=1)[0].strip()
            parts = clean.split()
            candidates = parts[1:] if len(parts)>=2 and parts[0] in SINK_IPS else parts if len(parts)==1 else []
            names = [domain(n.lower().rstrip('.')) for n in candidates]
            if candidates and all(n is not None or n.lower().rstrip('.') in ('localhost','localhost.localdomain','local','broadcasthost','ip6-localhost','ip6-loopback','ip6-allnodes','ip6-allrouters') for n in candidates):
                for name in names:
                    if name:
                        if name in exact:
                            stats['duplicate_names']+=1
                        exact.add(name)
                        stats['hosts_names']+=1
                if len(exact)>source['max_domains']:
                    raise BuildError(f"{source['id']}: source exceeds domain limit")
                continue
        if source['format']=='hosts':
            stats['invalid_lines']+=1
            skip('invalid_hosts_line',line)
        elif '#' in line:
            skip('cosmetic_rule',line)
        elif is_exception:
            skip('conditional_or_url_exception',line)
        else:
            skip('unsupported_browser_rule',line)
    if conditional_depth:
        raise BuildError(f"{source['id']}: unterminated conditional block")
    suffix = set()
    for name,important in blocks-disabled:
        if allowed(name,set(),important_exceptions):
            continue
        if not important and allowed(name,set(),exceptions):
            continue
        suffix.add(name)
    names = exact | suffix
    if len(names)>source['max_domains']:
        raise BuildError(f"{source['id']}: source exceeds domain limit")
    stats['domains']=len(names)
    stats['suffix_rule_roots']=len(suffix)
    stats['exceptions_applied']=len({name for name,_ in blocks})-len(suffix)
    if source['format']=='hosts' and stats['invalid_lines']>max(20,stats['data_lines']//100):
        raise BuildError(f"{source['id']}: invalid hosts format; no source silently dropped")
    return names,suffix,stats


def list_bytes(names):
    header = ('# ripDZL Adlist 3 - original 31-source DNS-name union\n'
              '# Explicit names only; ABP suffix intent and skipped browser rules are audited.\n'
              '# Upstream attribution and source hashes: stats.json and SOURCES.md\n')
    return (header+''.join('0.0.0.0 '+n+'\n' for n in sorted(names))).encode('ascii')


def source_metadata(text,source,actual_count):
    header = text[:16384]
    result = {}
    fields = re.findall(r'^[!#]\s*(Title|Version|Last modified|Updated|Released|Expires|License|Homepage):\s*([^\r\n]+)',header,re.M|re.I)
    result['upstream_headers'] = {key.lower():value[:240] for key,value in fields}
    if source.get('require_entry_count'):
        counts = re.findall(r'^[!#]\s*Number of entries:\s*([0-9]+)\s*$',header,re.M)
        if len(counts)!=1 or int(counts[0])!=actual_count:
            raise BuildError(f"{source['id']}: declared entry count is missing or incomplete")
        result['declared_domains']=actual_count
    if 'max_age_hours' in source:
        stamps = re.findall(r'^[!#]\s*Last modified:\s*([^\r\n]+)',header,re.M)
        if len(stamps)!=1:
            raise BuildError(f"{source['id']}: missing upstream timestamp")
        try:
            modified = datetime.strptime(stamps[0],'%d %b %Y %H:%M UTC').replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise BuildError(f"{source['id']}: unsupported upstream timestamp") from exc
        age = (datetime.now(timezone.utc)-modified).total_seconds()/3600
        if age>source['max_age_hours'] or age < -6:
            raise BuildError(f"{source['id']}: stale or future upstream timestamp")
        result['upstream_modified_utc']=modified.isoformat()
    return result


def router_plan(names, plain_bytes, cfg):
    rc = cfg['router']
    estimate = names*rc['bytes_per_name_budget']+rc['resolver_reserve_mib']*MIB
    cache_mib = max(32,((estimate+16*MIB-1)//(16*MIB))*16)
    reasons = []
    if cache_mib>rc['max_cache_mib']:
        reasons.append(f"Estimated cache budget {cache_mib} MiB exceeds {rc['max_cache_mib']} MiB limit")
    if plain_bytes>rc['max_file_bytes']:
        reasons.append('Router domain file exceeds upload-size limit')
    return {'eligible':not reasons,'reasons':reasons,'cache_mib':cache_mib,
            'estimated_name_bytes_at_75':names*75,'budgeted_name_bytes':names*rc['bytes_per_name_budget'],
            'required_free_mib':cache_mib+rc['min_free_mib'],'min_free_mib':rc['min_free_mib'],
            'max_cache_mib':rc['max_cache_mib'],'max_names':max(0,(rc['max_cache_mib']-rc['resolver_reserve_mib'])*MIB//rc['bytes_per_name_budget'])}


def router_files(data,names,cfg,*,builder_version=VERSION):
    parsed,_ = parse_hosts(decode(data),cfg['max_domains'])
    plain = ''.join(n+'\n' for n in sorted(parsed)).encode('ascii')
    ident = hashlib.sha256(plain).hexdigest()[:16]
    host,count = f'adlist-v3-{ident}.txt',f'adlist-v3-{ident}.count.txt'
    plan = router_plan(names,len(plain),cfg)
    template = (ROOT/'router/install-rb5009-local.rsc.in').read_text()
    replacements = {'__BUILDER_VERSION__':builder_version,'__ADLIST_FILE__':host,'__COUNT_FILE__':count,
        '__EXPECTED_NAMES__':names,'__EXPECTED_BYTES__':len(plain),
        '__CACHE_KIB__':min(plan['cache_mib'],plan['max_cache_mib'])*1024,
        '__MAX_CACHE_KIB__':plan['max_cache_mib']*1024,
        '__MIN_FREE_BYTES__':plan['min_free_mib']*MIB,
        '__REQUIRED_FREE_BYTES__':plan['required_free_mib']*MIB,
        '__MAX_NAMES__':plan['max_names'],'__MAX_FILE_BYTES__':cfg['router']['max_file_bytes'],
        '__ELIGIBLE__':'true' if plan['eligible'] else 'false'}
    for key,value in replacements.items():
        template = template.replace(key,str(value))
    instructions = (f'Builder: {builder_version}\nExpected names: {names}\nExpected bytes: {len(plain)}\n'
        f'SHA-256: {hashlib.sha256(plain).hexdigest()}\nRouter eligible by estimate: {plan["eligible"]}\n'
        f'Planned cache: {plan["cache_mib"]} MiB; required free before import: {plan["required_free_mib"]} MiB\n'
        'This estimate is not a RAM measurement. Never force a refused install.\n')
    if plan['eligible']:
        instructions += (f'\nUpload these THREE files into Files root:\n{host}\n{count}\ninstall-rb5009-local.rsc\n'
            '\n/import file-name=install-rb5009-local.rsc verbose=yes dry-run=yes\n'
            '/import file-name=install-rb5009-local.rsc\n')
    else:
        instructions += '\nDEPLOYMENT BLOCKED: '+ '; '.join(plan['reasons'])+'\nThe full PC list was retained without truncation.\n'
    return {f'router-ready/{host}':plain,f'router-ready/{count}':str(names).encode(),
            'router-ready/install-rb5009-local.rsc':template.encode(),
            'router-ready/INSTALL.txt':instructions.encode()}


def audit_csv(sources):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['id','original_url','resolved_url','format','domains','new_names_at_merge','suffix_rule_roots','ignored_lines','source_sha256'])
    for s in sources:
        writer.writerow([s['id'],s['original_url'],s['resolved_url'],s['format'],s['domains'],s['new_names_at_merge'],s['suffix_rule_roots'],sum(s['skipped'].values()),s['sha256']])
    return out.getvalue().encode('utf-8')


def verify_output(output,cfg):
    if (output/'.adlist-transaction').exists():
        state = json.loads(decode(read_bounded(output/'.adlist-transaction/state.json',1048576)))
        if not isinstance(state,dict) or state.get('phase')!='committed':
            raise BuildError('Pending publication recovery; run a normal build')
    data = read_bounded(output/'merged_hosts.txt',cfg['max_output_bytes'])
    names,counts = parse_hosts(decode(data),cfg['max_domains'])
    if counts['invalid_lines'] or counts['duplicate_names'] or not cfg['min_domains']<=len(names)<=cfg['max_domains'] or data!=list_bytes(names):
        raise BuildError('Published hosts syntax/count/canonical form is invalid')
    report = json.loads(decode(read_bounded(output/'stats.json',1048576)))
    sha = hashlib.sha256(data).hexdigest()
    if not isinstance(report,dict) or report.get('sha256')!=sha or report.get('domains')!=len(names) or report.get('bytes')!=len(data):
        raise BuildError('Published statistics do not match hosts')
    sources = report.get('sources',[])
    if [s.get('id') for s in sources] != [s['id'] for s in cfg['sources']]:
        raise BuildError('Published output does not account for every configured source')
    if report.get('source_manifest_sha256') != manifest_hash(cfg):
        raise BuildError('Configuration changed since the last successful build')
    expected_plan = router_plan(len(names),sum(len(n)+1 for n in names),cfg)
    if report.get('router') != expected_plan or report.get('source_count')!=len(sources) or report.get('all_configured_sources_succeeded') is not True:
        raise BuildError('Router budget or source completeness metadata is invalid')
    if read_bounded(output/'merged_hosts.sha256',200)!=(sha+'  merged_hosts.txt\n').encode():
        raise BuildError('Checksum sidecar does not match')
    if read_bounded(output/'expected_names.txt',20)!=str(len(names)).encode():
        raise BuildError('Count sidecar does not match')
    compressed = read_bounded(output/'merged_hosts.txt.gz',MAX_OUTPUT)
    if report.get('gzip_bytes')!=len(compressed) or report.get('gzip_sha256')!=hashlib.sha256(compressed).hexdigest():
        raise BuildError('Compressed hosts metadata does not match')
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as handle:
            if handle.read(len(data)+1)!=data:
                raise BuildError('Compressed hosts content does not match')
    except (OSError,EOFError,zlib.error) as exc:
        raise BuildError('Invalid compressed hosts') from exc
    if read_bounded(output/'source-audit.csv',1048576)!=audit_csv(sources):
        raise BuildError('Source audit does not match statistics')
    suffix_data = read_bounded(output/'suffix_domains.txt',cfg['max_output_bytes'])
    if hashlib.sha256(suffix_data).hexdigest()!=report.get('suffix_sha256'):
        raise BuildError('Suffix-intent audit checksum does not match')
    built_with = report.get('builder_version')
    if built_with not in ('3.0.0','3.0.1',VERSION):
        raise BuildError('Unsupported completed-build version')
    if built_with==VERSION and report.get('coverage_audit') is None:
        raise BuildError('Completed build is missing its coverage audit manifest')
    if report.get('coverage_audit') is not None:
        verify_audit_files(output,report)
    for rel,raw in router_files(data,len(names),cfg,builder_version=built_with).items():
        if read_bounded(output/rel,MAX_OUTPUT)!=raw:
            raise BuildError('Router-ready files do not match verified hosts/template')
    return {'verified':True,'builder_version':VERSION,'sources':len(sources),'domains':len(names),
            'bytes':len(data),'sha256':sha,'router':report['router']}


def manifest_hash(cfg):
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def reuse_build(args):
    """Verify and copy a completed build; change its deployment plan, never its names.

    The original folder is read-only except for its OS lock. Publication in the
    new folder includes the original user rules in the same recovery transaction.
    No network calls, parsing of source feeds, or freshness claims are made.
    """
    source = args.reuse_build.resolve(strict=True)
    output = args.output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise BuildError('Extract the update to a separate folder beside the completed build')
    cfg = config_at(args.config)
    old_cfg = config_at(source/'sources.json')
    if {k:v for k,v in cfg.items() if k!='router'} != {k:v for k,v in old_cfg.items() if k!='router'}:
        raise BuildError('Source/parsing configuration differs; reuse requires the same complete source configuration')
    output.mkdir(parents=True,exist_ok=True)
    with build_lock(source), build_lock(output):
        recover_transaction(output)
        if (output/'merged_hosts.txt').exists() or (output/'stats.json').exists():
            raise BuildError('Destination already contains a build; use a newly extracted update folder')
        verified = verify_output(source,old_cfg)
        report = json.loads(decode(read_bounded(source/'stats.json',1048576)))
        data = read_bounded(source/'merged_hosts.txt',cfg['max_output_bytes'])
        files = router_files(data,verified['domains'],cfg)
        plain_bytes = next(len(raw) for rel,raw in files.items()
                           if re.fullmatch(r'router-ready/adlist-v3-[0-9a-f]{16}\.txt',rel))
        plan = router_plan(verified['domains'],plain_bytes,cfg)
        report.update(builder_version=VERSION,source_manifest_sha256=manifest_hash(cfg),router=plan,
            deployment_prepared_utc=datetime.now(timezone.utc).isoformat(),
            reused_from_builder_version=report['builder_version'],changed=False)
        for name in ('merged_hosts.txt.gz','source-audit.csv','suffix_domains.txt',
                     'merged_hosts.sha256','expected_names.txt'):
            files[name] = read_bounded(source/name,MAX_OUTPUT)
        if report.get('coverage_audit') is not None:
            for name in AUDIT_FILES:
                files[name] = read_bounded(source/name,MAX_OUTPUT)
        else:
            legacy_names,_ = parse_hosts(decode(data),cfg['max_domains'])
            audit_files = legacy_reports(legacy_names,report)
            report['coverage_audit'] = file_metadata(audit_files)
            files.update(audit_files)
        for name,wildcards in (('allowlist.txt',True),('blocklist.txt',False)):
            user_rules(source/name,wildcards)
            files[name] = read_bounded(source/name,1048576)
        files['stats.json'] = (json.dumps(report,indent=2)+'\n').encode()
        files['merged_hosts.txt'] = data
        warning = publish_files(output,files)
        if warning:
            report['cleanup_warning'] = warning
        verify_output(output,cfg)
        return report


def prune_ready(output,keep):
    ready = output/'router-ready'
    for item in ready.iterdir():
        if re.fullmatch(r'adlist-v3-[0-9a-f]{16}(?:\.count)?\.txt',item.name) and 'router-ready/'+item.name not in keep:
            try:
                item.unlink()
            except OSError:
                return 'Current result is valid; old PC router upload files need cleanup'
    return None


def run(args):
    cfg = config_at(args.config)
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    with build_lock(output):
        if args.dry_run and (output/'.adlist-transaction').exists():
            raise BuildError('Run a normal build to recover the pending publication first')
        recover_transaction(output)
        names,suffix = set(),set()
        sources = []
        coverage = Coverage(s['id'] for s in cfg['sources'])
        for index,configured in enumerate(cfg['sources'],1):
            source = dict(configured)
            print(f'[{index}/{len(cfg["sources"])}] {source["id"]}: reading required source',file=sys.stderr,flush=True)
            if args.input_dir is None:
                data = download(source)
            else:
                data = read_bounded(args.input_dir/(source['id']+'.txt'),source['max_download_bytes'])
            text = decode(data)
            if '<html' in text[:2048].lower() or '<!doctype' in text[:2048].lower():
                raise BuildError(f"{source['id']}: HTML error document")
            entries,roots,stats = parse_feed(text,source)
            if len(entries)<source['min_domains']:
                raise BuildError(f"{source['id']}: only {len(entries)} usable DNS names; source is not silently omitted")
            metadata = source_metadata(text,source,len(entries))
            coverage.add(index-1,entries)
            added = len(entries-names)
            sources.append({'id':source['id'],'original_url':source.get('original_url',source['url']),
                'resolved_url':source.get('_resolved_url',source['url']),'format':source['format'],
                'license':source['license'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                'new_names_at_merge':added,**stats,**metadata})
            names.update(entries)
            suffix.update(roots)
            if len(names)>cfg['max_domains']:
                raise BuildError('Full union exceeds PC domain cap; no truncated publication')
            print(f'  {len(entries):,} names; {added:,} new; union {len(names):,}',file=sys.stderr,flush=True)
        custom,_ = user_rules(args.blocklist,False)
        names.update(custom)
        exact,allow_suffix = user_rules(args.allowlist,True)
        exact.update(cfg.get('protected_exact',[]))
        before_allow = len(names)
        names = {n for n in names if not allowed(n,exact,allow_suffix)}
        suffix &= names
        if not cfg['min_domains']<=len(names)<=cfg['max_domains']:
            raise BuildError('Final domain count is outside configured limits')
        data = list_bytes(names)
        suffix_data = ''.join(n+'\n' for n in sorted(suffix)).encode('ascii')
        if len(data)>cfg['max_output_bytes'] or len(suffix_data)>cfg['max_output_bytes']:
            raise BuildError('Full output exceeds PC byte cap; no truncated publication')
        target = output/'merged_hosts.txt'
        previous = read_bounded(target,MAX_OUTPUT) if target.exists() else None
        if previous is not None:
            old_names,old_stats = parse_hosts(decode(previous),cfg['max_domains'])
            if not old_names or old_stats['invalid_lines']:
                raise BuildError('Previous output is invalid; retain it for inspection')
            removed,added = len(old_names-names)/len(old_names),len(names-old_names)/len(old_names)
            if not args.accept_large_change and max(removed,added)>cfg['max_change_fraction']:
                raise BuildError(f'Suspicious union change: {removed:.1%} removed, {added:.1%} added; review before --accept-large-change')
            old_report = output/'stats.json'
            if old_report.exists():
                stored = json.loads(decode(read_bounded(old_report,1048576)))
                old_counts = {s['id']:s['domains'] for s in stored.get('sources',[])}
                for s in sources:
                    before = old_counts.get(s['id'])
                    if before and not args.accept_large_change and abs(s['domains']-before)/before>cfg['max_change_fraction']:
                        raise BuildError(f"{s['id']}: suspicious per-source count change; old publication retained")
        plan = router_plan(len(names),sum(len(n)+1 for n in names),cfg)
        compressed = gzip.compress(data,compresslevel=6,mtime=0)
        report = {'schema_version':2,'builder_version':VERSION,
            'generated_utc':datetime.now(timezone.utc).isoformat(),'source_manifest_sha256':manifest_hash(cfg),
            'source_count':len(sources),'all_configured_sources_succeeded':True,'domains':len(names),'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'suffix_sha256':hashlib.sha256(suffix_data).hexdigest(),
            'gzip_bytes':len(compressed),'gzip_sha256':hashlib.sha256(compressed).hexdigest(),
            'suffix_rule_roots':len(suffix),'allowlist_removed':before_allow-len(names),'custom_domains':len(custom),
            'changed':previous!=data,'router':plan,'sources':sources,
            'semantics':'Exact-name projection. Browser paths, options and cosmetic rules are not DNS rules. ABP suffix roots do not enumerate unknown subdomains.'}
        if args.dry_run:
            return report
        files = router_files(data,len(names),cfg)
        if previous==data:
            try:
                stored = json.loads(decode(read_bounded(output/'stats.json',1048576)))
                verify_output(output,cfg)
                same_sources = [(s['id'],s['sha256']) for s in stored['sources']]==[(s['id'],s['sha256']) for s in sources]
                prior_audit = json.loads(decode(read_bounded(output/'coverage-audit.json',1048576))) if stored.get('coverage_audit') else {}
                if stored.get('builder_version')==VERSION and same_sources and prior_audit.get('source_overlap_available') is True:
                    warning = prune_ready(output,files)
                    if warning:
                        stored['cleanup_warning']=warning
                    stored['changed']=False
                    return stored
            except (OSError,ValueError,KeyError,BuildError):
                pass
        audit_files = coverage.reports(names,custom,sources,snapshot_sha256=report['sha256'],generated_utc=report['generated_utc'])
        report['coverage_audit'] = file_metadata(audit_files)
        files.update(audit_files)
        if previous is not None and previous!=data:
            files['merged_hosts.previous.txt']=previous
        files['stats.json']=(json.dumps(report,indent=2)+'\n').encode()
        files['merged_hosts.txt.gz']=compressed
        files['source-audit.csv']=audit_csv(sources)
        files['suffix_domains.txt']=suffix_data
        files['merged_hosts.sha256']=(report['sha256']+'  merged_hosts.txt\n').encode()
        files['expected_names.txt']=str(len(names)).encode()
        files['merged_hosts.txt']=data
        warning = publish_files(output,files)
        if warning:
            report['cleanup_warning']=warning
        warning = prune_ready(output,files)
        if warning:
            report['cleanup_warning']=warning
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'sources.json')
    parser.add_argument('--output',type=Path,default=ROOT)
    parser.add_argument('--allowlist',type=Path,default=ROOT/'allowlist.txt')
    parser.add_argument('--blocklist',type=Path,default=ROOT/'blocklist.txt')
    parser.add_argument('--input-dir',type=Path,help='Use local ID.txt source snapshots instead of downloading')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--verify',action='store_true')
    mode.add_argument('--reuse-build',type=Path,help='Verify and reuse a complete v3.0.x folder without downloading; extract this update separately')
    parser.add_argument('--accept-large-change',action='store_true')
    args = parser.parse_args()
    try:
        if args.reuse_build:
            result = reuse_build(args)
        elif args.verify:
            with build_lock(args.output):
                result = verify_output(args.output,config_at(args.config))
        else:
            result = run(args)
        summary = {k:v for k,v in result.items() if k!='sources'}
        if isinstance(result.get('sources'),int):
            summary['sources']=result['sources']
        print(json.dumps(summary,indent=2))
        return 0
    except (BuildError,OSError,ValueError,KeyError,TypeError) as exc:
        message = f'{datetime.now(timezone.utc).isoformat()} ERROR: {exc}'
        print(message,file=sys.stderr)
        try:
            args.output.mkdir(parents=True,exist_ok=True)
            log = args.output/'build-error.log'
            if log.exists():
                os.replace(log,args.output/'build-error.previous.log')
            atomic_write(log,(message[:4096]+'\n').encode())
        except OSError:
            pass
        return 1


if __name__=='__main__':
    sys.exit(main())
