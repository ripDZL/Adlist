# Evidence and validation - October 18, 2026

## Scope correction

The user requested preservation of the original 31 feeds after learning that v2.1.1 used only HaGeZi Light. Version 3 restores those exact URLs. `original_sources.json` and the configuration fingerprint make omission of a configured original source an error.

The supplied archive could not be downloaded under this environment's network restrictions. A local Safe Domains variant was recovered from the user's Downloads directory and reviewed. It has the same 31 URLs, plus ten visible pinned domains. Its bytes are not claimed to be identical to the attached archive.

## Findings in the recovered merger

The old implementation chose format using URL substrings. It could feed hosts/bare-domain lists, including WindowsSpyBlocker and Perflyst Android, to an ABP parser and collect no names. Conversely, the OISD ABP endpoint was sent to its hosts parser. Errors were printed and ignored before a new merged file and run timestamp were written. That could publish a shortened list after failed downloads. Its domain check also allowed underscores and other malformed host forms.

The replacement does not guess formats from filenames. It validates the entire required set before a recoverable publication. Individual-source count changes are checked as well as union changes, because failure of a mostly overlapping feed can be hidden in the final count.

## Reported complete build and deployment update

The user reported all 31 sources succeeding and 3,210,777 names in v3.0.0. The 256 MiB cache policy refused that result. The count requires a 336 MiB plan using the existing 100-byte/name allowance and 16 MiB resolver budget. Version 3.0.1 permits up to 384 MiB while retaining the live free-RAM requirement (at least 592 MiB for this count) and 256 MiB reserve. Actual router resources have not been measured.

The new reuse mode verifies the complete old result before copying it into a separate update folder without network calls. It retains the names, source evidence, original build timestamp and user rules. Tests cover v3.0.0 compatibility, source corruption, destination/source-configuration refusal, hard resource boundaries and restoration after an injected publication failure.

## Domain necessity and overlap review

See DOMAIN-REVIEW.md. Twenty real samples contain 101,927 unique names and 651 repeated cross-source memberships. The TikTok pair shares 435 names but has two names only in its normal list and 178 only in its extended list. GoodbyeAds YouTube contains 97,446 googlevideo.com names among 97,645 parsed names; those are review candidates, not automatically declared false positives. A separate historical September 5 file was scanned in full: 3,050,240 accepted unique names, zero exact duplicates and 963 entries rejected by the current hostname policy. These are not measurements of the new 3,210,777-name build.

New complete builds calculate exact exclusive contributions independent of source order and export pairwise overlap and review reports. Offline audits and copies of older builds explicitly mark unavailable source provenance. No automatic domain or source pruning, suffix collapsing or bulk DNS queries are performed.

## Checks performed

- 56 Python tests pass on Windows. These include all 31 configured feeds contributing in a synthetic end-to-end build, missing-last-source preservation, manifest omission, per-source regression, aliases, safe browser-rule handling, exceptions, disabled rules, timestamp/count checks, router-budget refusal without truncation, gzip verification, lock contention, replacement failure and an actual killed child process during publication.
- Twenty real feed samples were parsed and checked: WindowsSpyBlocker, the three Perflyst feeds, AdGuard Social, the twelve HaGeZi native feeds, GoodbyeAds YouTube/Samsung/Xiaomi. The YouTube sample contains 97,645 explicit names. These sample results are not a complete union count.
- The native samples showed that some unchanged feeds retain older modification dates. Their declared counts remain required; they are not rejected solely for an older content date. The volatile TIF/Pro feeds retain the configured age check.
- All three PowerShell scripts pass parser checks. RouterOS scripts receive lexical/manual review only. A generated test installer is checked separately from the template before packaging.

## Current limits

Direct HTTPS downloading in the execution environment fails DNS resolution; the source integration also cannot transfer every large feed. Therefore no completed current 31-source snapshot is included or claimed. The ZIP contains the production configuration and builder. Its first complete build must run on a machine that can reach all required sources. Partial real samples and synthetic test outputs are not shipped as the user's list.

No live RB5009 import, RAM measurement, CPU measurement, DNS query check or router rollback execution was performed. The calculated name budget and free-RAM reserve are estimates and checks, not a guarantee against every RouterOS allocation. The memory guard cannot prevent every spike. Exact-name files cannot enumerate arbitrary children of ABP suffix rules or implement browser content rules.

Full-size replacement temporarily removes this ad blocking. Normal upstream DNS configuration is preserved. Rollback requires an intact previous local file, available RAM and working RouterOS commands; if it cannot complete, the partial list is removed and recovery is logged. Router interruption/power loss is not an atomic transaction. Use one router account and one import at a time because the lease is user-scoped.

No router configuration or repository publication was performed in this editing session. Original source availability remains an external condition: an unavailable required feed causes failure, not silent omission. Archived sources remain because the user requested their original coverage; they are not represented as newly maintained feeds.

## Primary references

- [RouterOS adlist manual](https://manual.mikrotik.com/docs/cli-reference/ip/dns/adlist/): exact matching, supported plain-name format, approximate per-name memory and disabled-list cache behavior.
- [RouterOS scripting](https://help.mikrotik.com/docs/spaces/ROS/pages/47579229/Scripting): scopes, errors and import dry runs.
- [HaGeZi legacy-format explanation](https://github.com/hagezi/dns-blocklists-legacy): explicit-name limitations and unknown child names.
- [Developer Dan's list page](https://www.github.developerdan.com/hosts/): the original source is an older published list, retained deliberately.
