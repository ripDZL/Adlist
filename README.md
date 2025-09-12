# Blocklists for Technitium DNS

I put this together to clean up my home network by blocking ads, trackers, and telemetry with [Technitium DNS Server](https://technitium.com/dns/). This repo contains a merged blocklist—either `merged_hosts.txt` or split into parts like `merged_hosts_part1.txt`, `merged_hosts_part2.txt`, etc.—designed to make your internet cleaner and more private.



## This blocklist is built from 31 sources, optimized to remove duplicates and redundancies. It covers:

- Ads: Banner ads, pop-ups, and other annoyances on websites.
- Trackers: Analytics and tracking scripts that follow you online.
- Social Media: Widgets and trackers from social platforms.
- Device-Specific Telemetry: Tracking from devices like Xiaomi, Samsung, Apple, Amazon, Roku, LG TVs, and more.
- Platform-Specific: Filters to reduce ads on platforms like YouTube.

Here’s the full list of sources:

<details>
<summary>Click to expand and see all 31 sources</summary>

- [StevenBlack/hosts](https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts)
- [Hagezi TIF](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/tif.txt)
- [Hagezi Pro](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt)
- [Blocklist Project Tracking](https://blocklistproject.github.io/Lists/tracking.txt)
- [Hagezi Native Xiaomi](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.xiaomi.txt)
- [Hagezi Native Oppo-Realme](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.oppo-realme.txt)
- [Hagezi Native Vivo](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.vivo.txt)
- [Hagezi Native Roku](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.roku.txt)
- [Hagezi Native LG WebOS](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.lgwebos.txt)
- [Hagezi Native TikTok Extended](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.tiktok.extended.txt)
- [Hagezi Native TikTok](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.tiktok.txt)
- [Hagezi Native Samsung](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.samsung.txt)
- [Hagezi Native WinOffice](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.winoffice.txt)
- [Hagezi Native Huawei](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.huawei.txt)
- [Hagezi Native Apple](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.apple.txt)
- [Hagezi Native Amazon](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.amazon.txt)
- [WindowsSpyBlocker Spy](https://raw.githubusercontent.com/crazy-max/WindowsSpyBlocker/master/data/hosts/spy.txt)
- [Frogeye Firstparty Trackers](https://hostfiles.frogeye.fr/firstparty-trackers-hosts.txt)
- [Perflyst Android Tracking](https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/android-tracking.txt)
- [Perflyst SmartTV](https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/SmartTV.txt)
- [Perflyst AmazonFireTV](https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/AmazonFireTV.txt)
- [Developerdan Ads and Tracking Extended](https://www.github.developerdan.com/hosts/lists/ads-and-tracking-extended.txt)
- [GoodbyeAds YouTube AdBlock Filter](https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Formats/GoodbyeAds-YouTube-AdBlock-Filter.txt)
- [GoodbyeAds Samsung AdBlock](https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Extension/GoodbyeAds-Samsung-AdBlock.txt)
- [GoodbyeAds Xiaomi Extension](https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Extension/GoodbyeAds-Xiaomi-Extension.txt)
- [GoodbyeAds Hosts](https://raw.githubusercontent.com/jerryn70/GoodbyeAds/master/Hosts/GoodbyeAds.txt)
- [AdGuard Base Filter](https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_2_Base/filter.txt)
- [AdGuard Spyware Filter](https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_3_Spyware/filter.txt)
- [AdGuard Social Filter](https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/filters/filter_4_Social/filter.txt)
- [EasyPrivacy](https://easylist.to/easylist/easyprivacy.txt)
- [OISD Big](https://big.oisd.nl/)

</details>

## Why This Blocklist?

I created this because fetching 31 separate blocklists was bogging down my Technitium server with too many requests. By merging them into one or a few files and cutting out duplicates and overlaps, I got a blocklist that’s just as effective but way easier on the server. It’s formatted for Technitium’s hosts-based blocking, updated daily, and keeps your network fast and private.


## Contributing
This is my personal setup, but I’m open to suggestions. Got ideas for better blocklists or ways to reduce false positives? Open an issue and reach out.

## Troubleshooting
- **False Positives/Blocked Sites**: Some legit domains might get blocked. Use Technitium’s Allowlist to fix issues.
- **Fetch Errors?**: Test the raw GitHub URLs in a browser to ensure they’re accessible.
- **Need Help?**: Open an issue or contact me (I’ll share contact info if we’re working together).

## Split into two files for now will update into one single file later. 9-12-25
