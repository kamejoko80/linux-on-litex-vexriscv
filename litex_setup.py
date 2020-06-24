#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
from collections import OrderedDict

import urllib.request

current_path = os.path.dirname(os.path.realpath(__file__))

# Repositories -------------------------------------------------------------------------------------

# name,  (url, recursive clone, develop)
repos = [
    # HDL
    ("migen",        ("https://github.com/m-labs/",        True,  True, "19d5eae")),

    # LiteX SoC builder
    ("litex",        ("https://github.com/kamejoko80/",    True,  True, "fpga_lab")),

    # LiteX cores ecosystem
    ("liteeth",      ("https://github.com/enjoy-digital/", False, True, "705003e")),
    ("litedram",     ("https://github.com/enjoy-digital/", False, True, "48c2fc2")),
    ("litepcie",     ("https://github.com/enjoy-digital/", False, True, "586ef78")),
    ("litesata",     ("https://github.com/enjoy-digital/", False, True, "2e5c5b1")),
    ("litesdcard",   ("https://github.com/enjoy-digital/", False, True, "da5467b")),
    ("liteiclink",   ("https://github.com/enjoy-digital/", False, True, "6fdd020")),
    ("litevideo",    ("https://github.com/enjoy-digital/", False, True, "41f3014")),
    ("litescope",    ("https://github.com/enjoy-digital/", False, True, "54488c0")),
    ("litejesd204b", ("https://github.com/enjoy-digital/", False, True, "d4b4af9")),
    ("litespi",      ("https://github.com/litex-hub/",     False, True, "938ea0b")),

    # LiteX boards support
    ("litex-boards", ("https://github.com/litex-hub/",     False, True, "4ad6042")),
]
repos = OrderedDict(repos)

# RISC-V toolchain download ------------------------------------------------------------------------

def sifive_riscv_download():
    base_url  = "https://static.dev.sifive.com/dev-tools/"
    base_file = "riscv64-unknown-elf-gcc-8.3.0-2019.08.0-x86_64-"

    # Windows
    if (sys.platform.startswith("win") or sys.platform.startswith("cygwin")):
        end_file = "w64-mingw32.zip"
    # Linux
    elif sys.platform.startswith("linux"):
        end_file = "linux-ubuntu14.tar.gz"
    # Mac OS
    elif sys.platform.startswith("darwin"):
        end_file = "apple-darwin.tar.gz"
    else:
        raise NotImplementedError(sys.platform)
    fn = base_file + end_file

    if not os.path.exists(fn):
        url = base_url + fn
        print("Downloading", url, "to", fn)
        urllib.request.urlretrieve(url, fn)
    else:
        print("Using existing file", fn)

    print("Extracting", fn)
    shutil.unpack_archive(fn)

# Setup --------------------------------------------------------------------------------------------

if os.environ.get("TRAVIS", "") == "true":
    # Ignore `ssl.SSLCertVerificationError` on CI.
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

if len(sys.argv) < 2:
    print("Available commands:")
    print("- init")
    print("- install (add --user to install to user directory)")
    print("- update")
    print("- gcc")
    exit()

# Repositories cloning
if "init" in sys.argv[1:]:
    os.chdir(os.path.join(current_path))
    for name in repos.keys():
        if not os.path.exists(name):
            url, need_recursive, need_develop, revision = repos[name]
            # clone repo (recursive if needed)
            print("[cloning " + name + "]...")
            full_url = url + name
            opts = "--recursive" if need_recursive else ""
            subprocess.check_call(
                "git clone " + full_url + " " + opts,
                shell=True)
            subprocess.check_call(
                "git --git-dir=" + name + "/.git checkout " + revision,
                shell=True)

# Repositories installation
if "install" in sys.argv[1:]:
    for name in repos.keys():
        url, need_recursive, need_develop, revision = repos[name]
        # develop if needed
        print("[installing " + name + "]...")
        if need_develop:
            os.chdir(os.path.join(current_path, name))
            if "--user" in sys.argv[1:]:
                subprocess.check_call(
                    "python3 setup.py develop --user",
                    shell=True)
            else:
                subprocess.check_call(
                    "python3 setup.py develop",
                    shell=True)
            os.chdir(os.path.join(current_path))

    if "--user" in sys.argv[1:]:
        if ".local/bin" not in os.environ.get("PATH", ""):
            print("Make sure that ~/.local/bin is in your PATH")
            print("export PATH=$PATH:~/.local/bin")

# Repositories update
if "update" in sys.argv[1:]:
    for name in repos.keys():
        if not os.path.exists(name):
            raise Exception("{} not initialized, please (re)-run init and install first.".format(name))
        # update
        print("[updating " + name + "]...")
        os.chdir(os.path.join(current_path, name))
        subprocess.check_call(
            "git pull",
            shell=True)
        os.chdir(os.path.join(current_path))

# RISC-V GCC installation
if "gcc" in sys.argv[1:]:
    sifive_riscv_download()
    if "riscv64" not in os.environ.get("PATH", ""):
        print("Make sure that the downloaded RISC-V compiler is in your $PATH.")
        print("export PATH=$PATH:$(echo $PWD/riscv64-*/bin/)")
