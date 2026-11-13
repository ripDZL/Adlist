# Read-only checks; no DNS cache dump of millions of names.
/system/resource/print
/ip/dns/print
/ip/dns/adlist/print detail
/system/scheduler/print detail where name="adlist-v2-memory-guard"
/log/print where topics~"dns|script"
