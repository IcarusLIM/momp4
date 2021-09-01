from datetime import datetime

FTYP = "ftyp".encode("utf-8")
MOOV = "moov".encode("utf-8")
FREE = "free".encode("utf-8")
MDAT = "mdat".encode("utf-8")

MVHD = "mvhd".encode("utf-8")

BOXSIZE_LEN = 4
BOXTYPE_LEN = 4
LARGESIZE_LEN = 8

SUGGEST_HEADER_LEN = 1024

has_child = {MOOV}
should_load_body = {FTYP, MVHD}


def parse_int(bytes):
    return int.from_bytes(bytes, byteorder="big")


class _Box:
    def __init__(self, box_type, start, header_len, box_len) -> None:
        self.box_type = box_type
        self.start = start
        self.header_len = header_len
        self.data_offset = start + header_len
        self.box_len = box_len
        self.is_intact = False
        self.data = None
        self.children = []

    def next_offset(self):
        return self.start + self.box_len


class MP4Stream:

    box_tree = []

    store_bytes = b""
    store_offset = 0
    store_not_change = 0

    def feed(self, bytes_steam, offset=-1):
        # no offset or offset continuous, just append
        if offset < 0 or self.store_offset + len(self.store_bytes) == offset:
            self.store_bytes += bytes_steam
            self._endless_loop_check(len(bytes_steam) > 0)
            return self._process_stream()
        else:
            boxs = self._find_box(offset)
            if boxs:
                self._endless_loop_check(self.store_bytes != bytes_steam)
                self.store_bytes = bytes_steam
                self.store_offset = offset
                return self._process_stream(boxs)
            else:
                return len(self.store_bytes) + self.store_offset, SUGGEST_HEADER_LEN

    # returns
    # None: offset invalid
    # [box1, box2]: box2, child of box1, is start at the offset
    # [box1, None]: there is a child of box1 start at the offset, which has not init yet
    def _find_box(self, offset):
        if len(self.box_tree) == 0:
            return [None] if offset == 0 else None
        is_valid_start = False
        # check start
        for box1 in self.box_tree:
            if box1.start == offset:
                return [box1]
            if is_valid_start:
                continue
            if box1.start + box1.box_len == offset:
                is_valid_start = True
                continue

            if box1.box_type == MOOV:
                if len(box1.children) == 0:
                    return [box1, None] if offset == box1.data_offset else None

                is_valid_start2 = False
                for box2 in box1.children:
                    if box2.start == offset:
                        return [box1, box2]
                    if is_valid_start2:
                        continue
                    if box2.start + box2.box_len == offset:
                        is_valid_start2 = True
                if is_valid_start2:
                    return [box1, None]
            else:
                # other case, there is no need to check child box
                continue
        return [None] if is_valid_start else None

    def _process_stream(self, boxs=None):
        if not boxs:
            boxs = self._find_box(self.store_offset)
        if not boxs:
            raise Exception("oops, strange!!!")
        while True:
            box = boxs[-1]
            store_end = self._store_range()[1]
            if box is None:
                box = self._make_box(self.store_offset)
                if box is None:
                    return store_end, SUGGEST_HEADER_LEN
                if len(boxs) > 1:
                    boxs[-2].children.append(box)
                else:
                    self.box_tree.append(box)
                boxs[-1] = box
            if box.box_type in has_child and box.data_offset < box.next_offset():
                self.store_offset = box.data_offset
                self.store_bytes = self.store_bytes[box.header_len :]
                boxs.append(None)
                continue
            if box.box_type in should_load_body:
                # ensure store intact
                if box.next_offset() > store_end:
                    return store_end, box.next_offset() + SUGGEST_HEADER_LEN - store_end
                # extract box content
                if box.box_type == FTYP:
                    self._load_ftyp(box)
                elif box.box_type == MVHD:
                    self._load_mvhd(box)
                box.is_intact = True
            # set store for next box
            if store_end < box.next_offset():
                self.store_bytes = b""
                self.store_offset = box.next_offset()
            else:
                self.store_bytes = self.store_bytes[
                    box.next_offset() - self.store_offset :
                ]
                self.store_offset = box.next_offset()

            # remove finish box
            while boxs[-1] is not None:
                if len(boxs) <= 1:
                    boxs[0] = None
                elif boxs[-1].next_offset() == boxs[-2].next_offset():
                    boxs = boxs[:-1]
                else:
                    boxs[-1] = None

    def _make_box(self, offset):
        relative_offset = offset - self.store_offset
        header_len = BOXSIZE_LEN + BOXTYPE_LEN
        if len(self.store_bytes) < relative_offset + header_len:
            return None
        box_size = self._store_bytes_toint(
            relative_offset, relative_offset + BOXSIZE_LEN
        )
        box_type = self.store_bytes[
            relative_offset + BOXSIZE_LEN : relative_offset + BOXSIZE_LEN + BOXTYPE_LEN
        ]
        if box_size == 0:
            header_len += LARGESIZE_LEN
            if len(self.store_bytes) < relative_offset + header_len:
                return None
            box_size = self._store_bytes_toint(
                relative_offset + header_len,
                relative_offset + header_len + LARGESIZE_LEN,
            )
        return _Box(box_type, offset, header_len, box_size)

    def _load_ftyp(self, box):
        relative_offset = box.start - self.store_offset
        data_bytes = self.store_bytes[
            relative_offset + box.header_len : box.next_offset()
        ]
        data = {
            "major_band": data_bytes[0:4].decode("utf-8"),
            "minor_version": parse_int(data_bytes[4:8]),
        }
        compatible_brands = []
        for i in range((len(data_bytes) - 8) // 4):
            compatible_brands.append(data_bytes[8 + 4 * i : 12 + 4 * i].decode("utf-8"))
        data["compatible_brands"] = compatible_brands
        box.data = data

    def _load_mvhd(self, box):
        relative_offset = box.start - self.store_offset
        data_bytes = self.store_bytes[
            relative_offset + box.header_len : box.next_offset()
        ]
        p = 0
        data = {}
        for (key, item_len) in [
            ("version", 1),
            ("flags", 3),
            ("creation_time", 4),
            ("modification_time", 4),
            ("time_scale", 4),
            ("duration", 4),
            ("rate", 4),
            ("volume", 2),
        ]:
            data[key] = data_bytes[p : p + item_len]
            p += item_len
        data["version"] = parse_int(data["version"])
        data["creation_time"] = datetime.fromtimestamp(parse_int(data["creation_time"]))
        data["modification_time"] = datetime.fromtimestamp(
            parse_int(data["modification_time"])
        )
        data["time_scale"] = parse_int(data["time_scale"])
        data["duration"] = parse_int(data["duration"])
        data["length"] = data["duration"] / data["time_scale"]
        rate_hex = data["rate"].hex()
        data["rate"] = float.fromhex(rate_hex[:4] + "." + rate_hex[-4:])
        volume_hex = data["volume"].hex()
        data["volume"] = float.fromhex(volume_hex[:2] + "." + volume_hex[-2:])
        box.data = data

    def _store_bytes_toint(self, start, end):
        return int.from_bytes(
            self.store_bytes[start:end],
            byteorder="big",
        )

    def _store_range(self):
        return [self.store_offset, self.store_offset + len(self.store_bytes)]

    def _endless_loop_check(self, changed):
        if changed:
            self.store_not_change = 0
        else:
            self.store_not_change += 1
        if self.store_not_change > 10:
            raise Exception("dead loop")

    def get_meta(self):
        res = {}

        def f(box):
            if box.box_type == FTYP:
                res["ftyp"] = box.data
            elif box.box_type == MVHD:
                res["meta"] = box.data

        self._traverse_box(f)
        return res, "ftyp" in res and "meta" in res

    def _traverse_box(self, f, boxs=None):
        if boxs is None:
            boxs = self.box_tree
        for box in boxs:
            f(box)
            self._traverse_box(f, boxs=box.children)
