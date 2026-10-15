#!/usr/bin/env python3
"""Renderiza as telas de um post do estúdio Conta Leve em JPG (1080 px de largura).

Uso:
  python3 tools/render.py --studio estudio.html --post post.json --blobs pasta_blobs --out pasta_saida

- estudio.html: o HTML publicado do estúdio (Artifact read).
- post.json: o documento do post (coleção posts), com "slides".
- pasta_blobs: arquivos das fotos usadas nas telas, cada um com o nome igual ao id do asset.
- Saída: 1.jpg, 2.jpg, ... na pasta de saída. Imprime a lista de arquivos.
"""
import argparse, asyncio, base64, functools, http.server, json, os, shutil, socketserver, tempfile, threading

from playwright.async_api import async_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))


def montar(studio, post, blobs, tmp):
    os.makedirs(os.path.join(tmp, "_blob"), exist_ok=True)
    if blobs and os.path.isdir(blobs):
        for f in os.listdir(blobs):
            shutil.copy(os.path.join(blobs, f), os.path.join(tmp, "_blob", f))
    shutil.copytree(os.path.join(AQUI, "fonts"), os.path.join(tmp, "fonts"))
    shutil.copy(os.path.join(AQUI, "mock.js"), os.path.join(tmp, "mock.js"))
    head = open(os.path.join(AQUI, "head.html"), encoding="utf-8").read()
    seed = {"posts": {"render": post}, "fotos": {}}
    html = head + "<script>window.__SEED=" + json.dumps(seed, ensure_ascii=False) + "</script><script src=\"mock.js\"></script>" + open(studio, encoding="utf-8").read()
    open(os.path.join(tmp, "index.html"), "w", encoding="utf-8").write(html)


async def renderizar(tmp, out, porta):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 900})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        await pg.goto(f"http://127.0.0.1:{porta}/index.html")
        await pg.wait_for_function("typeof S!=='undefined' && S.posts && S.posts.some(x=>x.id==='render')", timeout=20000)
        js = """()=>{const p=S.posts.find(x=>x.id==='render');return p.slides.map((s,i)=>{const c=document.createElement('canvas');drawSlide(c,p,i,1);return c.toDataURL('image/jpeg',.93)})}"""
        await pg.evaluate(js)
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(3000)  # fotos carregando
        imgs = await pg.evaluate(js)
        await b.close()
    os.makedirs(out, exist_ok=True)
    arqs = []
    for i, s in enumerate(imgs):
        f = os.path.join(out, f"{i + 1}.jpg")
        open(f, "wb").write(base64.b64decode(s.split(",", 1)[1]))
        arqs.append(f)
    return arqs, erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--studio", required=True)
    ap.add_argument("--post", required=True)
    ap.add_argument("--blobs", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    post = json.load(open(a.post, encoding="utf-8"))
    post = post.get("data", post) if isinstance(post.get("data"), dict) else post
    tmp = tempfile.mkdtemp(prefix="cl_render_")
    montar(a.studio, post, a.blobs, tmp)
    class Quieto(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass
    handler = functools.partial(Quieto, directory=tmp)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        arqs, erros = asyncio.run(renderizar(tmp, a.out, porta))
    finally:
        srv.shutdown()
    print(json.dumps({"arquivos": arqs, "erros": erros}, ensure_ascii=False))


if __name__ == "__main__":
    main()
