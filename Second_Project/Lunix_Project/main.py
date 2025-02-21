import re
from decimal import Decimal
#Qusay Bider 1220649///omar hamayle 1220356
# Data structures to mimic bash associative arrays
PATH_TO_CLI = {
    "/interfaces/interface[name=eth0]/state/counters": "show interfaces eth0 counters",
    "/system/memory/state": "show memory",
    "/interfaces/interface[name=eth1]/state/counters": "show interfaces eth1 counters",
    "/system/cpu/state/usage": "show cpu",
    "/routing/protocols/protocol[ospf]/ospf/state": "show ospf status",
    "/interfaces/interface[name=eth0]/state": "show interfaces eth0 status; show interfaces eth0 mac-address; show interfaces eth0 mtu; show interfaces eth0 speed",
    "/bgp/neighbors/neighbor[neighbor_address=10.0.0.1]/state": "show bgp neighbors 10.0.0.1; show bgp neighbors 10.0.0.1 received-routes; show bgp neighbors 10.0.0.1 advertised-routes",
    "/ospf/areas/area[id=0.0.0.0]/state": "show ospf area 0.0.0.0; show ospf neighbors",
    "/system/disk/state": "show disk space; show disk health",
    "/system/cpu/state": "show cpu usage; show cpu user; show cpu system; show cpu idle",
}

GNMI_OUTPUTS = {
    "/interfaces/interface[name=eth0]/state/counters": '{"in_octets": 1500000, "out_octets": 1400000, "in_errors": 10, "out_errors": 2}',
    "/system/memory/state": '{"total_memory": 4096000, "available_memory": 1024000, "used": "361296bytes"}',
    "/interfaces/interface[name=eth1]/state/counters": '{"in_octets": 200000, "out_octets": 100000, "in_errors": 5}',
    "/system/cpu/state/usage": '{"cpu_usage": 65, "idle_percentage": 35}',
    "/routing/protocols/protocol[ospf]/ospf/state": '{"ospf_area": "0.0.0.0", "ospf_state": "up"}',
    "/interfaces/interface[name=eth0]/state": '{"admin_status": "ACTIVE", "oper_status": "LINK_UP", "mac_address": "10:1C:42:2B:60:5A", "mtu": 1500, "speed": 1000000000}',
    "/bgp/neighbors/neighbor[neighbor_address=10.0.0.1]/state": '{"peer_as": 65001, "connection_state": "Established", "received_prefix_count": 120, "sent_prefix_count": 95}',
    "/ospf/areas/area[id=0.0.0.0]/state": '{"area_id": "0.0.0.0", "active_interfaces": 4, "lsdb_entries": 200, "adjacencies": [{"neighbor_id": "1.1.1.1", "state": "full"}, {"neighbor_id": "0.2.2.2", "state": "full"}]}',
    "/system/disk/state": '{"total_space": 1024000, "used_space": 500000, "available_space": 524000, "disk_health": "good"}',
    "/system/cpu/state": '{"cpu_usage": 75, "user_usage": 45, "system_usage": 20, "idle_percentage": 25, "utilization": 31, "used": 43.10}',
}

CLI_OUTPUTS = {
    "/interfaces/interface[name=eth0]/state/counters": 'in_octets: 1500000\nout_octets: 1400000\nin_errors: 10\nout_errors: 2',
    "/system/memory/state": 'total_memory: 4096000\navailable_memory: 1024000\nused: 352.8289KB',
    "/interfaces/interface[name=eth1]/state/counters": 'in_octets: 200000\nout_octets: 100000',
    "/system/cpu/state/usage": 'cpu_usage: 65\nidle_percentage: 35%',
    "/routing/protocols/protocol[ospf]/ospf/state": 'ospf_area: 0.0.0.0\nospf_state: down',
    "/interfaces/interface[name=eth0]/state": 'admin_status: Active\noper_status: LinkUp\nmac_address: 10:1C:42:2B:60:5A\nmtu: 1500\nspeed: 1G',
    "/bgp/neighbors/neighbor[neighbor_address=10.0.0.1]/state": 'peer_as: 65001\nconnection_state: established\nreceived_prefix_count: 120\nsent_prefix_count: 95',
    "/ospf/areas/area[id=0.0.0.0]/state": 'area_id: 0.0.0.0\nactive_interfaces: 4\nlsdb_entries: 200\nneighbor_id: 1.1.1.1, state: full\nneighbor_id: 2.2.2.2, state: full',
    "/system/disk/state": 'total_space: 1024000\nused_space: 500000\navailable_space: 524000\ndisk_health: good',
    "/system/cpu/state": 'cpu_usage: 75\nuser_usage: 45\nsystem_usage: 20\nidle_percentage: 25\nutilization: 31.0%\nused: 43.10',
}


