#!/usr/bin/python
"""
Parse ALOHA ascii trace file from NS-3 Aqua-Sim to extract results from simulation.
"""


import sys
import numpy
import re


# Energy-related pararmeters
TX_POWER = 60.0     # Watts
RX_POWER = 0.158     # Watts
IDLE_POWER = 0.158   # Watts
LINK_SPEED = 80000.0  # bps


# Parse trace file to tx/rx events
def parse_events(trace_file_path):
    # Store raw tx/rx events, parsed from the original trace file
    EVENTS = []

    with open(trace_file_path, "r") as f:
        # Store tx/rx event list
        event = ""
        i = 0
        for line in f:

            if (line[0] == "t" or line[0] =="r") and (i != 0):

                EVENTS.append(event)

                event = line[:-1]

            else:
                event += line[:-1]

            i += 1

        EVENTS.append(event)
    return EVENTS


def print_events(EVENTS):
    for event in EVENTS:
        #if event[0] == "t":
            print (event)
            print ("")


def parse_field_value(line, field_name):
    """Parse a specific field value from the trace line using regex"""
    import re
    pattern = rf'{field_name}=([^)\s]+)'
    match = re.search(pattern, line)
    if match:
        value = match.group(1)
        # Remove trailing comma if present
        if value.endswith(','):
            value = value[:-1]
        return value
    return None

