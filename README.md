# Adlist 3.0.2: the original 31-source build

This version restores **all 31 original URLs**. It does not substitute HaGeZi Light. Every source is required, and the complete accepted DNS-name union is retained without trimming it to a router cap.

**This package contains the tested builder, not a completed live snapshot.** The editing environment could not download every full feed. Run `Build-Adlist.cmd` on the PC to obtain the real union, source report and matching deployment files. No complete current domain count or measured router memory use is claimed.

## Check duplicates, overlap and domains needing review

The final hosts and router files already contain each accepted exact name once. Removing overlapping feeds does not reduce final router RAM if other feeds still supply those same names. Parent and child names are separate DNS rules and are retained.

Every new complete build now also creates:

| File | Meaning |
|---|---|
| `coverage-audit.json` | True exclusive contributions per feed, shared-name counts, review categories and parent/child counts |
| `source-overlap.csv` | Exact intersections for every pair of configured feeds, after final allow rules |
| `domain-review.csv.gz` | Review candidates with their actual contributing feeds; extract to read the CSV |

The new contribution counts are independent of source order. Existing `new_names_at_merge` values are order-dependent and are not a safe basis for deleting a feed. Zero exclusive names means that one input can be omitted for that snapshot; deleting several individually redundant inputs can still lose names. Recalculate the union after any proposed change.

To audit a completed older build without downloading, extract this update separately, run **Audit-Existing-Build.cmd**, and paste the folder containing the old `stats.json` and `merged_hosts.txt`. The reports go into the new folder's `domain-audit` directory. The old result is verified and retained. It checks all final names, flags video-delivery/service names for review, and reports duplicate verification. Older builds do not contain per-domain source provenance, so their exclusive source counts remain explicitly unavailable. A new complete build is required for exact source-overlap measurements.

`Prepare-Existing-Build.cmd` also creates a legacy audit when copying an older completed result. It does not invent source provenance. Audit reports are tied to the verified hosts checksum. New complete builds retain their reports through verification, copying and publication.

Review flags do not establish that a domain is harmful or safe. No domain, source, parent/child rule or pinned addition is removed by this audit. It performs no bulk DNS queries and does not delete names because they currently fail to resolve. Determining necessity needs source policy and evidence of actual breakage or use. The additional overlap index consumes PC memory only; the router payload is unchanged.

Read **DOMAIN-REVIEW.md** for the actual findings and their limits.

## Reuse your completed 3,210,777-name build

Version 3.0.0 used a 256 MiB cache ceiling, which refused the reported complete build. This update provides a bounded 384 MiB ceiling for a router with at least 1 GiB RAM. The existing calculation plans **336 MiB** for 3,210,777 names and requires **592 MiB free RAM before import**, including the unchanged 256 MiB reserve. Eligibility still depends on upload size and the router's actual resources. This is not a measured memory result.

1. Extract the WHOLE update ZIP into a **separate folder beside your completed build**. Keep the old folder intact.
2. Double-click **Prepare-Existing-Build.cmd** and paste the old folder's path when prompted. Choose the folder containing `sources.json`, `stats.json` and `merged_hosts.txt`.
3. The helper verifies the old hosts, gzip, source audit, counts, hashes and generated installer before copying. It preserves every name, source evidence, the original build timestamp, and your allow/block rules. It regenerates the deployment plan and records a separate preparation timestamp. It downloads nothing and leaves the old build intact.
4. Read the new `router-ready/INSTALL.txt`, then follow the router checks below. The helper refuses an existing destination build or a changed source configuration.

PowerShell alternative:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build-Adlist.ps1 -ReuseBuild "C:\path\to\completed-build"
```

Do not extract over the original folder or manually change its `sources.json`: its verified output is tied to that original configuration. A later normal `Build-Adlist.cmd` run in the new folder refreshes all feeds as usual.

## Build on Windows

Extract the entire package to a new folder and double-click **Build-Adlist.cmd**. Python 3.11+ is required; only the standard library is used. The launcher finds Python instead of assuming a hardcoded Python 3.9 installation or Downloads directory.

PowerShell alternative, from the extracted folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build-Adlist.ps1
```

Progress identifies each required source and its parsed/new domain counts. A failure stops publication. Existing output remains intact. The next normal build recovers an interrupted publication before attempting downloads. Two compact error logs are retained.

