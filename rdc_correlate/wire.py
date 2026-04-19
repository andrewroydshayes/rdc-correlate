"""TLV wire-protocol parser for the Kohler RDC. Same format as rdc-proxy/wire.py
— duplicated here so rdc-correlate has no private-repo dependency."""

import struct


def parse_tlv_records(buf):
    """Yield (ts_offset_byte, param_id, vlen, value_bytes) records from a TLV buffer.

    We return the byte offset within `buf` where each frame starts so the
    caller can map it back to a per-byte timestamp (needed for stream
    reassembly where one TCP segment can contain fragments of multiple frames).
    """
    i, N = 0, len(buf)
    while i + 12 <= N:
        lf = struct.unpack_from("<I", buf, i)[0]
        ver = struct.unpack_from("<H", buf, i + 4)[0]
        if ver != 2 or lf < 14 or lf > 4096 or i + lf > N:
            i += 1
            continue
        count = struct.unpack_from("<H", buf, i + 6)[0]
        body = buf[i + 12: i + lf]
        off = 0
        ok = True
        recs = []
        for _ in range(count):
            if off + 8 > len(body):
                ok = False
                break
            rid = struct.unpack_from("<H", body, off)[0]
            vlen = struct.unpack_from("<I", body, off + 4)[0]
            if off + 8 + vlen + 2 > len(body):
                ok = False
                break
            val = body[off + 8: off + 8 + vlen]
            off += 8 + vlen + 2
            recs.append((rid, vlen, val))
        if not ok or off != len(body):
            i += 1
            continue
        for rid, vlen, val in recs:
            yield i, rid, vlen, val
        i += lf


def parse_pcap_payloads(pcap_path):
    """Use tshark to extract the client-to-cloud TLV stream from a pcap file.

    Yields (wall_ts_s, param_id, vlen, value_bytes). Relies on tshark CLI
    (apt install tshark).
    """
    import subprocess
    from collections import defaultdict

    try:
        out = subprocess.check_output(
            [
                "tshark", "-r", pcap_path,
                "-Y", "ip.src==192.168.4.50 and tcp.dstport==5253 and tcp.len>0",
                "-T", "fields",
                "-e", "frame.time_epoch", "-e", "tcp.stream",
                "-e", "tcp.seq", "-e", "tcp.payload",
                "-o", "tcp.desegment_tcp_streams:TRUE",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return

    streams = defaultdict(list)
    for line in out.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) < 4 or not parts[3]:
            continue
        try:
            t, sid, seq, hx = float(parts[0]), int(parts[1]), int(parts[2]), parts[3]
            payload = bytes.fromhex(hx)
        except (ValueError, IndexError):
            continue
        streams[sid].append((seq, t, payload))

    for sid, entries in streams.items():
        entries.sort(key=lambda x: x[0])
        byte_ts = []
        chunks = []
        for seq, t, payload in entries:
            chunks.append(payload)
            byte_ts.extend([t] * len(payload))
        buf = b"".join(chunks)
        for frame_off, rid, vlen, val in parse_tlv_records(buf):
            ts = byte_ts[frame_off] if frame_off < len(byte_ts) else byte_ts[-1] if byte_ts else 0.0
            yield ts, rid, vlen, val
