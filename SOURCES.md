# Original sources

All 31 original URLs are required. No HaGeZi Light replacement is used.

| # | Source ID | Parser | Original URL |
|---:|---|---|---|
| 1 | oisd-big | abp | https://big.oisd.nl/ |
| 2 | frogeye-firstparty | hosts | https://hostfiles.frogeye.fr/firstparty-trackers-hosts.txt |
| 3 | windows-spyblocker | hosts | https://raw.githubusercontent.com/crazy-max/WindowsSpyBlocker/master/data/hosts/spy.txt |
| 4 | perflyst-android | hosts | https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/android-tracking.txt |
| 5 | stevenblack | hosts | https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts |
| 6 | developerdan | hosts | https://www.github.developerdan.com/hosts/lists/ads-and-tracking-extended.txt |
| 7 | goodbyeads | hosts | https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Hosts/GoodbyeAds.txt |
| 8 | easyprivacy | abp | https://easylist.to/easylist/easyprivacy.txt |
| 9 | hagezi-tif | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/tif.txt |
| 10 | hagezi-pro | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt |
| 11 | adguard-social | abp | https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_4_Social/filter.txt |
| 12 | adguard-base | abp | https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_2_Base/filter.txt |
| 13 | adguard-spyware | abp | https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_3_Spyware/filter.txt |
| 14 | blocklistproject-tracking | hosts | https://blocklistproject.github.io/Lists/tracking.txt |
| 15 | hagezi-xiaomi | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.xiaomi.txt |
| 16 | hagezi-oppo-realme | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.oppo-realme.txt |
| 17 | hagezi-vivo | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.vivo.txt |
| 18 | hagezi-roku | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.roku.txt |
| 19 | hagezi-lgwebos | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.lgwebos.txt |
| 20 | hagezi-tiktok-extended | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.tiktok.extended.txt |
| 21 | hagezi-tiktok | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.tiktok.txt |
| 22 | hagezi-samsung | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.samsung.txt |
| 23 | hagezi-winoffice | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.winoffice.txt |
| 24 | hagezi-huawei | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.huawei.txt |
| 25 | hagezi-apple | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.apple.txt |
| 26 | hagezi-amazon | abp | https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.amazon.txt |
| 27 | perflyst-smarttv | hosts | https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/SmartTV.txt |
| 28 | perflyst-firetv | hosts | https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/AmazonFireTV.txt |
| 29 | goodbyeads-youtube | abp | https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Formats/GoodbyeAds-YouTube-AdBlock-Filter.txt |
| 30 | goodbyeads-samsung | hosts | https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Extension/GoodbyeAds-Samsung-AdBlock.txt |
| 31 | goodbyeads-xiaomi | hosts | https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Extension/GoodbyeAds-Xiaomi-Extension.txt |

The OISD entry also has an explicit same-publisher GitHub mirror for retrieval failure. No source is optional.

HaGeZi feeds require matching declared counts. TIF/Pro also enforce the configured maximum age. Small native feeds are permitted to retain older content dates when unchanged. The older Developer Dan source remains included because the user requested the original coverage; its publisher page identifies its older update date.

The generator is GPL-3.0-or-later. Source data retain their upstream terms and authorship. Each successful build records source URLs, hashes, upstream attribution headers when present, counts and parser results. The supplied code-only package does not redistribute the downloaded feed snapshots.

ABP rules include suffix semantics that cannot be made equivalent by an exact-name hosts file. Browser-specific and conditional rules are audited separately. A source being configured does not establish a completed live build; inspect all 31 successful rows in stats.json/source-audit.csv after building.
