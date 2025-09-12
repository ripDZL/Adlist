Blocklists for Technitium DNS

I put this together to make my home network a little cleaner by blocking ads, trackers, and all that annoying telemetry stuff using Technitium DNS Server. This repo contains a merged blocklist (either merged_hosts.txt or split into parts like merged_hosts_part1.txt, merged_hosts_part2.txt, etc.) that’s ready to plug into Technitium for a smoother, ad-free internet experience.What’s This About?The goal here is simple: keep ads, trackers, and telemetry from cluttering up my network. The blocklist files combine a bunch of popular sources into one (or a few) tidy hosts files, covering everything from general ad networks to social media widgets and device-specific tracking (think Samsung TVs, Xiaomi phones, or Apple services). It’s designed to work seamlessly with Technitium DNS, reducing the number of URLs your server needs to fetch while still blocking a ton of unwanted stuff.Whether you’re tired of pop-up ads, creepy trackers, or devices phoning home, these files aim to give you a cleaner, more private internet. I update them daily to keep things fresh, so your DNS server stays on top of the latest ad and tracker domains.What’s Covered?The blocklist pulls from 31 different sources (I won’t bore you with the full list), but here’s the gist:Ads: Blocks banner ads, pop-ups, and other annoying stuff on websites.
Trackers: Stops analytics scripts and trackers that follow you around the web.
Social Media: Cuts out social media widgets that track your activity.
Device-Specific Telemetry: Targets tracking from devices like Xiaomi, Samsung, Apple, Amazon, Roku, LG TVs, and more.
Platform-Specific: Includes filters to reduce ads on platforms like YouTube.

The result is a comprehensive hosts file (or files) that Technitium can use to block millions of domains, keeping your network lean and private.How to Use1. Add to Technitium DNSGetting this set up in Technitium is super easy:Open the Technitium DNS web interface.
Head to Settings > Blocklist.
Turn on the blocklist feature.
Add the raw URL(s) from this repository:If it’s one file: https://raw.githubusercontent.com/your-username/blocklists/main/merged_hosts.txt
If split: https://raw.githubusercontent.com/your-username/blocklists/main/merged_hosts_part1.txt, merged_hosts_part2.txt, etc.

Split into two files for now will update two one single file later. 9-12-25
