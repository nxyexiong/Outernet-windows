from logger import LOGGER


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

    # get count
    qdcount = data[4] * 256 + data[5]
    ancount = data[6] * 256 + data[7]

    # get answer offset
    anoffset = 12 + qdcount * 6
    for _ in range(qdcount):
        while data[anoffset] != 0:
            anoffset += 1
        anoffset += 5

    # handle answers
    answers = []
    recmap = {}
    for _ in range(ancount):
        name, nlen = read_domain_name(data, anoffset, -1)
        anoffset += nlen
        atype = data[anoffset + 1]
        aclass = data[anoffset + 3]
        ardlen = data[anoffset + 8] * 256 + data[anoffset + 9]
        if atype == 1 and aclass == 1 and ardlen == 4:
            addr = str(data[anoffset + 10]) + '.' + \
                   str(data[anoffset + 11]) + '.' + \
                   str(data[anoffset + 12]) + '.' + \
                   str(data[anoffset + 13])
            while recmap.get(name) is not None:
                name = recmap.get(name)
            answers.append((name, addr))
        elif atype == 5 and aclass == 1:
            cname, nlen = read_domain_name(data, anoffset + 10, anoffset + 10 + ardlen)
            recmap[cname] = name
        anoffset += 10 + ardlen
    return answers


def read_domain_name(data, offset, end):
    if end != -1 and offset >= end:
        return b'', 0
    name = b''
    length = 0
    if data[offset] & 0xC0 == 0xC0:
        tmpaddr = (data[offset] & 0x3F) * 256 + data[offset + 1]
        subname, sublen = read_domain_name(data, tmpaddr, end)
        name += subname
        length = 2
    else:
        while data[offset] != 0:
            if data[offset] & 0xC0 == 0xC0:
                tmpaddr = (data[offset] & 0x3F) * 256 + data[offset + 1]
                subname, sublen = read_domain_name(data, tmpaddr, end)
                if name != b'':
                    name += b'.'
                    length += 1
                name += subname
                length += 2
                break
            label_len = data[offset]
            if name != b'':
                name += b'.'
                length += 1
            name += data[offset + 1:offset + 1 + label_len]
            offset += label_len + 1
            length += label_len

    return name, length


if __name__ == "__main__":
    data_hex = '4568011db27d00007a1172d5080808080a0000060035fbd301099b93000481800001000a0000000003617069056970696679036f72670000010001c00c0005000100000e02001c0c6e6167616e6f2d3139353939096865726f6b7573736c03636f6d00c02b0005000100000ad4002e13656c623039373330372d3933343932343933320975732d656173742d3103656c6209616d617a6f6e617773c042c053000100010000003a00041717e55ec053000100010000003a000417175399c053000100010000003a00041717f39ac053000100010000003a000436f393e2c053000100010000003a0004ae81c7e8c053000100010000003a000436e15c40c053000100010000003a000436ebbbf8c053000100010000003a00041717497c'
    data = bytearray.fromhex(data_hex)
    ans = detect_dns_answers_internal(data)
    print(ans)
