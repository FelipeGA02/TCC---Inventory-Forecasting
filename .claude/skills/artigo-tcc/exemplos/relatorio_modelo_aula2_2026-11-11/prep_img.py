import os, glob, fitz
from PIL import Image, ImageDraw, ImageFont, ImageFilter
T = os.path.dirname(os.path.abspath(__file__)); IMG = os.path.join(T, "img"); SH = os.path.join(T, "shots")
MEDIA = os.path.join(T, "base", "work", "word", "media")
REL = r"c:/Users/felip/OneDrive/Documentos/Estudos/TCC/Relatórios"
# 1. casos de uso: troca "(14 dias)" por "(2 semanas a 3 meses)"
im = Image.open(os.path.join(MEDIA, "image3.png")).convert("RGB")
px = im.load(); fill = px[1170, 70]
print("fill", fill)
d = ImageDraw.Draw(im)
d.rectangle([1000, 134, 1345, 180], fill=fill)
f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 38)
txt = "(2 semanas a 3 meses)"; w = d.textlength(txt, font=f)
d.text((1170 - w / 2, 137), txt, font=f, fill=(0, 0, 0))
im.save(os.path.join(IMG, "casos_uso.png"))
# 2. telas
def crop(src, dst, box=None):
    im = Image.open(os.path.join(SH, src)).convert("RGB")
    if box: im = im.crop(box)
    im.save(os.path.join(IMG, dst)); print(dst, im.size)
crop("f_login.png", "t_login.png", (330, 230, 1110, 670))
crop("f_inicio.png", "t_inicio.png")
crop("f_importar.png", "t_importar.png")
crop("f_conferencia.png", "t_conferencia.png", (0, 0, 1440, 740))
crop("f_conferir.png", "t_conferir.png")
crop("f_previsao.png", "t_previsao.png")
crop("f_previsao_produto.png", "t_previsao_produto.png", (0, 430, 1440, 1070))
crop("f_historico.png", "t_historico.png")
crop("f_relatorios.png", "t_relatorios.png")
crop("f_notificacoes.png", "t_notificacoes.png", (720, 0, 1440, 330))
crop("x06_relatorios.png", "t_uso.png", (240, 950, 1240, 1480))
r = fitz.open(os.path.join(SH, "relatorio_gerencial.pdf"))[0].get_pixmap(dpi=130)
r.save(os.path.join(IMG, "t_pdf.png"))
# 3. protótipo
for n, dst in [("Picture_2234.jpg", "p_inicio.jpg"), ("Picture_2343.jpg", "p_previsao.jpg"), ("Picture_2394.jpg", "p_simulador.jpg")]:
    Image.open(os.path.join(T, "proto", n)).convert("RGB").save(os.path.join(IMG, dst), quality=90)
# 4. atas
atas = [("01", "Documento_-_Registro_de_Reuniao_com_Entidade_01_assinado_assinado.pdf"),
        ("02", "Documento_-_Registro_de_Reuniao_com_Entidade_02_assinado_assinado.pdf")] + \
       [(f"{i:02d}", f"Documento - Registro de Reuniao com Entidade {i:02d}.pdf") for i in range(3, 9)]
for num, fn in atas:
    doc = fitz.open(os.path.join(REL, fn))
    for i, pg in enumerate(doc):
        pm = pg.get_pixmap(dpi=110)
        Image.frombytes("RGB", (pm.width, pm.height), pm.samples).save(os.path.join(IMG, f"ata{num}_{i+1}.jpg"), quality=82)
    print("ata", num, len(doc))
# 5. sistema da loja (anexo): borra o nome do usuário na barra de status da tela 39
im = Image.open(os.path.join(REL, "Sistema do cliente", "Captura de Tela (39).png")).convert("RGB")
box = (18, 652, 120, 666); im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(6)), box)
im.save(os.path.join(IMG, "erp_filtro.png"))
Image.open(os.path.join(REL, "Sistema do cliente", "Captura de Tela (37).png")).convert("RGB").save(os.path.join(IMG, "erp_relatorio.png"))
