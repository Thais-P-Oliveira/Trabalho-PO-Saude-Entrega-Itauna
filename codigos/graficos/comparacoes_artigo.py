"""Compara investimento, pressao por proximidade e ocupacao das equipes fixas."""
from pathlib import Path
import sys
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from caminhos import RAIZ
from paleta import EXISTENTE, URBANA, RURAL
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd
from geografia import limite_municipal, projetar
from graficos_demanda import NOVAS, nome

SAIDA = RAIZ/'imagens/comparacoes_artigo'
FIGURAS = RAIZ/'documentacao/artigo/figuras'
RESULTADOS = RAIZ/'resultados/atual'


from tabelas import ler_tabela

def salvar(fig, arquivo):
    fig.savefig(SAIDA/f'{arquivo}.png', dpi=300, bbox_inches='tight')
    fig.savefig(SAIDA/f'{arquivo}.pdf', bbox_inches='tight')
    if arquivo != 'pressao_territorial':
        shutil.copy2(SAIDA/f'{arquivo}.pdf', FIGURAS/f'{arquivo}.pdf')
    plt.close(fig)


def investimento():
    t = ler_tabela(RESULTADOS/'sensibilidade/resumo.csv', sep=';')
    t = t[(t.grupo == 'curva') & (t.status == 'Optimal')].sort_values('cobertura').copy()
    t['cobertura_pct'] = 100*t.cobertura
    t['obra_milhoes'] = t.construcao_estimativa_por_porte/1e6
    # Diferencas finitas entre cenarios, nao custo marginal de um modelo continuo.
    t['incremento_obra'] = t.construcao_estimativa_por_porte.diff()
    t['incremento_cobertura_pp'] = t.cobertura_pct.diff()
    t['obra_por_habitante_adicional'] = t.incremento_obra/(t.populacao*t.cobertura.diff())
    t.to_csv(SAIDA/'investimento_cobertura.csv', sep=';', index=False, encoding='utf-8-sig')
    fig, ax = plt.subplots(figsize=(7,4))
    ax.plot(t.cobertura_pct, t.obra_milhoes, '-o', color='#25668c')
    for r in t.itertuples():
        ax.annotate(f'{int(r.novas_ubs)} UBS', (r.cobertura_pct,r.obra_milhoes),
                    xytext=(0,9), textcoords='offset points', ha='center', fontsize=8)
    ax.set_xlabel('Cobertura com capacidade das UBS fixas (%)')
    ax.set_ylabel('Construção das novas UBS (R$ milhões)')
    ax.margins(x=.12,y=.20); ax.grid(alpha=.2)
    ax.spines[['top','right']].set_visible(False)
    salvar(fig,'investimento_cobertura')


def pressao():
    p = ler_tabela(RESULTADOS/'graficos_demanda/atribuicao_91_pontos_mais_proxima.csv',sep=';')
    u = ler_tabela(RESULTADOS/'graficos_demanda/utilizacao_ubs_antes_depois.csv',sep=';').set_index('codigo')
    limite,_ = limite_municipal()
    geoms = [limite] if limite.geom_type == 'Polygon' else list(limite.geoms)
    fig,axes = plt.subplots(1,2,figsize=(9,6),sharex=True,sharey=True)
    cmap = plt.get_cmap('YlOrRd'); norm=Normalize(0,300)
    x,y = projetar(p.lon,p.lat)
    for ax,rede in zip(axes,['atual','plano']):
        for g in geoms:
            ax.add_patch(Polygon(np.asarray(g.exterior.coords)/1000,fc='#f4f6f6',ec='#35434a',lw=.7))
        p[f'pressao_{rede}_pct'] = p[f'ubs_{rede}'].replace(NOVAS).map(u[f'utilizacao_{rede}'])
        ax.scatter(x/1000,y/1000,c=p[f'pressao_{rede}_pct'],cmap=cmap,norm=norm,
                   s=18,edgecolors='#555555',linewidths=.25,zorder=2)
        ax.set_aspect('equal'); ax.set_xlabel('Leste-Oeste (km)'); ax.grid(alpha=.15)
        ax.text(.03,.97,'Rede atual' if rede=='atual' else 'Plano proposto',
                transform=ax.transAxes,va='top',fontsize=9)
    axes[0].set_ylabel('Norte-Sul (km)')
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=axes,
                 fraction=.035,pad=.04,label='Demanda potencial / capacidade efetiva da UBS mais proxima (%)')
    p.to_csv(SAIDA/'pressao_territorial.csv',sep=';',index=False,encoding='utf-8-sig')
    salvar(fig,'pressao_territorial')


def ocupacao():
    t = ler_tabela(RESULTADOS/'plano/aps/ubs_completas.csv')
    t['ocupacao_esf_pct'] = 100*t.pop_atendida/(3000*t.n_esf)
    t['rural'] = t.nome.str.contains('rural',case=False,regex=False)
    t['rotulo'] = [NOVAS.get(r.id_ubs,nome(r.nome)) for r in t.itertuples()]
    t['rotulo'] = t.rotulo.str.replace('UBS Parque Jardim Santanense / Residencial Santanense','Parque Jd. Santanense',regex=False).str.replace('UBS ','',regex=False)
    t.to_csv(SAIDA/'ocupacao_equipes.csv',sep=';',index=False,encoding='utf-8-sig')
    fig,ax = plt.subplots(figsize=(7,9))
    t['ordem_ocupacao'] = t.ocupacao_esf_pct.round(4)
    t = t.sort_values(['ordem_ocupacao','rotulo'],ascending=[False,True])
    yy=np.arange(len(t))
    ax.barh(yy,t.ocupacao_esf_pct,color=np.where(t.status=='EXISTENTE',EXISTENTE,np.where(t.rural,RURAL,URBANA)))
    ax.set_yticks(yy,t.rotulo,fontsize=8);ax.invert_yaxis()
    ax.set_xlim(0,115);ax.axvline(100,color='#555555',lw=.8,ls='--')
    for y,v in zip(yy,t.ocupacao_esf_pct):ax.text(v+1,y,f'{v:.0f}%',va='center',fontsize=7)
    ax.set_xlabel('População alocada / capacidade das eSF (%)')
    ax.legend(handles=[Line2D([],[],color=EXISTENTE,lw=7,label='UBS existente'),
                       Line2D([],[],color=URBANA,lw=7,label='Nova urbana'),
                       Line2D([],[],color=RURAL,lw=7,label='Nova rural')],
              loc='lower right',frameon=False,fontsize=8)
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();salvar(fig,'ocupacao_equipes')


if __name__ == '__main__':
    SAIDA.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'pdf.fonttype':42})
    investimento();pressao();ocupacao()
