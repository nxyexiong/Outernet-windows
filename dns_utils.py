from logger import LOGGER
from dnslib import DNSRecord


def detect_dns_answers(packet):
    try:
        return detect_dns_answers_internal(packet)
    except Exception:
        LOGGER.error("unable to extract dns info: %s" % packet)
        return None


def detect_dns_answers_internal(packet):
    # is ipv4
    if packet[0] & 0xf0 != 0x40:
        return None

    # ip header min length
    if len(packet) < 20:
        return None

    # is udp
    if packet[9] != 17:
        return None

    # get ipv4 header length
    header_len = (packet[0] & 0x0f) * 4

    # is port 53
    port = packet[header_len] * 256 + packet[header_len + 1]
    if port != 53:
        return None

    # get actual data
    data = packet[header_len + 8:]

    # get dns record
    record = DNSRecord.parse(data)

    # get question
    #question_name = b'.'.join(record.get_q().get_qname().label)
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
    import time
    start_time = time.time()
    ans = detect_dns_answers_internal(data)
    end_time = time.time()
    print(ans)
    print(end_time - start_time)