def parse_fields(EVENTS):
    # TRACE object with parsed fields
    TRACE = {"bad":[],"RX/TX-MODE": [], "TS": [], "NODE_ID": [], "TX_POWER": [], "RX_POWER": [], "TX_TIME": [], "DIRECTION": [],
    "NUM_FORWARDS": [], "ERROR": [], "UNIQUE_ID": [], "PTYPE": [], "PAYLOAD_SIZE": [], "MAC_SRC_ADDR": [], "MAC_DST_ADDR": [], "ORIGINAL_LINE": []}

    # Store per Node information: number of processed RX events, number of collisions
    NODE_VALUES = {"PROCESSED_RX_COUNT": 0, "RX_ENERGY": 0.0, "TX_ENERGY": 0.0, "IDLE_ENERGY": 0.0, "COLLISION_COUNT": 0, "LAST_TS": 0.0}
    #NODE_INFO = {"NODE_ID": {"PROCESSED_RX_COUNT": 0, "RX_ENERGY": 0.0, "TX_ENERGY": 0.0, "IDLE_ENERGY": 0.0, "COLLISION_COUNT": 0, "LAST_TS": 0.0}}
    NODE_INFO = {}
    for i in range(300):
        NODE_INFO[i] = dict(NODE_VALUES)

    def ensure_node_exists(node_id):
        """Ensure a node exists in NODE_INFO, create it if it doesn't"""
        if node_id not in NODE_INFO:
            NODE_INFO[node_id] = dict(NODE_VALUES)

    # Parse the fields
    for line in EVENTS:

        stripped_line = line.split(" ")
        if line[0] == "t":
            # Store original line for later use
            TRACE["ORIGINAL_LINE"].append(line)
            # Use dynamic parsing instead of hard-coded indices
            ptype = parse_field_value(line, "PacketType")
            if ptype is None:
                ptype = "UNKNOWN"
            TRACE["PTYPE"].append(ptype)
            TRACE["RX/TX-MODE"].append("TX")
            ts = float(stripped_line[1])
            TRACE["TS"].append(ts)
            node_id = int(stripped_line[2].split("/")[2])
            TRACE["NODE_ID"].append(node_id)

            TRACE["TX_POWER"].append(TX_POWER)

            # Parse Size from the line
            size_match = parse_field_value(line, "Size")
            if size_match:
                payload_size = int(size_match)
            else:
                payload_size = 50  # default
            TRACE["PAYLOAD_SIZE"].append(payload_size)

            TRACE["RX_POWER"].append(0)

            # Parse TxTime
            txtime_match = parse_field_value(line, "TxTime")
            if txtime_match:
                # Remove + and ns suffix
                txtime_str = txtime_match.replace('+', '').replace('ns', '')
                try:
                    tx_time = float(txtime_str)
                except ValueError:
                    tx_time = 0.0
            else:
                tx_time = 0.0
            TRACE["TX_TIME"].append(tx_time)

            # Parse Direction
            direction_match = parse_field_value(line, "Direction")
            if direction_match:
                direction = direction_match
            else:
                direction = "UNKNOWN"
            TRACE["DIRECTION"].append(direction)

            # Parse NumForwards
            numforwards_match = parse_field_value(line, "NumForwards")
            if numforwards_match:
                num_forwards = int(numforwards_match)
            else:
                num_forwards = 0
            TRACE["NUM_FORWARDS"].append(num_forwards)

            # Parse Error
            error_match = parse_field_value(line, "Error")
            if error_match:
                error = error_match
            else:
                error = "False"
            TRACE["ERROR"].append(error)

            # Parse UniqueID
            uniqueid_match = parse_field_value(line, "UniqueID")
            if uniqueid_match:
                unique_id = int(uniqueid_match)

            TRACE["UNIQUE_ID"].append(unique_id)

            # Parse MAC addresses
            sa_match = parse_field_value(line, "SA")
            if sa_match:
                mac_src = sa_match
            else:
                mac_src = "000"
            TRACE["MAC_SRC_ADDR"].append(mac_src)

            da_match = parse_field_value(line, "DA")
            if da_match:
                mac_dst = da_match
            else:
                mac_dst = "000"
            TRACE["MAC_DST_ADDR"].append(mac_dst)

            # Update node info
            # We need to add the IDLE power to TX power (node can't consume less than IDLE energy when in TX)
            header_size = payload_size
            ensure_node_exists(node_id)
            NODE_INFO[node_id]["TX_ENERGY"] += ((header_size * 8) / LINK_SPEED) * TX_POWER
            NODE_INFO[node_id]["TX_ENERGY"] += ((header_size * 8) / LINK_SPEED) * IDLE_POWER
            #print(ts, NODE_INFO[node_id]["LAST_TS"])
            if ts >= NODE_INFO[node_id]["LAST_TS"]:
                TRACE["bad"].append(0)
                NODE_INFO[node_id]["IDLE_ENERGY"] += ((ts - NODE_INFO[node_id]["LAST_TS"]) / 1000000000.0) * IDLE_POWER
                #print(NODE_INFO[node_id]["LAST_TS"])
                NODE_INFO[node_id]["LAST_TS"] = ts + ((header_size * 8) / LINK_SPEED)
                #print(NODE_INFO[node_id]["LAST_TS"])
                # print header_size
            else:
                TRACE["bad"].append(1)
                NODE_INFO[node_id]["COLLISION_COUNT"] += 1
                # print "TX", node_id, header_size, ts, "<--->", NODE_INFO[node_id]["LAST_TS"]


        elif line[0] == "r":
            # Store original line for later use
            #print("r:", NODE_INFO[node_id]["LAST_TS"])
            TRACE["ORIGINAL_LINE"].append(line)
            # Use dynamic parsing for RX events
            ptype = parse_field_value(line, "PacketType")
            if ptype is None:
                ptype = "UNKNOWN"
            TRACE["PTYPE"].append(ptype)
            TRACE["RX/TX-MODE"].append("RX")
            ts = float(stripped_line[1])
            TRACE["TS"].append(ts)
            node_id = int(stripped_line[2].split("/")[2])
            TRACE["NODE_ID"].append(node_id)

            TRACE["TX_POWER"].append(TX_POWER)

            # Parse Size from the line
            size_match = parse_field_value(line, "Size")
            if size_match:
                payload_size = int(size_match)
            else:
                payload_size = 50  # default
            TRACE["PAYLOAD_SIZE"].append(payload_size)

            TRACE["RX_POWER"].append(0)
            TRACE["TX_TIME"].append(0)

            # Parse Direction
            direction_match = parse_field_value(line, "Direction")
            if direction_match:
                direction = direction_match
            else:
                direction = "UNKNOWN"
            TRACE["DIRECTION"].append(direction)

            # Parse NumForwards
            numforwards_match = parse_field_value(line, "NumForwards")
            if numforwards_match:
                num_forwards = int(numforwards_match)
            else:
                num_forwards = 0
            TRACE["NUM_FORWARDS"].append(num_forwards)

            # Parse Error
            error_match = parse_field_value(line, "Error")
            if error_match:
                error = error_match
            else:
                error = "False"
            TRACE["ERROR"].append(error)

            # Parse UniqueID
            uniqueid_match = parse_field_value(line, "UniqueID")
            if uniqueid_match:
                unique_id = int(uniqueid_match)
            TRACE["UNIQUE_ID"].append(unique_id)

            # Parse MAC addresses
            sa_match = parse_field_value(line, "SA")
            if sa_match:
                mac_src = sa_match
            else:
                mac_src = "000"
            TRACE["MAC_SRC_ADDR"].append(mac_src)

            # Try DA first, then DestAddr if DA not found
            da_match = parse_field_value(line, "DA")
            if da_match:
                mac_dst = da_match
            else:
                destaddr_match = parse_field_value(line, "DestAddress")
                if destaddr_match:
                    mac_dst = destaddr_match
                else:
                    mac_dst = "000"
            TRACE["MAC_DST_ADDR"].append(mac_dst)

            # Update node info
            # if (ts - (((header_size) * 8) / LINK_SPEED) * 1000000000.0) > NODE_INFO[node_id]["LAST_TS"]:
            header_size = payload_size
            ensure_node_exists(node_id)
            #print(ts - (((header_size) * 8) / LINK_SPEED) , NODE_INFO[node_id]["LAST_TS"])
            if (ts - (((header_size) * 8) / LINK_SPEED)) >= NODE_INFO[node_id]["LAST_TS"]:
                TRACE["bad"].append(0)
                NODE_INFO[node_id]["PROCESSED_RX_COUNT"] += 1
                NODE_INFO[node_id]["IDLE_ENERGY"] += ((ts - NODE_INFO[node_id]["LAST_TS"]) / 1000000000.0) * IDLE_POWER
                # print header_size
                # NODE_INFO[node_id]["LAST_TS"] = ts + ((header_size * 8) / LINK_SPEED) * 1000000000.0
                # NODE_INFO[node_id]["LAST_TS"] = ts - (((header_size) * 8) / LINK_SPEED) * 1000000000.0    # Rx event is traced at the end of reception, therefore, we need to find the beginning of Rx
                NODE_INFO[node_id]["LAST_TS"] = ts
                NODE_INFO[node_id]["RX_ENERGY"] += ((header_size * 8) / LINK_SPEED) * RX_POWER
            else:
                TRACE["bad"].append(1)
                NODE_INFO[node_id]["COLLISION_COUNT"] += 1
                # print "RX", node_id, header_size, (ts - (((header_size) * 8) / LINK_SPEED) * 1000000000.0), "<--->", NODE_INFO[node_id]["LAST_TS"]
                # print (NODE_INFO[node_id]["LAST_TS"] - (ts - (((header_size) * 8) / LINK_SPEED) * 1000000000.0)) / 1000000000.

    return TRACE, NODE_INFO

