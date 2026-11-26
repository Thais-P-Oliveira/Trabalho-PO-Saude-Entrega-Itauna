"""Gera figuras a partir dos resultados salvos, sem alterar o texto do artigo."""
from pathlib import Path as _Caminho
import sys as _sistema
_sistema.path.insert(0, str(_Caminho(__file__).resolve().parents[1]))
from caminhos import RAIZ
import csv
import argparse
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PLANO = RAIZ / 'resultados' / 'atual' / 'plano'
FIG = RAIZ / 'resultados' / 'atual' / 'figuras_artigo'
PNG = RAIZ / 'imagens'
from caminhos import CACHE
os.environ.setdefault('MPLCONFIGDIR', str(CACHE / 'matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

AZUL, LARANJA, CINZA = '#255a7b', '#CC6688', '#d7dbdf'
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#eeeeee', 'grid.linewidth': 0.8, 'axes.axisbelow': True})


from tabelas import ler_tabela

def br(v, casas=1):
    return f'{v:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def salvar(fig, nome):
    PNG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f'{nome}.pdf', bbox_inches='tight')
    fig.savefig(PNG / f'{nome}.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def ler(p):
    return ler_tabela(p, sep=';', encoding='utf-8-sig')


def distancias(comp):
    amb = comp[comp.tipo == 'AMB']
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    vias = [25, 50, 75]
    for k, (cen, cor, rot) in enumerate([('unico', AZUL, 'Principal: um nível'), ('multiplo', LARANJA, 'Complementar: múltiplos')]):
        v = [amb[(amb.cenario == cen) & (amb.via_percentual == p)].distancia_media_por_percurso.iloc[0] for p in vias]
        x = [i + (k - 0.5) * 0.34 for i in range(3)]
        ax.bar(x, v, width=0.34, color=cor, label=rot)
        for xi, vi in zip(x, v):
            ax.text(xi, vi + 0.06, br(vi, 2), ha='center', va='bottom', fontsize=8.5)
    ax.set_xticks(range(3), [f'{p}%' for p in vias])
    ax.set_xlabel('Parcela da demanda terciária via secundária')
    ax.set_ylabel('Distância média por percurso (km)')
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
    ax.grid(axis='x', visible=False)
    ax.legend(frameon=False, ncol=2, loc='upper center')
    salvar(fig, 'distancias')


def percursos(comp):
    r = comp[(comp.tipo == 'AMB') & (comp.cenario == 'unico') & (comp.via_percentual == 50)].iloc[0]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.text(1, 3, 'UBS\nplano fixo', ha='center', va='center', fontsize=11)
    alvos = [(5, 'Termina na secundária\n' + br(r.termina2, 0) + ' eventos'),
             (3, 'Direto à terciária\n' + br(r.direto3, 0) + ' eventos'),
             (1, 'Secundária e terciária\n' + br(r.via23, 0) + ' percursos alocados\n' + br(2 * r.via23, 0) + ' procedimentos alocados')]
    for y, txt in alvos:
        ax.annotate('', xy=(5.4, y + 0.1), xytext=(2, 3), arrowprops=dict(arrowstyle='->', color=AZUL, lw=2))
        ax.text(5.8, y + 0.1, txt, va='center', fontsize=11)
    salvar(fig, 'percursos')


def capacidades():
    c = ler(PLANO / 'unico_via_50/capacidades.csv')
    c = c[c.limite_pico_anualizado > 0].copy()
    # Ordem importa: o CEO II tambem comeca com "CENTRO DE ESPEC".
    nomes = [('CENTRO DE ESPECIALIDADES ODONTOLOGICAS', 'CEO II'), ('CENTRO DE ESPEC', 'Centro de especialidades'),
             ('APAE', 'APAE'), ('CAPS 2', 'CAPS 2'), ('CAPS AD', 'CAPS AD'), ('HOSPITAL', 'Hospital')]
    c['rotulo'] = [next(v for k, v in nomes if n.upper().startswith(k)) for n in c.nome]
    c['uso'] = c.ambulatorial_total / c.limite_pico_anualizado * 100
    c[['cnes','nome','ambulatorial_total','limite_pico_anualizado','uso']].to_csv(FIG/'conferencia_capacidades.csv',sep=';',index=False,encoding='utf-8-sig')
    c = c.sort_values('rotulo', ascending=False)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    fig.subplots_adjust(left=.30,right=.96,bottom=.17,top=.98)
    cores = [LARANJA if u >= 99.95 else AZUL for u in c.uso]
    y = list(range(len(c)))
    ax.barh(y, c.uso, color=cores)
    ax.set_yticks(y, c.rotulo)
    for yi, u in zip(y, c.uso):
        ax.text(u + 1, yi, br(u) + '%', va='center', fontsize=9.5)
    hospital=c[c.cnes.astype(str)=='2105780']
    if len(hospital):
        h=hospital.iloc[0]
        if 'limite_alta' not in c:raise ValueError('Audite o plano para exportar limite_alta antes de gerar a figura.')
        if h.limite_alta>0:
            yy=len(c)
            uso=100*h.ambulatorial_alta/h.limite_alta
            ax.barh(yy,uso,color=LARANJA)
            ax.text(uso+1,yy,br(uso)+'%',va='center',fontsize=9.5)
            ax.set_yticks(list(y)+[yy],list(c.rotulo)+['Hospital: limite de alta'])
    ax.set_xlim(0, 114)
    ax.tick_params(labelsize=9.5)
    ax.set_xlabel('Uso do limite ambulatorial (%)',fontsize=10)
    ax.grid(axis='y', visible=False)
    salvar(fig, 'capacidades')


def main():
    global PLANO,FIG,PNG
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plano',type=Path,default=PLANO)
    ap.add_argument('--figuras',type=Path,default=FIG)
    ap.add_argument('--imagens',type=Path,default=PNG)
    args=ap.parse_args()
    PLANO,FIG,PNG=args.plano.resolve(),args.figuras.resolve(),args.imagens.resolve()
    FIG.mkdir(parents=True,exist_ok=True);PNG.mkdir(parents=True,exist_ok=True)
    comp = ler(PLANO / 'comparacao_completa.csv')
    distancias(comp)
    percursos(comp)
    capacidades()
    print('Figuras salvas em', FIG)


if __name__ == '__main__':
    main()
