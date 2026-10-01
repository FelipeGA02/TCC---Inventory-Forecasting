# -*- coding: utf-8 -*-
"""Desempacota e reempacota o DOCX (não há `zip` no Git Bash desta máquina).

    python docx_zip.py unpack "docs/project/TCC2 - Inicial.docx" <tmp>/work
    python docx_zip.py pack <tmp>/work <tmp>/draft.docx

O empacotamento grava [Content_Types].xml primeiro e _rels/ em seguida, como o Word espera.
Se o arquivo estiver aberto no Word, `unpack` ainda funciona (leitura), mas não sobrescreva o
original enquanto o Word estiver com ele aberto: gere em <tmp> e copie só no fim.
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")


def unpack(docx, dst):
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(docx) as z:
        for name in z.namelist():
            if name.endswith("/") or ".." in name or name.startswith("/"):
                continue
            z.extract(name, dst)
    print("ok", dst)


def pack(src, docx):
    files = []
    for dp, _, fn in os.walk(src):
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), src).replace(os.sep, "/"))
    files.sort(key=lambda x: (x != "[Content_Types].xml", not x.startswith("_rels"), x))
    if os.path.exists(docx):
        os.remove(docx)
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(src, f), f)
    print("ok", len(files), "arquivos,", os.path.getsize(docx), "bytes")


if __name__ == "__main__":
    cmd, a, b = sys.argv[1:4]
    {"unpack": unpack, "pack": pack}[cmd](a, b)
