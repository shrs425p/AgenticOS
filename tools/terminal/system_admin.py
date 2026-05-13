from __future__ import annotations


class SystemAdminMixin:
    # ---- Windows Event Logs ----
    def eventlog_query(
        self, log_name: str = "System", query: str = "", n: str = "50"
    ) -> str:
        """Query Windows Event Log using PowerShell (best-effort).

        Args:
            log_name: e.g. System, Application, Security
            query: optional substring filter on message/provider/id (best-effort)
            n: max events to return
        """
        if self.system != "Windows":
            return "Error: eventlog_query is Windows-only."
        try:
            limit = int(n)
        except Exception:
            limit = 50
        limit = max(1, min(limit, 500))

        q = (query or "").strip().replace('"', "'")
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
        return self.run_powershell(ps, timeout=60)

    # ---- Installed Apps (Windows) ----
    def installed_apps(self, filter_str: str = "") -> str:
        if self.system != "Windows":
            return "Error: installed_apps is Windows-only."
        flt = (filter_str or "").strip().replace('"', "'")
        ps = (
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* ,"
            "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
            "| Select-Object DisplayName,DisplayVersion,Publisher,InstallDate "
            "| Where-Object { $_.DisplayName } "
            "| Sort-Object DisplayName "
        )
        if flt:
            ps += f"| Where-Object {{ $_.DisplayName -like '*{flt}*' -or $_.Publisher -like '*{flt}*' }} "
        ps += "| Format-Table -AutoSize | Out-String -Width 240"
        return self.run_powershell(ps, timeout=60)

    # ---- Services (guarded) ----
    def service_list(self, filter_str: str = "") -> str:
        if self.system != "Windows":
            return self._run(
                "systemctl list-units --type=service --no-pager", timeout=30
            )
        flt = (filter_str or "").strip().replace('"', "'")
        ps = "Get-Service | Sort-Object Status,Name"
        if flt:
            ps += f" | Where-Object {{ $_.Name -like '*{flt}*' -or $_.DisplayName -like '*{flt}*' }}"
        ps += " | Select-Object Status,Name,DisplayName | Format-Table -AutoSize | Out-String -Width 240"
        return self.run_powershell(ps, timeout=60)

    def service_status(self, name: str) -> str:
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(
                f"systemctl status {self._quote_arg(svc)} --no-pager", timeout=30
            )
        ps = (
            f'$s=Get-Service -Name "{svc}" -ErrorAction Stop; '
            "$s | Select-Object Status,Name,DisplayName,StartType | Format-List | Out-String -Width 240"
        )
        return self.run_powershell(ps, timeout=30)

    def service_start(self, name: str) -> str:
        if not self.rules.get("allow_service_control", False):
            return "Error: service control is disabled by rules (rules.allow_service_control=false)."
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(f"systemctl start {self._quote_arg(svc)}", timeout=30)
        return self.run_powershell(
            f"Start-Service -Name \"{svc}\" -ErrorAction Stop; 'OK'", timeout=30
        )

    def service_stop(self, name: str) -> str:
        if not self.rules.get("allow_service_control", False):
            return "Error: service control is disabled by rules (rules.allow_service_control=false)."
        svc = (name or "").strip()
        if not svc:
            return "Error: name required."
        if self.system != "Windows":
            return self._run(f"systemctl stop {self._quote_arg(svc)}", timeout=30)
        return self.run_powershell(
            f"Stop-Service -Name \"{svc}\" -ErrorAction Stop; 'OK'", timeout=30
        )

    # ---- Scheduled Tasks (guarded for create) ----
    def scheduled_tasks_list(self, filter_str: str = "") -> str:
        if self.system != "Windows":
            return "Error: scheduled_tasks_list is Windows-only."
        flt = (filter_str or "").strip()
        ps = "Get-ScheduledTask | Select-Object TaskName,TaskPath,State"
        if flt:
            flt = flt.replace('"', "'")
            ps += f" | Where-Object {{ $_.TaskName -like '*{flt}*' -or $_.TaskPath -like '*{flt}*' }}"
        ps += " | Sort-Object TaskPath,TaskName | Format-Table -AutoSize | Out-String -Width 240"
        return self.run_powershell(ps, timeout=60)

    def scheduled_task_run(self, task_name: str) -> str:
        if self.system != "Windows":
            return "Error: scheduled_task_run is Windows-only."
        name = (task_name or "").strip().replace('"', "")
        if not name:
            return "Error: task_name required."
        return self.run_powershell(
            f"Start-ScheduledTask -TaskName \"{name}\" -ErrorAction Stop; 'OK'",
            timeout=30,
        )

    def scheduled_task_create_daily(
        self, task_name: str, command: str, time_hhmm: str = "09:00"
    ) -> str:
        if not self.rules.get("allow_system_changes", False):
            return "Error: task creation is disabled by rules (rules.allow_system_changes=false)."
        if self.system != "Windows":
            return "Error: scheduled_task_create_daily is Windows-only."
        name = (task_name or "").strip().replace('"', "")
        cmd = (command or "").strip()
        t = (time_hhmm or "09:00").strip()
        if not name or not cmd:
            return "Error: task_name and command required."
        # Create a basic daily task using schtasks (simpler + predictable).
        return self.run_command(
            f'schtasks /Create /F /SC DAILY /TN "{name}" /TR "{cmd}" /ST {t}',
            timeout=30,
        )
