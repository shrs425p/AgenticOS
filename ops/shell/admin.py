"""Module for system_admin.py"""
from __future__ import annotations


from kernel.base import tool
class SystemAdminMixin:
    # ---- Windows Event Logs ----
    @tool(name="eventlogquery", desc="Query system event logs (Windows Event Log or Linux journalctl). Args: log_name(optional), query(optional), n(optional)", category="Terminal")
    def eventlogquery(
        self, log_name: str = "System", query: str = "", n: str = "50"
    ) -> str:
        """Query system event logs (Windows Event Log or Linux journalctl).

        Args:
            log_name: Windows Event Log name (e.g. System, Application, Security) (ignored on Linux)
            query: optional substring filter on message/provider/id
            n: max events to return
        """
        try:
            limit = int(n)
        except Exception:
            limit = 50
        limit = max(1, min(limit, 500))

        q = (query or "").strip().replace('"', "'")

        if self.system != "Windows":
            # Unix/Linux journalctl implementation
            cmd = f"journalctl -n {limit} --no-pager"
            if q:
                cmd += f" | grep -i {self._quote_arg(q)}"
            return self._run(cmd, timeout=self._get_timeout("system_admin", 30))

        # Windows Event Log implementation
        ln = (log_name or "System").strip().replace('"', "")
        if q:
            ps = (
                f'$ev=Get-WinEvent -LogName "{ln}" -MaxEvents {limit} | '
                f"Where-Object {{ $_.Message -like '*{q}*' -or $_.ProviderName -like '*{q}*' -or $_.Id -eq '{q}' }} | "
                "Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message; "
                "$ev | Format-List | Out-String -Width 300"
            )
        else:
            ps = (
                f'Get-WinEvent -LogName "{ln}" -MaxEvents {limit} | '
                "Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | "
                "Format-List | Out-String -Width 300"
            )
        return self.runpowershell(ps, timeout=self._get_timeout("system_admin", 60))

    # ---- Installed Apps (Windows) ----
    @tool(name="installedapps", desc="List installed apps (Windows). Args: filter_str(optional)", category="Terminal")
    def installedapps(self, filter_str: str = "") -> str:
        """installedapps function."""
        if self.system != "Windows":
            return "Error: installedapps is Windows-only."
        flt = (filter_str or "").strip().replace('"', "'")
        reg1 = self.cfg.get("windows_paths", {}).get("uninstall_registry", "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*")
        reg2 = self.cfg.get("windows_paths", {}).get("wow6432_uninstall_registry", "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*")
        ps = (
            f"Get-ItemProperty {reg1} , {reg2} "
            "| Select-Object DisplayName,DisplayVersion,Publisher,InstallDate "
            "| Where-Object { $_.DisplayName } "
            "| Sort-Object DisplayName "
        )
        if flt:
            ps += f"| Where-Object {{ $_.DisplayName -like '*{flt}*' -or $_.Publisher -like '*{flt}*' }} "
        ps += "| Format-Table -AutoSize | Out-String -Width 240"
        return self.runpowershell(ps, timeout=self._get_timeout("system_admin", 60))

    # ---- Services (guarded) ----
    @tool(name="servicelist", desc="List services. Args: filter_str(optional)", category="Terminal")
    def servicelist(self, filter_str: str = "") -> str:
        """servicelist function."""
        if self.system != "Windows":
            return self._run(
                "systemctl list-units --type=service --no-pager", timeout=self._get_timeout("service_control", 30)
            )
        flt = (filter_str or "").strip().replace('"', "'")
        ps = "Get-Service | Sort-Object Status,Name"
        if flt:
            ps += f" | Where-Object {{ $_.Name -like '*{flt}*' -or $_.DisplayName -like '*{flt}*' }}"
        ps += " | Select-Object Status,Name,DisplayName | Format-Table -AutoSize | Out-String -Width 240"
        return self.runpowershell(ps, timeout=self._get_timeout("service_control", 60))

    @tool(name="servicestatus", desc="Service status. Args: name", category="Terminal")
    def servicestatus(self, name: str) -> str:
        """servicestatus function."""
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(
                f"systemctl status {self._quote_arg(svc)} --no-pager", timeout=self._get_timeout("service_control", 30)
            )
        ps = (
            f'$s=Get-Service -Name "{svc}" -ErrorAction Stop; '
            "$s | Select-Object Status,Name,DisplayName,StartType | Format-List | Out-String -Width 240"
        )
        return self.runpowershell(ps, timeout=self._get_timeout("service_control", 30))

    @tool(name="servicestart", desc="Start service (guarded). Args: name", category="Terminal")
    def servicestart(self, name: str) -> str:
        """servicestart function."""
        if not self.rules.get("allow_service_control", False):
            return "Error: service control is disabled by rules (rules.allow_service_control=false)."
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(f"systemctl start {self._quote_arg(svc)}", timeout=self._get_timeout("service_control", 30))
        return self.runpowershell(
            f"Start-Service -Name \"{svc}\" -ErrorAction Stop; 'OK'", timeout=self._get_timeout("service_control", 30)
        )

    @tool(name="servicestop", desc="Stop service (guarded). Args: name", category="Terminal")
    def servicestop(self, name: str) -> str:
        """servicestop function."""
        if not self.rules.get("allow_service_control", False):
            return "Error: service control is disabled by rules (rules.allow_service_control=false)."
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(f"systemctl stop {self._quote_arg(svc)}", timeout=self._get_timeout("service_control", 30))
        return self.runpowershell(
            f"Stop-Service -Name \"{svc}\" -ErrorAction Stop; 'OK'", timeout=self._get_timeout("service_control", 30)
        )

    # ---- Scheduled Tasks (guarded for create) ----
    @tool(name="scheduledtaskslist", desc="List scheduled tasks (Windows). Args: filter_str(optional)", category="Terminal")
    def scheduledtaskslist(self, filter_str: str = "") -> str:
        """scheduledtaskslist function."""
        if self.system != "Windows":
            return "Error: scheduledtaskslist is Windows-only."
        flt = (filter_str or "").strip()
        ps = "Get-ScheduledTask | Select-Object TaskName,TaskPath,State"
        if flt:
            flt = flt.replace('"', "'")
            ps += f" | Where-Object {{ $_.TaskName -like '*{flt}*' -or $_.TaskPath -like '*{flt}*' }}"
        ps += " | Sort-Object TaskPath,TaskName | Format-Table -AutoSize | Out-String -Width 240"
        return self.runpowershell(ps, timeout=self._get_timeout("system_admin", 60))

    @tool(name="scheduledtaskrun", desc="Run scheduled task (Windows). Args: task_name", category="Terminal")
    def scheduledtaskrun(self, task_name: str) -> str:
        """scheduledtaskrun function."""
        if self.system != "Windows":
            return "Error: scheduledtaskrun is Windows-only."
        name = (task_name or "").strip().replace('"', "")
        if not name:
            return "Error: task_name required."
        return self.runpowershell(
            f"Start-ScheduledTask -TaskName \"{name}\" -ErrorAction Stop; 'OK'",
            timeout=self._get_timeout("system_admin", 30),
        )

    @tool(name="scheduledtaskcreatedaily", desc="Create a daily scheduled task (Windows only). Args: task_name, command, time_hhmm(optional)", category="Terminal")
    def scheduledtaskcreatedaily(
        self, task_name: str, command: str, time_hhmm: str = "09:00"
    ) -> str:
        """scheduledtaskcreatedaily function."""
        if not self.rules.get("allow_system_changes", False):
            return "Error: task creation is disabled by rules (rules.allow_system_changes=false)."
        if self.system != "Windows":
            return "Error: scheduledtaskcreatedaily is Windows-only."
        name = (task_name or "").strip().replace('"', "")
        cmd = (command or "").strip()
        t = (time_hhmm or "09:00").strip()
        if not name or not cmd:
            return "Error: task_name and command required."
        # Create a basic daily task using schtasks (simpler + predictable).
        return self.runcommand(
            f'schtasks /Create /F /SC DAILY /TN "{name}" /TR "{cmd}" /ST {t}',
            timeout=self._get_timeout("system_admin", 30),
        )

    @tool(name="firewallruleslist", desc="List firewall rules for security compliance audits. Args: filter_str(optional)", category="Terminal")
    def firewallruleslist(self, filter_str: str = "") -> str:
        """List active firewall rules.

        Args:
            filter_str: optional substring filter on rule name/display name
        """
        flt = (filter_str or "").strip()
        if self.system == "Windows":
            ps = "Get-NetFirewallRule | Select-Object Name,DisplayName,Enabled,Profile,Action,Direction"
            if flt:
                flt = flt.replace('"', "'")
                ps += f" | Where-Object {{ $_.DisplayName -like '*{flt}*' -or $_.Name -like '*{flt}*' }}"
            ps += " | Sort-Object Enabled -Descending | Format-Table -AutoSize | Out-String -Width 240"
            return self.runpowershell(ps, timeout=self._get_timeout("system_admin", 60))
        else:
            # Linux/macOS
            if flt:
                return self._run(f"iptables -L -n | grep -i {self._quote_arg(flt)}", timeout=self._get_timeout("system_admin", 30))
            return self._run("iptables -L -n", timeout=self._get_timeout("system_admin", 30))

    @tool(name="activeportslist", desc="Audit all active network ports and TCP/UDP socket connections. Args: none", category="Terminal")
    def activeportslist(self) -> str:
        """Audit all active network ports and TCP/UDP socket connections."""
        if self.system == "Windows":
            ps = "Get-NetTCPConnection | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess | Format-Table -AutoSize | Out-String -Width 240"
            return self.runpowershell(ps, timeout=self._get_timeout("system_admin", 60))
        else:
            return self._run("ss -tulpn || netstat -tulan", timeout=self._get_timeout("system_admin", 30))
