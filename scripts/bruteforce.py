#!/usr/bin/env python3
import io
import os
import itertools
import shutil
from datetime import datetime, timedelta

from functools import reduce
from typing import List, Tuple, Generator
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
import binhex

__version__ = "1.0"
__author__ = "h5vx"


def parse_config(filename):
    """
    Parse bruteforce config
    Config will be in form [(line, row, charset), (line, row, charset), ...]
    Example: [(28, 44, "1l`"), (35, 4, "1liI")]
    """
    result = []

    f = open(filename)

    for line, i in zip(f.readlines(), itertools.count(start=1)):
        line: str = line.strip()

        if not line or line.startswith("#"):
            continue

        try:
            pos, charset = map(str.strip, line.split("-", maxsplit=1))
            ln, row = map(int, pos.split(":", maxsplit=1))
        except ValueError:
            print(f"{filename}:{i} line is not valid; ignored", file=os.sys.stderr)

        if charset == "?":
            charset = (
                "!\"#$%&'()*+,-012345689@ABCDEFGHIJKLMNPQRSTUVXYZ[`abcdefhijklmpqr"
            )

        result.append((ln, row, charset.encode("ascii")))

    f.close()
    return result


def file_mutator(
    buf: io.BytesIO, config: List[Tuple]
) -> Generator[Tuple[int], None, None]:
    """
    Core of bruteforcer. It will mutate buffer :buf: following rules in :config:
    It's a generator. Each iteration causes buffer to unique mutation, and
    after each iteration buffer position will be reset to zero
    This generator yields "state" - a list of config charsets positions
    """
    # => Build lines position map
    line_pos = {1: 0}
    bs = buf.read()
    buf.seek(0)

    for ln in itertools.count(start=2):
        prev_pos = line_pos[ln - 1]

        try:
            pos = bs.index(b"\n", prev_pos + 1)
        except ValueError:
            break

        line_pos[ln] = pos

    # => Make generator of all possible charset combinations
    charsets = (c[2] for c in config)
    charsets_len = (len(c) for c in charsets)
    states = itertools.product(*(range(l) for l in charsets_len))

    # => Mutate the buffer with all possible combinations
    view = buf.getbuffer()  # We can mutate buffer through that view!

    for state in states:
        for config_entry, i in zip(config, itertools.count()):
            ln, row, charset = config_entry
            char = charset[state[i]]
            pos = line_pos[ln] + row

            view[pos] = char

        yield state  # Now let them use buffer
        buf.seek(0)  # Buffer should be usable again


def count_total_combinations(config):
    """
    Count number of all possible combinations from config
    """
    return reduce(int.__mul__, (len(c[2]) for c in config))


def run_bruteforce(binhex_filename, config_filename):
    config = parse_config(config_filename)
    total = count_total_combinations(config)
    start_time = last_report_time = datetime.now()

    with open(binhex_filename, "rb") as f:
        buf = io.BytesIO(f.read())

    def report_progress(progress):
        termsize = shutil.get_terminal_size((80, 20))
        now_time = datetime.now()
        worktime = now_time - start_time

        done_percent = int(progress / total * 100)
        tps = progress / (worktime.total_seconds() or 1)
        eta = timedelta(seconds=(total - progress) / tps)

        cut_ms = lambda td: str(td).split(".", 1)[0]

        line = (
            f"{progress} of {total} :: {tps:.2f}/s :: {cut_ms(worktime)}"
            f":: ETA {cut_ms(eta)} :: {done_percent}%"
        )
        if len(line) < termsize.columns:
            line += " " * (termsize.columns - len(line))

        print("\r" + line, end="", flush=True)

    report_progress(1)

    for state, n in zip(file_mutator(buf, config), itertools.count(start=1)):
        hexbin = binhex.HexBin(buf)
        data = hexbin.read(128000)  # TODO: Remove 128k limit

        try:
            hexbin.close_data()
        except binhex.Error:
            pass
        else:  # No exceptions occured, that means CRC is correct
            print(f"\nSuccess! State: {state}")

            for entry, i in zip(config, itertools.count()):
                ln, row, charset = entry
                char = chr(charset[state[i]])
                print(f"{ln}:{row} - {char}", end="\t")

                if i != 0 and (i + 1) % 4 == 0:
                    print("")

            if (i + 1) % 4:
                print("")

            fname = hexbin.FName.decode("ascii")

            with open(f"bruteforce_{n}_{fname}.hqx", "wb") as f_result:
                buf.seek(0)
                f_result.write(buf.read())
                print(f"Result hqx written to {f_result.name}")

            with open(f"bruteforce_{n}_{fname}", "wb") as f_bin:
                f_bin.write(data)
                print(f"Decoded binary written to {f_bin.name}")

        if n % 512 == 0 and (datetime.now() - last_report_time).seconds >= 1:
            report_progress(n)
            last_report_time = datetime.now()

    report_progress(n)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Bruteforce hqx until CRC checksum is correct"
    )
    p.add_argument("hqx_file", help="Initial bruteforce hqx")
    p.add_argument("conf_file", help="Bruteforce config")
    args = p.parse_args()

    try:
        run_bruteforce(args.hqx_file, args.conf_file)
    except KeyboardInterrupt:
        exit(1)