class GNMIHandler:
    @staticmethod
    def normalize_case(value):
        return value.lower() if isinstance(value, str) else value

    @staticmethod
    def normalize_value(value):
        if isinstance(value, str):
            value = GNMIHandler.normalize_case(value)
            value = re.sub(r"_", "", value)
            value = re.sub(r"bytes", "", value)
            value = re.sub(r"%", "", value)

            units = {
                "k": 10**3,
                "m": 10**6,
                "g": 10**9,
                "t": 10**12,
            }
            match = re.match(r"(\d+(?:\.\d+)?)([kmgt]?)b?$", value, re.IGNORECASE)
            if match:
                number, unit = match.groups()
                if unit.lower() in units:
                    value = str(float(number) * units[unit.lower()])
                else:
                    value = number

            try:
                return str(Decimal(value))
            except:
                return value

        return str(value)

    @staticmethod
    def compare_values(key, gnmi_value, cli_value):
        gnmi_converted = GNMIHandler.normalize_value(gnmi_value)
        cli_converted = GNMIHandler.normalize_value(cli_value)

        try:
            gnmi_float = float(gnmi_converted)
            cli_float = float(cli_converted)
            if abs(gnmi_float - cli_float) < 1e-6:
                return True, gnmi_converted, cli_converted
        except (ValueError, TypeError):
            pass

        return gnmi_converted == cli_converted, gnmi_converted, cli_converted


class CLIHandler:
    @staticmethod
    def extract_cli_data(cli_data):
        cli_lines = cli_data.splitlines()
        cli_dict = {}
        for line in cli_lines:
            match = re.match(r"(\w+): (.+)", line)
            if match:
                key, value = match.groups()
                cli_dict[key] = value
        return cli_dict


class ReportGenerator:
    def __init__(self, path):
        self.path = path

    def compare_outputs(self):
        gnmi_data = GNMI_OUTPUTS.get(self.path)
        cli_data = CLI_OUTPUTS.get(self.path)

        if not gnmi_data or not cli_data:
            print(f"Error: Missing data for path {self.path}")
            return

        mismatches = []
        missing_in_gnmi = []
        missing_in_cli = []

        gnmi_dict = eval(gnmi_data)
        cli_dict = CLIHandler.extract_cli_data(cli_data)

        for key, gnmi_value in gnmi_dict.items():
            if key == "adjacencies":
                cli_adjacencies = []
                for line in cli_data.splitlines():
                    match = re.search(r"neighbor_id: (.+), state: (.+)", line)
                    if match:
                        cli_adjacencies.append({"neighbor_id": match.group(1), "state": match.group(2)})

                if sorted(gnmi_value, key=lambda x: x["neighbor_id"]) != sorted(cli_adjacencies, key=lambda x: x["neighbor_id"]):
                    mismatches.append(f"{key}: gNMI={gnmi_value}, CLI={cli_adjacencies}")
            elif key not in cli_dict:
                missing_in_cli.append(key)
            else:
                cli_value = cli_dict.get(key)
                match_result, gnmi_converted, cli_converted = GNMIHandler.compare_values(key, gnmi_value, cli_value)
                if not match_result:
                    mismatches.append(
                        f"{key}: gNMI={gnmi_value} (converted: {gnmi_converted}), "
                        f"CLI={cli_value} (converted: {cli_converted})"
                    )

        for key in cli_dict.keys():
            if key not in gnmi_dict and key != "neighbor_id":
                missing_in_gnmi.append(key)

        if missing_in_cli:
            print(f"Keys missing in CLI for path {self.path}: {missing_in_cli}")
        if missing_in_gnmi:
            print(f"Keys missing in gNMI for path {self.path}: {missing_in_gnmi}")
        if mismatches:
            print(f"Mismatches for path {self.path}:")
            print("\n".join(mismatches))
        if not missing_in_cli and not missing_in_gnmi and not mismatches:
            print(f"All values match for path {self.path}.")

    def generate_report(self):
        print(f"### Report for Path: {self.path} ###")
        print(f"gNMI Output: {GNMI_OUTPUTS.get(self.path)}")
        print(f"CLI Output: {CLI_OUTPUTS.get(self.path)}")
        self.compare_outputs()


if __name__ == "__main__":
    path = input("Enter the gNMI path for comparison: ")
    if path in PATH_TO_CLI:
        report = ReportGenerator(path)
        report.generate_report()
    else:
        print(f"Error: The gNMI path '{path}' is not recognized.")