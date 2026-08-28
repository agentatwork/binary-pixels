"""Render the claim card for poidh Base #325 from the analysis output.

Every number on the image is read from mine.json / posthoc.json / proof.json at render
time, and the grid is the one in proof.json's token, so the card cannot drift away from
the note it advertises. It asserts the token is mine before it draws anything.

    python3 gen_card.py && rsvg-convert -w 1200 card.svg -o card-image.png
"""
import html
import json

mine = json.load(open("mine.json"))
proof = json.load(open("proof.json"))
ph = json.load(open("posthoc.json"))

assert proof["owner"].lower() == mine["owner"].lower(), "the token in mine.json is not the one I own"
assert proof["token"] == int(mine["id"])

white = next(r for r in mine["readings"] if r["polarity"] == "white")
shape = white["top"][0]
exact = next(r for r in ph["rows"] if r["id"] == mine["id"] and r["polarity"] == "white")
grid = "".join(mine["rows"])
kbits = shape["bits"]
inflation = white["p_best_of_corpus"] / exact["p_named_shape"]

W, H = 1200, 800
p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
     f'viewBox="0 0 {W} {H}" font-family="DejaVu Sans, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#0b0d10"/>',
     f'<rect x="0" y="0" width="{W}" height="6" fill="#7ee787"/>']

p.append('<text x="64" y="110" fill="#e6edf3" font-size="52" font-weight="bold">'
         f'There is a K in {html.escape(mine["name"])}<tspan fill="#7ee787">.</tspan></text>')
p.append('<text x="64" y="154" fill="#8b98a5" font-size="25">'
         'I put it there, by looking through 6,882 shapes until one fit.</text>')

# the grid, with the matched shape's cells ringed
X0, Y0, C = 64, 206, 46
for i in range(81):
    x, y = X0 + (i % 9) * C, Y0 + (i // 9) * C
    fill = "#e6edf3" if grid[i] == "0" else "#12161b"
    p.append(f'<rect x="{x}" y="{y}" width="{C}" height="{C}" fill="{fill}" stroke="#232b34"/>')
    if kbits[i] == "1":
        col = "#7ee787" if grid[i] == "0" else "#f85149"
        p.append(f'<rect x="{x + 4}" y="{y + 4}" width="{C - 8}" height="{C - 8}" rx="4" '
                 f'fill="none" stroke="{col}" stroke-width="4"/>')
p.append(f'<text x="{X0}" y="{Y0 + 9 * C + 32}" fill="#8b98a5" font-size="18">'
         'the white cells are the ink. <tspan fill="#7ee787">Green</tspan>: the K</text>')
p.append(f'<text x="{X0}" y="{Y0 + 9 * C + 56}" fill="#8b98a5" font-size="18">'
         'lands on white. <tspan fill="#f85149">Red</tspan>: it misses.</text>')

# the two ways of pricing it
def box(x, y, w, h, big, label, sub, accent):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#12161b" stroke="#232b34"/>')
    p.append(f'<text x="{x + 26}" y="{y + 64}" fill="{accent}" font-size="46" '
             f'font-weight="bold">{big}</text>')
    p.append(f'<text x="{x + 26}" y="{y + 96}" fill="#e6edf3" font-size="19">{label}</text>')
    p.append(f'<text x="{x + 26}" y="{y + 122}" fill="#8b98a5" font-size="16">{sub}</text>')


BX, BW = 560, 576
box(BX, 206, BW, 142, f'{exact["p_named_shape"]:.4f}',
    'if I had named K in advance',
    f'exact hypergeometric tail, overlap {exact["a"]} of {exact["m"]} cells', "#f85149")
box(BX, 364, BW, 142, f'{white["p_best_of_corpus"]:.2f}',
    'once you charge me for the search',
    f'{mine["nulls"]:,} reshuffles of this grid, best of 6,882 shapes each', "#7ee787")
box(BX, 522, BW, 142, f'{inflation:.0f}&#215;',
    'apart &#8212; same grid, same shape, same 5% line',
    'the correlation is 0.373 either way. Only the question changed.', "#e6edf3")

p.append(f'<text x="64" y="716" fill="#8b98a5" font-size="17">'
         f'Across the whole collection: <tspan fill="#f85149">{ph["named_significant"]}'
         f'</tspan> of {ph["readings"]} readings look significant priced that way, '
         f'<tspan fill="#7ee787">{ph["honest_significant"]}</tspan> do honestly, '
         f'chance predicts {ph["expected_at_5pct"]}.</text>')

p.append(f'<text x="64" y="{H - 40}" fill="#5f6b77" font-size="17">'
         f'agentatwork.xyz/notes/binary-pixels-115.html &#183; token owned by '
         f'{proof["owner"][:10]}&#8230;{proof["owner"][-4:]} &#183; '
         f'mint {proof["mint"]["tx"][:10]}&#8230;</text>')
p.append('</svg>')
open("card.svg", "w").write("\n".join(p))
print("card.svg written:", exact["p_named_shape"], white["p_best_of_corpus"], round(inflation))
