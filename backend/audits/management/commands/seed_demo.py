"""
Management command to populate the database with realistic demo data.

Usage:
    python manage.py seed_demo          # Add demo data
    python manage.py seed_demo --reset  # Wipe existing data first
"""

import random
from datetime import timedelta
from textwrap import dedent

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from audits.models import AuditComment, AuditRun, AuditSchedule, RuleResult, Tag
from devices.models import Device, DeviceGroup, DeviceHeader
from rules.models import CustomRule, SimpleRule
from settings.models import SiteSettings


# ---------------------------------------------------------------------------
# Realistic network device configurations
# ---------------------------------------------------------------------------

CONFIG_TEMPLATES = {
    "router": dedent("""\
        ! Router configuration - {name}
        hostname {name}
        !
        service timestamps debug datetime msec
        service timestamps log datetime msec
        service password-encryption
        !
        aaa new-model
        aaa authentication login default local
        aaa authorization exec default local
        !
        ip ssh version 2
        ip ssh time-out 60
        ip ssh authentication-retries 3
        !
        ntp server 10.0.0.1
        ntp server 10.0.0.2
        !
        logging buffered 64000
        logging host 10.10.10.100
        logging trap informational
        !
        banner motd ^
        *** AUTHORIZED ACCESS ONLY ***
        This system is the property of Example Corp.
        Unauthorized access is prohibited.
        ^
        !
        interface GigabitEthernet0/0
         ip address 192.168.1.1 255.255.255.0
         no shutdown
        !
        interface GigabitEthernet0/1
         ip address 10.0.1.1 255.255.255.0
         no shutdown
        !
        ip route 0.0.0.0 0.0.0.0 192.168.1.254
        !
        access-list 10 permit 10.0.0.0 0.0.255.255
        access-list 10 deny any log
        !
        snmp-server community public RO
        snmp-server community private RW
        snmp-server host 10.10.10.100 version 2c public
        !
        line con 0
         exec-timeout 5 0
         logging synchronous
        line vty 0 4
         transport input ssh
         exec-timeout 10 0
        !
        end
    """),
    "switch": dedent("""\
        ! Switch configuration - {name}
        hostname {name}
        !
        service timestamps debug datetime msec
        service timestamps log datetime msec
        service password-encryption
        !
        aaa new-model
        aaa authentication login default local
        !
        ip ssh version 2
        !
        ntp server 10.0.0.1
        !
        logging host 10.10.10.100
        logging trap warnings
        !
        spanning-tree mode rapid-pvst
        spanning-tree extend system-id
        !
        vlan 10
         name MANAGEMENT
        vlan 20
         name SERVERS
        vlan 30
         name WORKSTATIONS
        vlan 99
         name NATIVE
        !
        interface GigabitEthernet0/1
         switchport mode access
         switchport access vlan 10
         spanning-tree portfast
        !
        interface GigabitEthernet0/2
         switchport mode trunk
         switchport trunk native vlan 99
         switchport trunk allowed vlan 10,20,30
        !
        interface Vlan10
         ip address 10.10.10.2 255.255.255.0
        !
        ip default-gateway 10.10.10.1
        !
        line con 0
         exec-timeout 5 0
        line vty 0 4
         transport input ssh
        !
        end
    """),
    "firewall": dedent("""\
        ! Firewall configuration - {name}
        hostname {name}
        !
        service timestamps debug datetime msec
        service timestamps log datetime msec
        service password-encryption
        !
        aaa new-model
        aaa authentication login default local
        aaa authorization exec default local
        !
        ip ssh version 2
        ip ssh time-out 30
        !
        ntp server 10.0.0.1
        ntp server 10.0.0.2
        !
        logging buffered 128000
        logging host 10.10.10.100
        logging trap informational
        !
        banner motd ^
        *** AUTHORIZED ACCESS ONLY ***
        All activity is monitored and logged.
        ^
        !
        interface GigabitEthernet0/0
         nameif outside
         security-level 0
         ip address 203.0.113.1 255.255.255.252
        !
        interface GigabitEthernet0/1
         nameif inside
         security-level 100
         ip address 10.0.0.1 255.255.255.0
        !
        interface GigabitEthernet0/2
         nameif dmz
         security-level 50
         ip address 172.16.0.1 255.255.255.0
        !
        access-list OUTSIDE_IN extended deny ip any any log
        access-list INSIDE_OUT extended permit tcp 10.0.0.0 255.255.255.0 any eq 443
        access-list INSIDE_OUT extended permit tcp 10.0.0.0 255.255.255.0 any eq 80
        access-list INSIDE_OUT extended permit udp 10.0.0.0 255.255.255.0 any eq 53
        !
        ip route outside 0.0.0.0 0.0.0.0 203.0.113.2
        !
        line con 0
         exec-timeout 5 0
        line vty 0 4
         transport input ssh
         exec-timeout 5 0
        !
        end
    """),
    "router_insecure": dedent("""\
        ! Router configuration - {name}
        hostname {name}
        !
        service timestamps debug datetime msec
        no service password-encryption
        !
        enable password cisco123
        !
        ip ssh version 1
        !
        ntp server 10.0.0.1
        !
        logging buffered 4096
        !
        interface GigabitEthernet0/0
         ip address 192.168.5.1 255.255.255.0
         no shutdown
        !
        interface GigabitEthernet0/1
         ip address 10.0.5.1 255.255.255.0
         no shutdown
        !
        ip route 0.0.0.0 0.0.0.0 192.168.5.254
        !
        snmp-server community public RW
        !
        ip http server
        ip http secure-server
        !
        line con 0
         no exec-timeout
        line vty 0 4
         transport input telnet ssh
         no exec-timeout
        !
        end
    """),
}