def convert_string_to_int(s):
    """
    基于255进制的转换算法：
    - 如果字符串以0开头，则不转换，直接返回去掉前导0后的数字
    - 如果字符串不以0开头，则将首位乘以255，然后加上后面几位组成的数字
    """
    
    # 验证输入字符串长度
    if len(s) < 1 or len(s) > 4:
        raise ValueError("字符串长度必须在1-4位之间")
    
    # 验证所有字符都是数字
    if not s.isdigit():
        raise ValueError("字符串必须只包含数字")
    
    # 情况1: 字符串以0开头，不转换，直接返回去掉前导0后的数字
    if s[0] == '0':
        # 去掉前导0
        if len(s) > 1:
            return int(s[1:])  # 返回去掉首位0后的数字
        else:
            return 0  # 只有一位0，返回0
    
    # 情况2: 字符串不以0开头，进行255进制转换
    else:
        if len(s) == 1:
            # 只有一位，直接返回
            return int(s)
        else:
            # 首位乘以255，加上后面几位组成的数字
            first_digit = int(s[0])
            remaining_digits = int(s[1:])
            return first_digit * 255 + remaining_digits

# Print the parsed trace object
def print_trace(TRACE):
    for i in range(len(TRACE["UNIQUE_ID"])):
        if TRACE["RX/TX-MODE"][i] == "RX" and TRACE["PTYPE"][i] == "ACK":
            original_line = TRACE["ORIGINAL_LINE"][i]
            dest_match = re.search(r'DestAddress=(\d+)', original_line)
            if dest_match:
                dest_addr = dest_match.group(1)
                print(dest_addr,end = " ")
    


