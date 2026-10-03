"""Minimal MP3 stitching for generated audio sessions (no ffmpeg needed).

Guided sessions need long silences ("breathe in... [10 seconds]"), longer
than a text-to-speech pause tag allows. So `generate_audio` asks ElevenLabs
for each spoken segment separately and joins them here, with real silent
MP3 frames in between.

How:
  * ID3 tags and Xing/Info/VBRI header frames are dropped from every segment,
    so players don't read one segment's length as the whole file's.
  * A silent frame is a valid MPEG-1 Layer III frame whose side info and
    main data are all zeros (global gain 0, nothing to decode). It's built
    with the same sample rate, channel mode and bitrate as the speech
    frames, so the finished file stays constant-bitrate and players
    estimate its length and seek accurately.

Only MPEG-1 Layer III is supported (32/44.1/48 kHz), which covers
ElevenLabs' mp3_44100_* output formats.
"""
BITRATES_KBPS = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
SAMPLE_RATES = [44100, 48000, 32000]
SAMPLES_PER_FRAME = 1152


class MP3Error(ValueError):
    pass


def _strip_id3v2(data):
    if data[:3] == b'ID3' and len(data) >= 10:
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        footer = 10 if data[5] & 0x10 else 0
        return data[10 + size + footer:]
    return data


def _strip_id3v1(data):
    if len(data) >= 128 and data[-128:-125] == b'TAG':
        return data[:-128]
    return data


def parse_header(h):
    """Decode a 4-byte frame header. Returns a dict, or None if not a valid
    MPEG-1 Layer III header."""
    if len(h) < 4 or h[0] != 0xFF or (h[1] & 0xE0) != 0xE0:
        return None
    version = (h[1] >> 3) & 0x3
    layer = (h[1] >> 1) & 0x3
    if version != 0x3 or layer != 0x1:  # MPEG-1, Layer III only
        return None
    br_index = (h[2] >> 4) & 0xF
    sr_index = (h[2] >> 2) & 0x3
    if br_index in (0, 15) or sr_index == 3:
        return None
    bitrate = BITRATES_KBPS[br_index] * 1000
    sample_rate = SAMPLE_RATES[sr_index]
    padding = (h[2] >> 1) & 0x1
    channel_mode = (h[3] >> 6) & 0x3
    has_crc = not (h[1] & 0x1)
    return {
        'bitrate': bitrate, 'br_index': br_index,
        'sample_rate': sample_rate, 'sr_index': sr_index,
        'padding': padding, 'channel_mode': channel_mode,
        'mono': channel_mode == 0x3, 'has_crc': has_crc,
        'length': 144 * bitrate // sample_rate + padding,
    }


def _side_info_len(info):
    return 17 if info['mono'] else 32


def _is_info_frame(frame, info):
    """Xing/Info (LAME) or VBRI header frames carry length metadata, not audio."""
    start = 4 + (2 if info['has_crc'] else 0) + _side_info_len(info)
    return frame[start:start + 4] in (b'Xing', b'Info') or frame[36:40] == b'VBRI'


def audio_frames(data):
    """Split MP3 bytes into (header_info, frame_bytes) for real audio frames."""
    data = _strip_id3v1(_strip_id3v2(data))
    frames, i, n = [], 0, len(data)
    while i + 4 <= n:
        info = parse_header(data[i:i + 4])
        if info is None or info['length'] < 4:
            i += 1  # resync past junk
            continue
        frame = data[i:i + info['length']]
        if len(frame) < info['length']:
            break  # truncated final frame
        if not _is_info_frame(frame, info):
            frames.append((info, frame))
        i += info['length']
    return frames


def silent_frame(template):
    """One silent frame matching `template` (a parse_header dict), no padding."""
    b2 = (template['br_index'] << 4) | (template['sr_index'] << 2)  # padding 0, private 0
    b3 = template['channel_mode'] << 6
    header = bytes([0xFF, 0xFB, b2, b3])  # MPEG-1, Layer III, no CRC
    length = 144 * template['bitrate'] // template['sample_rate']
    return header + bytes(length - 4)


def silence(template, seconds):
    frame_seconds = SAMPLES_PER_FRAME / template['sample_rate']
    count = max(0, round(seconds / frame_seconds))
    return silent_frame(template) * count


def stitch(parts):
    """Join a list of parts into one MP3.

    Each part is either MP3 bytes (a spoken segment) or a number of seconds
    of silence. Returns (mp3_bytes, duration_seconds).
    """
    template = None
    for part in parts:
        if isinstance(part, (bytes, bytearray)):
            frames = audio_frames(part)
            if frames:
                template = frames[0][0]
                break
    if template is None:
        raise MP3Error('No MPEG-1 Layer III audio frames found in any segment')

    out = bytearray()
    frame_count = 0
    for part in parts:
        if isinstance(part, (bytes, bytearray)):
            for info, frame in audio_frames(part):
                if (info['sample_rate'], info['channel_mode']) != (
                        template['sample_rate'], template['channel_mode']):
                    raise MP3Error('Segments use different sample rates or channel modes')
                out += frame
                frame_count += 1
        else:
            chunk = silence(template, float(part))
            out += chunk
            frame_count += len(chunk) // len(silent_frame(template))
    duration = frame_count * SAMPLES_PER_FRAME / template['sample_rate']
    return bytes(out), duration