Verify a completed build without downloading:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build-Adlist.ps1 -Verify
```

`--dry-run` downloads/parses all sources and reports the result without publishing it. More than 25% change in the union or any individual source stops an update. After investigating a legitimate change, `Build-Adlist.ps1 -AcceptLargeChange` bypasses that change check; it cannot bypass missing sources, source validity or hard limits.

## What is preserved and what DNS can express

The parser accepts sink-address hosts entries, all valid aliases on a hosts line, bare domains in hosts sources, and unconditional ABP rules such as `||ads.vendor.net^`. It deduplicates exact names and preserves explicit parent and child names. Unconditional exceptions and `badfilter` rules are applied within their own source. A local allow rule takes priority over the final union.

Browser selectors, URL paths, regular expressions, request-type options and platform conditionals cannot be translated into equivalent whole-domain DNS blocks. They are counted by reason with examples in `stats.json`; domains are never harvested indiscriminately from those rules. Conditional browser exceptions are not turned into global DNS exceptions.

RouterOS adlists match **exact names**. An ABP suffix rule also covers unknown child names, which an exact-name file cannot enumerate. This build preserves the explicit hostname in each accepted rule and all explicit children supplied by the other sources; it does not claim equivalent wildcard coverage. `suffix_domains.txt` is an audit of these roots, not a standalone lossless replacement for the original ABP feeds. Keep browser filtering for browser rules.

The ten pinned domains in `blocklist.txt` came from the recovered local Safe Domains variant. They are visible, editable additions. The four download/bootstrap names in `sources.json` and any rules in `allowlist.txt` are excluded explicitly and counted.

## Files after a successful complete build

| File | Purpose |
|---|---|
| `merged_hosts.txt` | Full sorted hosts-format DNS-name union |
| `merged_hosts.txt.gz` | Verified gzip copy for storage/transfer; not a router upload |
| `stats.json` | Every source's hash, count, provenance, ignored-rule reasons and deployment estimate |
| `source-audit.csv` | One contribution row for each of the 31 sources |
| `suffix_domains.txt` | Audit of ABP suffix intent; do not upload to RouterOS |
| `merged_hosts.sha256` | Full hosts checksum |
| `expected_names.txt` | Full exact-name count |
| `router-ready` | One generated domain file, count sidecar, matching installer and instructions |

The router file uses **one domain per line**, which RouterOS supports. Removing the redundant `0.0.0.0 ` prefix saves eight bytes per name on transfer/storage without removing names. It does not reduce per-name DNS cache memory. The hosts-format file remains available for other DNS software.

## RB5009 deployment budget

The planner uses a budget of **100 bytes/name plus 16 MiB for normal DNS caching**, rounded up to 16 MiB increments, with a minimum 32 MiB and maximum 384 MiB DNS cache setting. This is a planning allowance above the manual's approximate 75 bytes/name, not a router measurement. It admits at most 3,858,759 names under this policy, subject to upload size and live resource checks. The ceiling is not automatically allocated: the reported count plans 336 MiB. More names are retained in the full PC result, while the generated installer refuses deployment.

Installation requires at least 1 GiB total RAM, free RAM equal to the planned cache plus a **256 MiB reserve**, and 32 MiB free storage after upload. The cache budget does not limit all RouterOS allocations. A one-minute guard removes only managed entries if free RAM falls below 256 MiB or the name cap is exceeded. It cannot prevent every spike between checks.

An existing cache larger than the planned value is retained, with a correspondingly higher free-RAM requirement. An existing cache above 384 MiB is refused for manual inspection. The initial free-RAM check occurs before unloading the old list, so a busy router can refuse even if removing the old list would reclaim memory. Do not bypass that check.

The installer checks uploaded byte size and count against embedded build values. PC verification checks SHA-256; the router does not cryptographically hash the uploaded file. A live RouterOS **7.20+** dry-run and resource checks remain necessary. No hardware execution was performed here.

## Install a completed build

1. Stop the old updater during migration and retain the current files. Use one router account and one import at a time: the installation lease uses user-scoped RouterOS globals.
2. Export and inspect:

   ```routeros
   /ip/dns/export file=adlist-dns-before-v3
   /system/resource/print
   /ip/dns/print
   /ip/dns/adlist/print detail
   ```

3. Read `router-ready/INSTALL.txt`. If deployment is refused, keep using the working list. The full PC file can be used by a DNS server with sufficient resources; no smaller substitute was generated.
4. If eligible, upload the three named deployment files to the router Files root. Do not upload the `.rsc.in` template or the root hosts file instead of the generated domain file.
5. Check, then install only after a successful dry-run:

   ```routeros
   /import file-name=install-rb5009-local.rsc verbose=yes dry-run=yes
   /import file-name=install-rb5009-local.rsc
   /system/resource/print
   /ip/dns/print
   /ip/dns/adlist/print detail
   ```

The installer refuses unrelated adlists or multiple managed entries. Existing managed URL-mode entries require manual migration to a verified local recovery file first. Do not use blanket `remove [find]` commands to migrate.

Updates retain the old local file, unload the old list, import the replacement disabled, verify its complete count, then activate it. **There is a temporary ad-blocking gap**; upstream DNS settings remain. This avoids deliberately loading two full lists at once. Reinstalling the same healthy local version skips reloading it.

If installation fails after removing the old entry, the installer attempts to reload the old local file only while sufficient RAM remains. If that recovery cannot complete, it removes the partial entry, retains the file, logs the problem and leaves this blocking absent. Process termination or power loss is not an atomic router transaction. An expired ten-minute lease lets the guard remove an abandoned candidate; it does not automatically restore a removed list or reboot the router.

Successful local updates retain current and previous project-named data files. Unrelated files are preserved. `router/status.rsc` provides read-only diagnostics without printing millions of cache entries. To remove the managed list, dry-run and import `router/remove-adlist-v2.rsc`; the stable management names also cover the earlier v2 installer. Original cache restoration is conditional on the installed budget still matching and no other adlists remaining.

Firewall, DHCP, interfaces, upstream DNS, DoH and `allow-remote-requests` are not changed. Devices must already use the router's DNS service. Clients using Technitium or their own DoH use that resolver's policy instead. No DNS redirection is installed.

## Daily generation and optional publishing

Optional local generation at 6:15 AM while the Windows user is signed in:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Daily-Task.ps1
```

This only regenerates PC files. It does not upload to the router or GitHub. Remove the task with `Install-Daily-Task.ps1 -Remove`.

After a successful full build, `Publish-To-GitHub.ps1` can create a draft PR through the user's `gh auth login` session. It verifies the package, rejects files at GitHub's size limit, uses a fresh review checkout and never merges main. No repository changes were made in this editing session.

The included GitHub workflow, once merged, runs tests and then downloads every required feed before verifying and committing a complete result. Schedules are best effort. It refuses files above the GitHub hosting limit. Do not enable automatic native router URL refresh for this full list: it bypasses the local installer's preflight, count validation and bounded rollback.

See `SOURCES.md` for the exact 31 URLs and `AUDIT.md` for evidence and test limits.