def detect_tx_conflicts(TRACE, tx_range=5000):
    collision_count = 0
    for i in range(len(TRACE["RX/TX-MODE"])):
        if TRACE["RX/TX-MODE"][i] == "RX":
            if TRACE["ERROR"][i] == "True":
                collision_count += 1
    return collision_count


def calc_recv_packets(TRACE):
    # Count packets that reached their intended destination
    successful_deliveries = set()
    for i in range(len(TRACE["TS"])):
        if TRACE["RX/TX-MODE"][i] == "RX" and TRACE["bad"][i] == 0:
            original_line = TRACE["ORIGINAL_LINE"][i]
            dest_match = re.search(r'DestAddress=(\d+)', original_line)
            if dest_match:
                dest_addr = dest_match.group(1)
                node_id = TRACE["NODE_ID"][i]
                unique_id = TRACE["UNIQUE_ID"][i]
                if convert_string_to_int(dest_addr) == node_id + 1:# or dest_addr == 255255:
                    successful_deliveries.add(unique_id)

    return len(successful_deliveries)


# Calculate number of actual hops a received packet has traversed (avg hop count)
def calc_hop_count(TRACE):
    return 1.0


# Calculate average end-to-end delay
def calc_delay(TRACE):
    delays = []
    processed_ids = []
    for i in range(len(TRACE["TS"])):
        if (int(TRACE["MAC_DST_ADDR"][i]) == TRACE["NODE_ID"][i] + 1) and (TRACE["UNIQUE_ID"][i] not in processed_ids):
            # Find the timestamp when this packet were initially sent
            for j in range(len(TRACE["TS"])):
                if (TRACE["UNIQUE_ID"][i] == TRACE["UNIQUE_ID"][j] and TRACE["RX/TX-MODE"][j] == "TX"):

                    delays.append((TRACE["TS"][i] - TRACE["TS"][j]) / 1000000000.) # to Seconds


            processed_ids.append(TRACE["UNIQUE_ID"][i])

    return numpy.array(delays).mean()


# Calculate "instantaneous" throuhgput - number of bits received over a second
def calc_isntantaneous_throughput(TRACE):
    processed_ids = []
    # Find the fisrt starting ts
    start_ts = 0.0
    num_recv_packets = 0
    timestamps = []
    throughputs = []
    moving_average = []
    previous_average = 0.0
    k = 1
    for i in range(len(TRACE["TS"])):
        if (int(TRACE["MAC_DST_ADDR"][i]) == TRACE["NODE_ID"][i] + 1) and (TRACE["UNIQUE_ID"][i] not in processed_ids):
            start_ts = float(TRACE["TS"][i])
            num_recv_packets += 1
            break

    # Go through the dictionary and find the packets, which MAC_DST_ADDR matches the address of the node.
    # Also, ignore duplicate receptions (if any) by checking UNIQUE_ID field
    for i in range(1, len(TRACE["TS"])):
        if (int(TRACE["MAC_DST_ADDR"][i]) == TRACE["NODE_ID"][i] + 1) and (TRACE["UNIQUE_ID"][i] not in processed_ids):
            processed_ids.append(TRACE["UNIQUE_ID"][i])
            if (float(TRACE["TS"][i] - start_ts)) < 10000000000.0: # if the time difference between current ts and starting ts is less than 10 seconds
                num_recv_packets += 1
            
            else:
                timestamps.append(float(TRACE["TS"][i] / 1000000000.0))
                current_throughput = (num_recv_packets * PACKET_SIZE * 8) / ((float(TRACE["TS"][i]) - start_ts) / 1000000000.0)
                throughputs.append(current_throughput)
                current_average = previous_average + (current_throughput - previous_average) / k
                moving_average.append(current_average)
                previous_average = current_average
                k += 1
                # inst_throuhgput[float(TRACE["TS"][i] / 1000000000.0)] = (num_recv_packets * PACKET_SIZE * 8) / ((float(TRACE["TS"][i]) - start_ts) / 1000000000.0) # bits
                start_ts = float(TRACE["TS"][i])
                num_recv_packets = 1

    return (timestamps, throughputs, moving_average)


