import dnslib
import dns.resolver as dnsr

from dnslib import DNSRecord


def checksum(data):
    length = len(data)
    if length % 2 == 1:
        data += b'\x00'
    s = 0
    for i in range(0, len(data), 2):
        s += data[i] * 256 + data[i + 1]
        s = (s & 0xffff) + (s >> 16)
    return ~s & 0xffff


def query_dns_with_servers(name, servers):
    try:
        d = dnsr.Resolver(configure=False)
        d.nameservers = servers
        d.timeout = 1
        d.lifetime = 1
        ans = d.query(name, 'A')
        return [x.address for x in ans]
    except Exception:
        return []


def re_resolve_dns(packet, dnsservers, is_request):
    # get ipv4 header length
    header_len = (packet[0] & 0x0f) * 4

    # get actual data
    data = packet[header_len + 8:]

    # get dns record
    record = DNSRecord.parse(data)

    # get question
    questions = record.questions

    # remove answers
    while record.a.rdata is not None:
        record.rr.remove(record.a)

    for question in questions:
        name = b'.'.join(record.q.get_qname().label).decode()
        ips = query_dns_with_servers(name, dnsservers)
        for aip in ips:
            record.add_answer(dnslib.RR(name, dnslib.QTYPE.A, rdata=dnslib.A(aip)))

    # set response
    record.header.set_qr(1)
    record.header.set_aa(1)
    record.header.set_ra(1)

    # repack
    data = record.pack()
    packet = packet[:header_len + 8] + data

    # udp length
    length = len(packet) - header_len
    packet = packet[:header_len + 4] + bytes([length >> 8, length % 256]) + packet[header_len + 6:]

    # packet length
    length = len(packet)
    packet = packet[:2] + bytes([length >> 8, length % 256]) + packet[4:]

    # switch addr
    if is_request:
        tmp = packet[12:16]
        packet = packet[:12] + packet[16:20] + packet[16:]
        packet = packet[:16] + tmp + packet[20:]
        tmp = packet[header_len:header_len + 2]
        packet = packet[:header_len] + packet[header_len + 2:header_len + 4] + packet[header_len + 2:]
        packet = packet[:header_len + 2] + tmp + packet[header_len + 4:]

    # udp checksum
    packet = packet[:header_len + 6] + b'\x00\x00' + packet[header_len + 8:]
    chkdata = packet[12:20] + b'\x00\x11' + packet[header_len + 4:header_len + 6] + packet[header_len:]
    chksum = checksum(chkdata)
    chksum_raw = bytes([chksum >> 8, chksum % 256])
    packet = packet[:header_len + 6] + chksum_raw + packet[header_len + 8:]

    # ip checksum
    packet = packet[:10] + b'\x00\x00' + packet[12:]
    chksum = checksum(packet[:header_len])
    chksum_raw = bytes([chksum >> 8, chksum % 256])
    packet = packet[:10] + chksum_raw + packet[12:]

    # get ips
    answers = detect_dns_answers(packet)

    return packet, answers


def is_dns_packet(packet):
    try:
        # is ipv4
        if packet[0] & 0xf0 != 0x40:
            return False

        # ip header min length
        if len(packet) < 20:
            return False

        # is udp
        if packet[9] != 17:
            return False

        # get ipv4 header length
        header_len = (packet[0] & 0x0f) * 4

        # udp header min length
        if len(packet) < header_len + 8:
            return False

        # is port 53
        src_port = packet[header_len] * 256 + packet[header_len + 1]
        dst_port = packet[header_len + 2] * 256 + packet[header_len + 3]
        if src_port != 53 and dst_port != 53:
            return False

        # get actual data
        data = packet[header_len + 8:]

        # try parse
        DNSRecord.parse(data)
    except Exception:
        return False

    return True


def get_dns_qnames(packet):
    # get ipv4 header length
    header_len = (packet[0] & 0x0f) * 4

    # get actual data
    data = packet[header_len + 8:]

    # get dns record
    record = DNSRecord.parse(data)

    # get question
    questions = record.questions

    # qnames
    qnames = []
    for item in questions:
        qnames.append(b'.'.join(item.get_qname().label))

    return qnames


def detect_dns_answers(packet):
    # get ipv4 header length
    header_len = (packet[0] & 0x0f) * 4

    # get actual data
    data = packet[header_len + 8:]

    # get dns record
    record = DNSRecord.parse(data)

    # get question
    questions = record.questions

    # get answers
    answers = {}
    for item in questions:
        ans = dns_get_answers(item.get_qname().label, item.get_qname().label, record)
        answers[b'.'.join(item.get_qname().label)] = ans

    return answers


def dns_get_answers(qname_label, name_label, record):
    rdatas = record.rr
    next_names = []
    for item in rdatas:
        if item.get_rname().label == name_label:
            if item.rtype != 1:
                next_names += dns_get_answers(qname_label, item.rdata.label.label, record)
            else:
                next_names.append(str(item.rdata))
    return next_names


if __name__ == "__main__":
    data_hex = '4568011db27d00007a1172d5080808080a0000060035fbd301099b93000481800001000a0000000003617069056970696679036f72670000010001c00c0005000100000e02001c0c6e6167616e6f2d3139353939096865726f6b7573736c03636f6d00c02b0005000100000ad4002e13656c623039373330372d3933343932343933320975732d656173742d3103656c6209616d617a6f6e617773c042c053000100010000003a00041717e55ec053000100010000003a000417175399c053000100010000003a00041717f39ac053000100010000003a000436f393e2c053000100010000003a0004ae81c7e8c053000100010000003a000436e15c40c053000100010000003a000436ebbbf8c053000100010000003a00041717497c'
    data = bytearray.fromhex(data_hex)
    ans = detect_dns_answers(data)
    print(ans)

    rdata = re_resolve_dns(data, ['114.114.114.114'], False)
    print(rdata)

    req_data = b'\x45\x00\x00\x3d\x0a\x3b\x00\x00\x80\x11\x16\x64\x0a\x00\x00\x02\x08\x08\x08\x08\xf4\x4f\x00\x35\x00\x29\xdb\xe9\xdb\xcc\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03\x70\x75\x62\x07\x69\x64\x71\x71\x69\x6d\x67\x03\x63\x6f\x6d\x00\x00\x01\x00\x01'
    rdata = re_resolve_dns(req_data, ['114.114.114.114'], True)
    print(rdata)
