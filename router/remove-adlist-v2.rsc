# Remove only managed entries/tasks; restore saved cache only if still at our budget.
{
    :global adlistV2InstallUntil
    :if ([:typeof $adlistV2InstallUntil] = "time") do={
        :if ([/system/resource/get uptime] < $adlistV2InstallUntil) do={ :error "Wait for active installation or its ten-minute lease to expire" }
    }
    /system/scheduler/remove [/system/scheduler/find where name="adlist-v2-memory-guard" and comment="ripDZL-adlist-v2"]
    /system/script/remove [/system/script/find where name="adlist-v2-memory-guard" and comment="ripDZL-adlist-v2"]
    /ip/dns/adlist/remove [/ip/dns/adlist/find where comment="ripDZL-adlist-v2"]
    /ip/dns/adlist/remove [/ip/dns/adlist/find where comment="ripDZL-adlist-v2-candidate"]
    :local stateId [/system/script/find where name="adlist-v2-runtime-state" and comment="ripDZL-adlist-v2"]
    :local restoreId [/system/script/find where name="adlist-v2-restore-cache" and comment="ripDZL-adlist-v2"]
    :local installedBudget 0
    :if ([:len $stateId] = 1) do={
        :local savedSource [/system/script/get $stateId source]
        :if ([:pick $savedSource 0 8] = ":return ") do={ :set installedBudget [:tonum [:pick $savedSource 8 [:len $savedSource]]] }
    }
    :if (([:len $restoreId] = 1) && ([:len [/ip/dns/adlist/find]] = 0) && ($installedBudget = [/ip/dns/get cache-size])) do={
        /system/script/run adlist-v2-restore-cache
        /system/script/remove $restoreId
        :if ([:len $stateId] = 1) do={ /system/script/remove $stateId }
        :put "Managed lists removed; original cache restored. Data files retained."
    } else={
        :put "Managed lists removed. Cache/restore metadata retained for manual review because settings or other lists differ."
    }
}
