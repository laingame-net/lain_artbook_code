#!/usr/bin/env python
import binhex_patched


def encode(filename_in, filename_out):
    binhex_patched.binhex(filename_in, filename_out)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("in_file")
    p.add_argument("out_file")
    args = p.parse_args()

    encode(args.in_file, args.out_file)

