import sys, os, pymupdf
from PIL import Image, ImageOps
src = r"C:/Users/felip/OneDrive/Documentos/Estudos/TCC/Relatórios/Documento - Registro de Reuniao com Entidade %s.pdf"
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
tot=0
for n in ["05","06","07","08"]:
    doc = pymupdf.open(src % n)
    for i, pg in enumerate(doc):
        pix = pg.get_pixmap(dpi=150)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        im = ImageOps.expand(im, border=2, fill=(128,128,128))
        im = im.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
        p=f"{out}/ata{n}_p{i+1}.png"; im.save(p, optimize=True); tot+=os.path.getsize(p)
        print(n, i+1, im.size, os.path.getsize(p)//1024, "KB")
print("total", tot//1024, "KB")
