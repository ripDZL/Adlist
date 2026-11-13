# Domain and source review

October 18, 2026, 1:14 AM EDT

The merger already deduplicates normalized exact names. A count of 3,210,777 from a verified build therefore represents unique accepted names, not 31 lists simply appended together. Removing a feed that contributes only shared names changes download/build work, not the final router domain count.

**Scope:** I reviewed the configuration of all 31 sources, parsed all names in 20 available real feed files, and scanned an available historical merged file. The newly reported October 18 build and its source snapshots were not found in the accessible files. These measurements must not be presented as an audit of those actual 3,210,777 names.

## Concrete findings

- The 20 real samples have 101,927 unique names after removing 651 repeated cross-source memberships. These are partial-source figures only.
- The TikTok samples share 435 names. The normal list has two other names; the extended list has 178 other names. Their names alone do not establish redundancy.
- GoodbyeAds Samsung versus HaGeZi Samsung: 29 shared, 72 only in GoodbyeAds and 171 only in HaGeZi. Xiaomi: 77 shared, 201 only in GoodbyeAds and 268 only in HaGeZi. Other feeds may cover those remaining names; that has not been measured for the full union.
- The YouTube sample contains 97,446 googlevideo.com names among 97,645 names; its header says January 21, 2024. It is the first list I would review for playback problems and questionable benefit. OISD explicitly lists this very feed among lists claiming YouTube blocking while explaining the limits of DNS-level YouTube filtering. These are review candidates, not 97,446 proven false positives.
- Developer Dan reports November 17, 2023 as the update date of the configured ads/tracking list. Older unique entries deserve review; age alone does not prove every entry is unnecessary.
- The historical September 5, 2026 file contained 3,051,203 data lines: 3,050,240 accepted unique names, zero exact duplicates and 963 entries rejected by the current hostname policy (830 underscore names, two local/reserved names and 131 other rejected forms, including IP literals). It also contained 97,446 googlevideo.com names. This is a different file from the new build.

## Review of all original inputs

| Source | Parsed names in available sample | Finding / next check |
|---|---:|---|
| `oisd-big` | Not locally available | Curated aggregate; adding other feeds can reintroduce its exclusions. Preserve explicit names and note suffix limits. |
| `frogeye-firstparty` | Not locally available | First-party/CNAME tracking focus. Measure exclusive exact names before omitting. |
| `windows-spyblocker` | 347 | Windows-specific coverage. Compare with Windows/Office native and aggregate lists. |
| `perflyst-android` | 80 | Android coverage. Small does not mean redundant; measure exact contributions. |
| `stevenblack` | Not locally available | Aggregate with likely shared coverage. Never infer full redundancy from its title. |
| `developerdan` | Not locally available | Published update date is November 17, 2023. Review stale unique additions and breakage before retaining long term. |
| `goodbyeads` | Not locally available | Aggregate/programmatic expansion. Publisher presents its Samsung/Xiaomi extensions as standalone alternatives. |
| `easyprivacy` | Not locally available | Browser list: only unconditional hostname rules enter DNS. Paths/options are not whole-domain rules. |
| `hagezi-tif` | Not locally available | Security coverage for malware/phishing/etc. Large size is not evidence of duplicate or unnecessary names. |
| `hagezi-pro` | Not locally available | Curated aggregate with partial native coverage. Native add-ons may be more aggressive. |
| `adguard-social` | 2 | Browser social-widget rules; this sample has only two usable unconditional DNS names. |
| `adguard-base` | Not locally available | Browser list: audit usable exact hostname rules separately from cosmetic and path rules. |
| `adguard-spyware` | Not locally available | Browser tracking list: retain only safe unconditional DNS projections. |
| `blocklistproject-tracking` | Not locally available | Tracking aggregate. Quantify exclusive names and maintenance, not list count. |
| `hagezi-xiaomi` | 345 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-oppo-realme` | 489 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-vivo` | 244 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-roku` | 57 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-lgwebos` | 231 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-tiktok-extended` | 613 | 613-name sample includes 178 names outside the normal list; not a complete strict superset in these snapshots. |
| `hagezi-tiktok` | 437 | 437-name sample shares 435 with extended; two remain outside extended. |
| `hagezi-samsung` | 200 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-winoffice` | 383 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-huawei` | 135 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-apple` | 110 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `hagezi-amazon` | 368 | Native device/service tracking; HaGeZi tiers already contain some coverage. Full native lists may add more aggressive blocking. Measure exclusivity and function before omitting. |
| `perflyst-smarttv` | 497 | Device-specific coverage; compare exact contributions and device functionality. |
| `perflyst-firetv` | 16 | Fire TV coverage; compare with Amazon native and aggregates. |
| `goodbyeads-youtube` | 97,645 | Priority review: 97,446 googlevideo.com names in the 97,645-name sample; header dated January 21, 2024. |
| `goodbyeads-samsung` | 101 | 101-name sample shares only 29 with HaGeZi Samsung. Also compare against main GoodbyeAds. |
| `goodbyeads-xiaomi` | 278 | 278-name sample shares only 77 with HaGeZi Xiaomi. Also compare against main GoodbyeAds. |

## What the update changes

New full builds now produce `coverage-audit.json`, `source-overlap.csv`, and `domain-review.csv.gz`. The source counts show exactly how many final names depend on each feed alone, independent of input order and after allow rules. Pinned custom names count as another input, so deleting a source does not falsely claim savings for names pinned locally. Review rows identify the contributing feeds for each candidate.

The older `new_names_at_merge` column remains for compatibility and is explicitly not an exclusive-source count. Multiple feeds can each have zero exclusive names while jointly providing needed coverage: removing several without recomputing can still lose domains.

`Audit-Existing-Build.cmd` verifies an older completed folder and reviews every final name offline. Missing source provenance stays unavailable. `Prepare-Existing-Build.cmd` performs the same review while reusing an older build. A new full build is needed for exact pairwise/exclusive-source results. Audit-only work changes no deployment or existing domain files. The router memory settings and guards are unchanged.

## Removal policy

No source or accepted domain was removed in this update. Parent and child names remain because RouterOS adlists match exact names. Bulk DNS lookups are not used: temporary nonresolution is not proof that a security-domain entry is unnecessary. Merely not seeing a domain in client traffic is also not proof that a preventative block has no value.

Combining feeds uses their accepted-name union. One publisher removing a false positive does not globally allow it if another publisher still lists it. Local explicit allow rules are the final override. Hostname syntax validation cannot certify that every domain is harmful; service functionality and false positives still need review.

## Primary references checked

- [RouterOS adlist manual](https://manual.mikrotik.com/docs/cli-reference/ip/dns/adlist/): exact-name matching.
- [HaGeZi README](https://github.com/hagezi/dns-blocklists#native-tracker): native lists partly overlap tier lists and can be more aggressive.
- [GoodbyeAds README](https://github.com/jerryn70/GoodbyeAds): Samsung/Xiaomi standalone lists and main-list scope.
- [OISD FAQ](https://oisd.nl/faq): combination/false-positive policy, suffix limits and DNS YouTube limitations.
- [Developer Dan](https://www.github.developerdan.com/hosts/): configured list date and known compatibility issues.

The sample counts and historical-file measurements come from local parsing, not publisher-advertised totals. `Docs/domain-sample-findings.json` records the twenty source hashes and exact pair comparisons.