# Calculate number of packets, sent by the source node (not counting the relays)
def calc_sent_packets(TRACE):
    num_sent_packets = 0
    processed_ids = []

    # Go through the dictionary and find the packets, which MAC_SRC_ADDR mathes the address of the node.
    # Also, ignore duplicate receptions (if any) by checking UNIQUE_ID field
    for i in range(len(TRACE["TS"])):
            num_sent_packets += 1

    return num_sent_packets


# Calculate total number of TX events
def calc_tx_calls(TRACE):
    return TRACE["RX/TX-MODE"].count("TX")


# Calculate total number of RX events
def calc_rx_calls(TRACE):
    return TRACE["RX/TX-MODE"].count("RX")

def calc_rx_nocol_calls(NODE_INFO):
    res = 0
    for i in range(len(NODE_INFO)):
        res = res + NODE_INFO[i]["PROCESSED_RX_COUNT"]
    return res

# Calculate total energy consumption
def calc_energy_consumption(NODE_INFO):
    total_energy = 0.0

    # print NODE_INFO
    for node in NODE_INFO:
        total_energy += NODE_INFO[node]["RX_ENERGY"]
    	# print "RX_ENERGY: ", NODE_INFO[node]["RX_ENERGY"]
        total_energy += NODE_INFO[node]["TX_ENERGY"]
        # print "TX_ENERGY: ", NODE_INFO[node]["TX_ENERGY"]
        total_energy += NODE_INFO[node]["IDLE_ENERGY"]
        # print "IDLE_ENERGY: ", NODE_INFO[node]["IDLE_ENERGY"]

    # print total_energy
    return total_energy


PACKET_SIZE = 800 # bytes
# Calculate energy per bit (received bit)
def calc_energy_per_bit(NODE_INFO, TRACE):
    total_energy = calc_energy_consumption(NODE_INFO)
    n_recv_packets = calc_recv_packets(TRACE)
    if n_recv_packets == 0:
        return 0.0
    return total_energy / (n_recv_packets * PACKET_SIZE * 8)


# Calculate total number of collisionis from all nodes
def calc_total_collisions(NODE_INFO):
    collision_count = 0
    for node in NODE_INFO:
        collision_count += NODE_INFO[node]["COLLISION_COUNT"]

    return collision_count


# Throughput calculation
def calc_throughput(TRACE):
    n_tx = calc_tx_calls(TRACE)
    throughput = (n_tx * TRACE["PAYLOAD_SIZE"][0])
    return throughput


# PDR
def calc_pdr(TRACE):
    n_recv_packets = calc_recv_packets(TRACE)
    n_sent_packets = calc_sent_packets(TRACE)
    pdr = (float(n_recv_packets) / n_sent_packets)
    return pdr


def main():
    # Parse the trace file to a list of tx/rx events
    TRACE_FILE_PATH = sys.argv[1]
    EVENTS = parse_events(TRACE_FILE_PATH)
    # print_events()
    TRACE, NODE_INFO = parse_fields(EVENTS)
    # print_trace()

    # Calculate number of sent and recevied packets
    n_recv_packets = calc_recv_packets(TRACE)
    print ("Number of received packets: ", n_recv_packets)
    n_sent_packets = calc_sent_packets(TRACE)
    print ("Number of sent packets: ", n_sent_packets)
    print ("Total number of tx calls: ", calc_tx_calls(TRACE))
    print ("Total number of rx calls: ", calc_rx_calls(TRACE))
    print ("Total energy consumption: ", calc_energy_consumption(NODE_INFO))
    print ("Energy per bit: ", calc_energy_per_bit(NODE_INFO, TRACE))
    print ("Throughput: ", calc_throughput(TRACE))
    # print ("Throughput per node: ", (n_recv_packets * 8 * TRACE["PAYLOAD_SIZE"][0]) / ((max(TRACE["NODE_ID"]) + 1) * (TRACE["TS"][-1] / 1000000000.0)))
    print ("PDR: ", float(n_recv_packets) / n_sent_packets)
    print ("Number of collisions: ", calc_total_collisions(NODE_INFO))
    print ("Instantaneous throuhgput: ", calc_isntantaneous_throughput(TRACE))
    print ("Average hop count: ", calc_hop_count(TRACE))


if __name__ == '__main__':
    main()