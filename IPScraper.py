import scapy.all as scapy
  
def scan(ip):
    arp_req_frame = scapy.ARP(pdst = ip)

    broadcast_ether_frame = scapy.Ether(dst = "ff:ff:ff:ff:ff:ff")
    
    broadcast_ether_arp_req_frame = broadcast_ether_frame / arp_req_frame

    answered_list = scapy.srp(broadcast_ether_arp_req_frame, timeout = 10, verbose = False)[0]
    result = []
    for i in range(0,len(answered_list)):
        client_dict = {"ip" : answered_list[i][1].psrc, "mac" : answered_list[i][1].hwsrc}
        result.append(client_dict)

    return result
  
def ip_results(result):
    print("-----------------------------------\nIP Address\tMAC Address\n-----------------------------------")
    ips = []
    for i in result:
        macAddr = (i["mac"])
        if macAddr[0:11] == "00:04:5f:ab" or macAddr[0:8] == "2c:3b:70":
            print("{}\t{}".format(i["ip"], i["mac"]))
            ips.append(i["ip"])
    return ips


