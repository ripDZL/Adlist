# Changes

## 3.0.2 - October 18, 2026

- Rechecks exact-name deduplication and retains all 31 original sources.
- Adds order-independent exclusive-source counts, pairwise overlaps and per-domain review candidates to every new complete build.
- Adds Audit-Existing-Build.cmd for a verified offline review of an older completed snapshot; missing source provenance remains explicitly unavailable.
- Flags video-delivery and shared-service names for investigation; does not automatically delete them or prune explicit children.
- Includes audit integrity checks, original-snapshot compatibility and source/copy preservation tests.
- DOMAIN-REVIEW.md distinguishes checked real samples, an older complete file and the still-unavailable newly reported snapshot.


## 3.0.1 - October 18, 2026

- Addresses the 256 MiB policy refusal reported after a complete 31-source build of 3,210,777 names.
- Sets a hard 384 MiB ceiling while retaining the 100-byte/name allowance, 16 MiB resolver budget and 256 MiB free-RAM reserve. That count plans 336 MiB and requires at least 592 MiB free RAM before import.
- Adds Prepare-Existing-Build.cmd / --reuse-build: verifies a complete v3.0.0 result and copies it into a separate update folder without downloading feeds or changing names.
- Preserves source evidence, build timestamp and user rules; records deployment preparation separately and retains the original folder.
- Includes compatibility, integrity, resource-boundary and interrupted-copy tests. No router execution or actual memory measurement is claimed.


## 3.0.0 - October 18, 2026

- Restores all 31 original source URLs instead of using HaGeZi Light alone.
- Required-source manifest, explicit hosts/ABP parsing and per-feed minimums.
- Preserves hosts aliases, explicit children, source-local exceptions and disabled rules.
- Reports browser rules and suffix semantics that exact-name DNS cannot express.
- Stops publication on missing, malformed, incomplete or suspicious required sources.
- Keeps the full union even if router deployment is refused; no cap-based truncation.
- Calculates a bounded cache budget and reserves 256 MiB free router RAM.
- Loads one full list at a time, retains the old file and attempts bounded rollback.
- Keeps recoverable PC publication, finite HTTPS retries and downgrade protection.
- Restores a verified gzip companion file and adds a per-source CSV audit.
- Includes 40 automated checks and reviewed Windows/RouterOS scripts.

The package ships the builder, without a prebuilt complete live 31-feed snapshot.

## 2.1.1 - October 16, 2026

The previous 150,865-domain package used HaGeZi Light only. It did not preserve
the original source union. Retain it as an existing working fallback until the
new full build and live router checks succeed.