def _make_config(template_key, device_name):
    return CONFIG_TEMPLATES[template_key].format(name=device_name)


class Command(BaseCommand):
    help = "Populate the database with realistic demo data for NetAudit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing demo-seeded data before creating new data.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting existing data...")
            RuleResult.objects.all().delete()
            AuditComment.objects.all().delete()
            AuditRun.objects.all().delete()
            AuditSchedule.objects.all().delete()
            Tag.objects.all().delete()
            CustomRule.objects.all().delete()
            SimpleRule.objects.all().delete()
            DeviceHeader.objects.all().delete()
            Device.objects.all().delete()
            DeviceGroup.objects.all().delete()
            User.objects.filter(username__startswith="demo_").delete()

        now = timezone.now()

        # --- Site settings ---
        site = SiteSettings.load()
        if not site.default_api_endpoint:
            site.default_api_endpoint = "https://netconfig.example.com/api/v1/devices"
            site.save()
            self.stdout.write("  Site settings configured")

        # --- Users ---
        users = self._create_users()

        # --- Device groups ---
        groups = self._create_device_groups()

        # --- Devices ---
        devices = self._create_devices(groups)

        # --- Rules ---
        simple_rules = self._create_simple_rules(groups)
        custom_rules = self._create_custom_rules(groups)

        # --- Tags ---
        tags = self._create_tags()

        # --- Audit runs with results ---
        audit_runs = self._create_audit_runs(
            devices, simple_rules, custom_rules, tags, users, now
        )

        # --- Schedules ---
        self._create_schedules(devices)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDemo data created successfully!\n"
                f"  Users:        {len(users)}\n"
                f"  Groups:       {len(groups)}\n"
                f"  Devices:      {len(devices)}\n"
                f"  Simple rules: {len(simple_rules)}\n"
                f"  Custom rules: {len(custom_rules)}\n"
                f"  Tags:         {len(tags)}\n"
                f"  Audit runs:   {len(audit_runs)}\n"
                f"  Schedules:    {AuditSchedule.objects.count()}\n"
                f"\nLogin credentials:\n"
                f"  admin / demo_admin  (admin role)\n"
                f"  editor / demo_editor (editor role)\n"
                f"  viewer / demo_viewer (viewer role)\n"
            )
        )

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _create_users(self):
        users = []
        user_defs = [
            ("admin", "admin@example.com", "demo_admin", User.Role.ADMIN),
            ("editor", "editor@example.com", "demo_editor", User.Role.EDITOR),
            ("viewer", "viewer@example.com", "demo_viewer", User.Role.VIEWER),
            ("demo_auditor", "auditor@example.com", "demo_auditor", User.Role.EDITOR),
        ]
        for username, email, password, role in user_defs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": role,
                    "is_staff": role == User.Role.ADMIN,
                    "is_superuser": role == User.Role.ADMIN,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"  Created user: {username} ({role})")
            users.append(user)
        return users

    # ------------------------------------------------------------------
    # Device groups
    # ------------------------------------------------------------------
    def _create_device_groups(self):
        group_defs = [
            ("Core Routers", "Primary backbone routers in the data center"),
            ("Edge Switches", "Access-layer switches across campus buildings"),
            ("Perimeter Firewalls", "Internet-facing firewall appliances"),
            ("Branch Office", "Remote branch office network equipment"),
        ]
        groups = []
        for name, desc in group_defs:
            g, created = DeviceGroup.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            if created:
                self.stdout.write(f"  Created group: {name}")
            groups.append(g)
        return groups

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------
    def _create_devices(self, groups):
        device_defs = [
            # (name, hostname, groups_idx_list, config_template, enabled)
            ("core-rtr-01", "core-rtr-01.dc1.example.com", [0], "router", True),
            ("core-rtr-02", "core-rtr-02.dc1.example.com", [0], "router", True),
            ("edge-sw-01", "edge-sw-01.bldg-a.example.com", [1], "switch", True),
            ("edge-sw-02", "edge-sw-02.bldg-b.example.com", [1], "switch", True),
            ("edge-sw-03", "edge-sw-03.bldg-c.example.com", [1], "switch", True),
            ("fw-perimeter-01", "fw-01.dmz.example.com", [2], "firewall", True),
            ("fw-perimeter-02", "fw-02.dmz.example.com", [2], "firewall", True),
            ("branch-rtr-nyc", "rtr.nyc.example.com", [3], "router_insecure", True),
            ("branch-rtr-lon", "rtr.lon.example.com", [3], "router", True),
            ("branch-sw-nyc", "sw.nyc.example.com", [1, 3], "switch", False),
        ]
        devices = []
        for name, hostname, group_idxs, config_tpl, enabled in device_defs:
            d, created = Device.objects.get_or_create(
                name=name,
                defaults={
                    "hostname": hostname,
                    "enabled": enabled,
                },
            )
            if created:
                for idx in group_idxs:
                    d.groups.add(groups[idx])
                self.stdout.write(f"  Created device: {name}")
            # Store config template key for later use
            d._config_tpl = config_tpl
            devices.append(d)

        # Add some device headers
        header_defs = [
            (devices[0], "Authorization", "Bearer eyJhbGciOiJIUzI1NiJ9.demo-token"),
            (devices[0], "X-Device-Type", "router"),
            (devices[5], "Authorization", "Bearer eyJhbGciOiJIUzI1NiJ9.fw-token"),
            (devices[5], "X-Device-Type", "firewall"),
        ]
        for dev, key, value in header_defs:
            DeviceHeader.objects.get_or_create(
                device=dev, key=key, defaults={"value": value}
            )

        return devices

    # ------------------------------------------------------------------
    # Simple rules
    # ------------------------------------------------------------------
    def _create_simple_rules(self, groups):
        rule_defs = [
            # Global rules (no device or group filter)
            {
                "name": "SSH Version 2 Required",
                "description": "Ensure SSH version 2 is configured for secure remote access",
                "rule_type": "must_contain",
                "pattern": "ip ssh version 2",
                "severity": "critical",
            },
            {
                "name": "No Telnet on VTY Lines",
                "description": "VTY lines should only allow SSH transport",
                "rule_type": "must_not_contain",
                "pattern": "transport input telnet",
                "severity": "critical",
            },
            {
                "name": "Password Encryption Enabled",
                "description": "Service password-encryption must be active",
                "rule_type": "must_contain",
                "pattern": "service password-encryption",
                "severity": "high",
            },
            {
                "name": "NTP Configured",
                "description": "At least one NTP server must be configured",
                "rule_type": "regex_match",
                "pattern": r"ntp server \d+\.\d+\.\d+\.\d+",
                "severity": "high",
            },
            {
                "name": "Syslog Server Configured",
                "description": "A remote logging host must be configured",
                "rule_type": "must_contain",
                "pattern": "logging host",
                "severity": "high",
            },
            {
                "name": "AAA Authentication Enabled",
                "description": "AAA new-model must be enabled for authentication",
                "rule_type": "must_contain",
                "pattern": "aaa new-model",
                "severity": "high",
            },
            {
                "name": "No Plaintext Passwords",
                "description": "Configuration should not contain plaintext enable passwords",
                "rule_type": "regex_no_match",
                "pattern": r"enable password \S+",
                "severity": "critical",
            },
            {
                "name": "Console Timeout Set",
                "description": "Console line should have an exec-timeout configured",
                "rule_type": "regex_match",
                "pattern": r"line con 0\s+exec-timeout \d+ \d+",
                "severity": "medium",
            },
            {
                "name": "No HTTP Server",
                "description": "HTTP server should be disabled on all devices",
                "rule_type": "must_not_contain",
                "pattern": "ip http server",
                "severity": "high",
            },
            {
                "name": "SNMP Community Not Public RW",
                "description": "SNMP public community should not have RW access",
                "rule_type": "must_not_contain",
                "pattern": "snmp-server community public RW",
                "severity": "critical",
            },
            {
                "name": "Login Banner Present",
                "description": "A login banner must be configured for legal compliance",
                "rule_type": "must_contain",
                "pattern": "banner motd",
                "severity": "medium",
            },
            {
                "name": "VTY Timeout Configured",
                "description": "VTY lines should have exec-timeout to prevent idle sessions",
                "rule_type": "regex_match",
                "pattern": r"line vty 0 4\s+.*exec-timeout \d+ \d+",
                "severity": "medium",
            },
        ]

        # Group-specific rules
        group_rules = [
            {
                "name": "Spanning Tree Rapid-PVST",
                "description": "Edge switches must use rapid-pvst spanning tree mode",
                "rule_type": "must_contain",
                "pattern": "spanning-tree mode rapid-pvst",
                "severity": "medium",
                "group": groups[1],  # Edge Switches
            },
            {
                "name": "Firewall Deny-All Default",
                "description": "Perimeter firewalls must have a deny-all rule on outside interface",
                "rule_type": "must_contain",
                "pattern": "deny ip any any log",
                "severity": "critical",
                "group": groups[2],  # Perimeter Firewalls
            },
            {
                "name": "Dual NTP Servers",
                "description": "Core routers need redundant NTP for accurate timing",
                "rule_type": "regex_match",
                "pattern": r"(?s)ntp server \d+\.\d+\.\d+\.\d+.*ntp server \d+\.\d+\.\d+\.\d+",
                "severity": "medium",
                "group": groups[0],  # Core Routers
            },
        ]

        rules = []
        for rdef in rule_defs:
            r, created = SimpleRule.objects.get_or_create(
                name=rdef["name"],
                defaults={
                    "description": rdef["description"],
                    "rule_type": rdef["rule_type"],
                    "pattern": rdef["pattern"],
                    "severity": rdef["severity"],
                },
            )
            if created:
                self.stdout.write(f"  Created simple rule: {rdef['name']}")
            rules.append(r)

        for rdef in group_rules:
            group = rdef.pop("group")
            r, created = SimpleRule.objects.get_or_create(
                name=rdef["name"],
                defaults={**rdef, "group": group},
            )
            if created:
                self.stdout.write(f"  Created simple rule: {rdef['name']} (group-scoped)")
            rules.append(r)

        # One disabled rule
        r, created = SimpleRule.objects.get_or_create(
            name="Deprecated: Check for MOTD",
            defaults={
                "description": "Old rule - superseded by Login Banner Present",
                "rule_type": "must_contain",
                "pattern": "motd",
                "severity": "info",
                "enabled": False,
            },
        )
        if created:
            self.stdout.write("  Created simple rule: Deprecated: Check for MOTD (disabled)")
        rules.append(r)

        return rules

    # ------------------------------------------------------------------
    # Custom rules
    # ------------------------------------------------------------------
    def _create_custom_rules(self, groups):
        custom_defs = [
            {
                "name": "NTP Redundancy Check",
                "description": "Verify that at least two NTP servers are configured with valid IPs",
                "filename": "test_ntp_redundancy.py",
                "severity": "high",
                "content": dedent("""\
                    import re
                    import pytest

                    def test_ntp_server_count(config):
                        \"\"\"Check that at least 2 NTP servers are configured.\"\"\"
                        ntp_lines = re.findall(r"ntp server (\\S+)", config)
                        assert len(ntp_lines) >= 2, (
                            f"Expected at least 2 NTP servers, found {len(ntp_lines)}"
                        )

                    def test_ntp_server_valid_ip(config):
                        \"\"\"Check that NTP servers are valid IPv4 addresses.\"\"\"
                        import ipaddress
                        ntp_lines = re.findall(r"ntp server (\\S+)", config)
                        for server in ntp_lines:
                            try:
                                ipaddress.IPv4Address(server)
                            except ipaddress.AddressValueError:
                                pytest.fail(f"Invalid NTP server IP: {server}")
                """),
            },
            {
                "name": "ACL Validation",
                "description": "Verify access lists follow security best practices",
                "filename": "test_acl_validation.py",
                "severity": "critical",
                "content": dedent("""\
                    import re
                    import pytest

                    def test_acl_exists(config):
                        \"\"\"Check that at least one ACL is configured.\"\"\"
                        acl_lines = re.findall(r"access-list \\d+", config)
                        assert len(acl_lines) > 0, "No access lists found in configuration"

                    def test_no_permit_any_any(config):
                        \"\"\"Ensure no ACL has a blanket permit any any rule.\"\"\"
                        matches = re.findall(r"access-list \\d+ permit .*any.*any", config)
                        assert len(matches) == 0, (
                            f"Found {len(matches)} overly permissive ACL rules"
                        )
                """),
            },
            {
                "name": "Interface Security Check",
                "description": "Verify interfaces are properly configured and documented",
                "filename": "test_interface_security.py",
                "severity": "medium",
                "content": dedent("""\
                    import re
                    import pytest

                    def test_no_shutdown_interfaces_have_ip(config):
                        \"\"\"Active interfaces should have IP addresses assigned.\"\"\"
                        # Find interface blocks
                        blocks = re.split(r"(?=interface )", config)
                        for block in blocks:
                            if "no shutdown" in block and "interface" in block:
                                iface = re.search(r"interface (\\S+)", block)
                                if iface and "Loopback" not in iface.group(1):
                                    assert "ip address" in block or "switchport" in block, (
                                        f"Interface {iface.group(1)} is active but has no IP or switchport config"
                                    )
                """),
            },
            {
                "name": "VLAN Audit",
                "description": "Check VLAN configuration on switches",
                "filename": "test_vlan_audit.py",
                "severity": "low",
                "group": groups[1],  # Edge Switches
                "content": dedent("""\
                    import re
                    import pytest

                    def test_native_vlan_not_default(config):
                        \"\"\"Native VLAN should not be VLAN 1.\"\"\"
                        trunk_blocks = re.findall(
                            r"switchport trunk native vlan (\\d+)", config
                        )
                        for vlan_id in trunk_blocks:
                            assert vlan_id != "1", (
                                "Native VLAN is set to VLAN 1 (default) — security risk"
                            )

                    def test_management_vlan_exists(config):
                        \"\"\"A management VLAN should be defined.\"\"\"
                        assert re.search(
                            r"vlan \\d+\\s+name MANAGEMENT", config, re.IGNORECASE
                        ), "No management VLAN found"
                """),
            },
        ]

        rules = []
        for cdef in custom_defs:
            group = cdef.pop("group", None)
            r, created = CustomRule.objects.get_or_create(
                name=cdef["name"],
                defaults={**cdef, "group": group},
            )
            if created:
                self.stdout.write(f"  Created custom rule: {cdef['name']}")
            rules.append(r)
        return rules

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def _create_tags(self):
        tag_names = [
            "compliance",
            "security",
            "quarterly-review",
            "pre-change",
            "post-change",
            "investigation",
            "baseline",
            "remediated",
        ]
        tags = []
        for name in tag_names:
            t, created = Tag.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f"  Created tag: {name}")
            tags.append(t)
        return tags

    # ------------------------------------------------------------------
    # Audit runs + results + comments
    # ------------------------------------------------------------------
    def _create_audit_runs(self, devices, simple_rules, custom_rules, tags, users, now):
        random.seed(42)  # Reproducible demo data
        all_runs = []

        # Generate audit runs spread over the last 30 days
        scenarios = [
            # (device_idx, days_ago, status, trigger, tag_names)
            (0, 28, "completed", "manual", ["baseline", "compliance"]),
            (0, 21, "completed", "scheduled", ["compliance"]),
            (0, 14, "completed", "scheduled", ["quarterly-review"]),
            (0, 7, "completed", "scheduled", []),
            (0, 1, "completed", "manual", ["security"]),
            (1, 25, "completed", "manual", ["baseline"]),
            (1, 18, "completed", "scheduled", []),
            (1, 11, "completed", "scheduled", []),
            (1, 4, "completed", "scheduled", []),
            (2, 27, "completed", "manual", ["baseline"]),
            (2, 20, "completed", "scheduled", []),
            (2, 13, "completed", "scheduled", ["pre-change"]),
            (2, 12, "completed", "manual", ["post-change"]),
            (2, 6, "completed", "scheduled", []),
            (3, 22, "completed", "manual", ["baseline"]),
            (3, 15, "completed", "scheduled", []),
            (3, 8, "failed", "scheduled", []),
            (3, 1, "completed", "scheduled", []),
            (4, 26, "completed", "manual", ["baseline"]),
            (4, 19, "completed", "scheduled", []),
            (5, 27, "completed", "manual", ["baseline", "security"]),
            (5, 20, "completed", "scheduled", ["security"]),
            (5, 13, "completed", "scheduled", []),
            (5, 6, "completed", "scheduled", []),
            (5, 0, "completed", "manual", ["security", "quarterly-review"]),
            (6, 24, "completed", "manual", ["baseline"]),
            (6, 17, "completed", "scheduled", []),
            (7, 23, "completed", "manual", ["baseline", "investigation"]),
            (7, 16, "completed", "scheduled", ["investigation"]),
            (7, 9, "completed", "manual", ["remediated"]),
            (7, 2, "completed", "scheduled", []),
            (8, 26, "completed", "manual", ["baseline"]),
            (8, 19, "completed", "scheduled", []),
            (8, 12, "completed", "scheduled", []),
            (0, 0, "pending", "manual", []),
            (3, 0, "fetching_config", "scheduled", []),
        ]

        tag_map = {t.name: t for t in tags}

        for dev_idx, days_ago, status, trigger, tag_names in scenarios:
            device = devices[dev_idx]
            config_tpl = getattr(device, "_config_tpl", "router")
            config = _make_config(config_tpl, device.name)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 12))

            run = AuditRun(
                device=device,
                status=status,
                trigger=trigger,
            )

            if status == "completed":
                run.config_snapshot = config
                run.config_fetched_at = created_at + timedelta(seconds=2)
                run.started_at = created_at + timedelta(seconds=3)
                run.completed_at = created_at + timedelta(
                    seconds=random.randint(8, 45)
                )
            elif status == "failed":
                run.started_at = created_at + timedelta(seconds=3)
                run.error_message = (
                    "Connection timed out: unable to reach device API endpoint "
                    f"at {device.hostname}:443 after 30s"
                )
            elif status == "fetching_config":
                run.started_at = created_at + timedelta(seconds=1)

            run.save()

            # Override auto-set created_at
            AuditRun.objects.filter(pk=run.pk).update(created_at=created_at)

            # Add tags
            for tname in tag_names:
                if tname in tag_map:
                    run.tags.add(tag_map[tname])

            # Create rule results for completed runs
            if status == "completed":
                summary = self._create_rule_results(
                    run, device, config, simple_rules, custom_rules
                )
                run.summary = summary
                run.save(update_fields=["summary"])

            all_runs.append(run)

        # Add comments to some runs
        self._create_comments(all_runs, users)

        self.stdout.write(f"  Created {len(all_runs)} audit runs with results")
        return all_runs

    def _create_rule_results(self, run, device, config, simple_rules, custom_rules):
        passed = failed = error = 0

        # Evaluate simple rules against the config
        for rule in simple_rules:
            if not rule.enabled:
                continue
            # Skip group-scoped rules that don't apply to this device
            if rule.group and not device.groups.filter(pk=rule.group_id).exists():
                continue
            if rule.device and rule.device_id != device.pk:
                continue

            # Actually evaluate the rule against the config
            outcome = self._eval_simple_rule(rule, config)
            msg = ""
            if outcome == "failed":
                msg = f'Pattern {"not " if "not" in rule.rule_type else ""}found: {rule.pattern[:80]}'

            RuleResult.objects.create(
                audit_run=run,
                simple_rule=rule,
                test_node_id=f"simple_rules::{rule.name.lower().replace(' ', '_')}",
                outcome=outcome,
                message=msg,
                duration=round(random.uniform(0.001, 0.05), 4),
                severity=rule.severity,
            )
            if outcome == "passed":
                passed += 1
            elif outcome == "failed":
                failed += 1
            else:
                error += 1

        # Evaluate custom rules (simulate test outcomes)
        for rule in custom_rules:
            if not rule.enabled:
                continue
            if rule.group and not device.groups.filter(pk=rule.group_id).exists():
                continue
            if rule.device and rule.device_id != device.pk:
                continue

            # Each custom rule file has multiple test functions
            test_fns = self._extract_test_functions(rule.content)
            for fn_name in test_fns:
                outcome = self._eval_custom_test(fn_name, config, device)
                msg = ""
                if outcome == "failed":
                    msg = f"Assertion failed in {fn_name}"

                RuleResult.objects.create(
                    audit_run=run,
                    custom_rule=rule,
                    test_node_id=f"{rule.filename}::{fn_name}",
                    outcome=outcome,
                    message=msg,
                    duration=round(random.uniform(0.01, 0.3), 4),
                    severity=rule.severity,
                )
                if outcome == "passed":
                    passed += 1
                elif outcome == "failed":
                    failed += 1
                else:
                    error += 1

        return {"passed": passed, "failed": failed, "error": error}

    def _eval_simple_rule(self, rule, config):
        """Evaluate a simple rule against config text. Returns outcome string."""
        import re as re_mod

        pattern = rule.pattern
        try:
            if rule.rule_type == "must_contain":
                return "passed" if pattern in config else "failed"
            elif rule.rule_type == "must_not_contain":
                return "passed" if pattern not in config else "failed"
            elif rule.rule_type == "regex_match":
                return "passed" if re_mod.search(pattern, config) else "failed"
            elif rule.rule_type == "regex_no_match":
                return "passed" if not re_mod.search(pattern, config) else "failed"
        except re_mod.error:
            return "error"
        return "error"

    def _extract_test_functions(self, content):
        """Extract test function names from custom rule Python source."""
        import re as re_mod

        return re_mod.findall(r"def (test_\w+)\(", content)

    def _eval_custom_test(self, fn_name, config, device):
        """Simulate custom test outcomes based on config content."""
        import re as re_mod
        import ipaddress

        # NTP redundancy checks
        if fn_name == "test_ntp_server_count":
            ntp_lines = re_mod.findall(r"ntp server (\S+)", config)
            return "passed" if len(ntp_lines) >= 2 else "failed"
        if fn_name == "test_ntp_server_valid_ip":
            ntp_lines = re_mod.findall(r"ntp server (\S+)", config)
            for server in ntp_lines:
                try:
                    ipaddress.IPv4Address(server)
                except ipaddress.AddressValueError:
                    return "failed"
            return "passed"
        # ACL checks
        if fn_name == "test_acl_exists":
            return "passed" if re_mod.search(r"access-list \d+", config) else "failed"
        if fn_name == "test_no_permit_any_any":
            matches = re_mod.findall(r"access-list \d+ permit .*any.*any", config)
            return "passed" if len(matches) == 0 else "failed"
        # Interface checks
        if fn_name == "test_no_shutdown_interfaces_have_ip":
            return "passed"  # Our demo configs are well-formed
        # VLAN checks
        if fn_name == "test_native_vlan_not_default":
            trunks = re_mod.findall(r"switchport trunk native vlan (\d+)", config)
            return "passed" if all(v != "1" for v in trunks) else "failed"
        if fn_name == "test_management_vlan_exists":
            return (
                "passed"
                if re_mod.search(r"vlan \d+\s+name MANAGEMENT", config, re_mod.IGNORECASE)
                else "failed"
            )
        return "passed"

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------
    def _create_comments(self, runs, users):
        completed_runs = [r for r in runs if r.status == "completed"]
        if not completed_runs:
            return

        comment_templates = [
            "Baseline audit completed. All critical checks passing.",
            "Reviewed results — SSH version and password encryption look good across the board.",
            "Flagged 2 issues for remediation: telnet access and missing login banner. Ticket NET-1042 created.",
            "Post-change verification complete. No regressions detected after firmware upgrade.",
            "Several rules failing on this device. Scheduling maintenance window for remediation.",
            "ACL configuration needs attention — overly permissive rules detected on outside interface.",
            "NTP redundancy check failing — only one NTP server configured. Adding secondary server to change request.",
            "Quarterly compliance review: this device meets all CIS benchmark requirements.",
            "SNMP community string needs rotation. Adding to next change window.",
            "Investigated the timeout failures — device API endpoint was unreachable during datacenter maintenance.",
            "Remediation complete. Re-ran audit to confirm all checks now pass.",
            "Pre-change audit captured. Will compare with post-change results after the maintenance window.",
        ]

        admin_user = users[0]
        editor_user = users[1]

        # Add comments to select runs
        comment_idx = 0
        for run in completed_runs:
            if comment_idx >= len(comment_templates):
                break
            # Add 1-2 comments to roughly half the completed runs
            if random.random() < 0.5:
                continue

            author = random.choice([admin_user, editor_user])
            AuditComment.objects.create(
                audit_run=run,
                author=author,
                content=comment_templates[comment_idx],
            )
            comment_idx += 1

            # Sometimes add a reply
            if random.random() < 0.3 and comment_idx < len(comment_templates):
                other_author = editor_user if author == admin_user else admin_user
                AuditComment.objects.create(
                    audit_run=run,
                    author=other_author,
                    content=comment_templates[comment_idx],
                )
                comment_idx += 1

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------
    def _create_schedules(self, devices):
        schedule_defs = [
            (devices[0], "Core Router 01 Weekly Audit", "0 2 * * 1", True),
            (devices[1], "Core Router 02 Weekly Audit", "0 2 * * 1", True),
            (devices[2], "Edge Switch 01 Daily Audit", "0 3 * * *", True),
            (devices[5], "Firewall 01 Daily Security Audit", "0 1 * * *", True),
            (devices[6], "Firewall 02 Daily Security Audit", "0 1 * * *", True),
            (devices[7], "Branch NYC Bi-Weekly Audit", "0 4 1,15 * *", True),
            (devices[8], "Branch London Bi-Weekly Audit", "0 4 1,15 * *", True),
            (devices[3], "Edge Switch 02 Weekly Audit", "0 3 * * 0", False),
        ]
        for device, name, cron, enabled in schedule_defs:
            AuditSchedule.objects.get_or_create(
                device=device,
                name=name,
                defaults={
                    "cron_expression": cron,
                    "enabled": enabled,
                },
            )
        self.stdout.write(f"  Created {len(schedule_defs)} audit schedules")
