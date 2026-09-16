# SPDX-FileCopyrightText: 2026 Valkyrie Profile 2 Translation Tools contributors
# SPDX-License-Identifier: GPL-3.0-only

"""Content-addressed store for compressor output."""

import hashlib
import os


def name(namespace, source, *parameters):
    """The store name for *source* compressed under these parameters."""
    digest = hashlib.sha256()
    digest.update(namespace.encode("ascii"))
    digest.update(b"\0")
    for parameter in parameters:
        digest.update(b"%d\0" % (parameter,))
    digest.update(bytes(source))
    return digest.hexdigest()


def path(store, key):
    return os.path.join(store, key[:2], key + ".slz")


def read(store, key):
    try:
        with open(path(store, key), "rb") as source:
            return source.read()
    except FileNotFoundError:
        return None


def write(store, key, blob):
    destination = path(store, key)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temporary = destination + ".tmp"
    with open(temporary, "wb") as output:
        output.write(blob)
    os.replace(temporary, destination)


def resolve(explicit, default, variable):
    if explicit is not None:
        return explicit
    setting = os.environ.get(variable)
    if setting == "0":
        return ""
    if setting:
        return setting
    return default


def cached(store, key, produce, seeds=()):
    """The stored blob for *key*, or *produce*'s, kept on the way out."""
    for seed in seeds:
        blob = read(seed, key)
        if blob is not None:
            return blob
    blob = read(store, key)
    if blob is None:
        blob = produce()
        write(store, key, blob)
    return blob
