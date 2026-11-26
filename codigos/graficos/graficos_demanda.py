"""Calcula a demanda potencial pela UBS mais proxima e gera os graficos."""
from pathlib import Path as _Caminho
import sys as _sistema
_sistema.path.insert(0, str(_Caminho(__file__).resolve().parents[1]))
from caminhos import RAIZ
from paleta import EXISTENTE, URBANA, RURAL, MOVEL, NO_RAIO, FORA_RAIO, cor_ubs
import argparse,json,hashlib,textwrap
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch,Polygon
from caminhos import RAIZ,BASE
from geografia import distancias_haversine_km,limite_municipal,projetar

LARGURA=16/2.54
AZUL,COR_ATUAL='#25668c','#75869b'
NOVAS={'NOVA_33':'N1','NOVA_77':'N2','NOVA_64':'N3','NOVA_90':'N4','NOVA_55':'N5',
       'NOVA_83':'N6','NOVA_61':'N7','NOVA_74':'N8','NOVA_71':'N9'}
ACENTOS={'UBS ALTO DO ROSARIO':'UBS Alto do Rosário','UBS GRACAS':'UBS Graças',
 'UBS IRMAOS AULER':'UBS Irmãos Auler','UBS PADRE EUSTAQUIO':'UBS Padre Eustáquio',
 'UBS SAO GERALDO':'UBS São Geraldo','UBS VARZEA DA OLARIA':'UBS Várzea da Olaria',
 'UBS PARQUE JARDIM SANTANENSE RESIDENCIAL SANTANENSE':'UBS Parque Jardim Santanense / Residencial Santanense'}

from tabelas import ler_tabela

def nome(s):
 if s in ACENTOS:return ACENTOS[s]
 t=str(s).title().replace('Ubs ','UBS ').replace(' Ii',' II').replace(' Xii',' XII')
 for a,b in [(' Do ',' do '),(' Da ',' da '),(' De ',' de ')]:t=t.replace(a,b)
 return t

def br(v,n=1):return f'{v:,.{n}f}'.replace(',','X').replace('.',',').replace('X','.')
def salvar(fig,saida,nome):
 # Sem bbox tight: largura física preservada em 16 cm, fonte mínima de 9 pt.
 fig.savefig(saida/f'{nome}.pdf');fig.savefig(saida/f'{nome}.png',dpi=300);plt.close(fig)

def entradas(plano):
 pontos=ler_tabela(plano/'aps/demanda_cenario.csv')
 u=ler_tabela(plano/'aps/ubs_completas.csv')
 fontes=ler_tabela(BASE/'unidades_existentes_itauna.xlsx',dtype={'cnes':str})
 rec=ler_tabela(BASE/'fontes_publicas/ubs_recursos_cnes_202607.xlsx',sep=';',dtype={'cnes':str})
 ids={f'UBS{int(r.j)}':r.cnes for r in fontes.itertuples()}
 u['cnes']=u.id_ubs.map(ids)
 u=u.merge(rec[['cnes','esf','acs_vinculos']],on='cnes',how='left',validate='many_to_one')
 return pontos,u

def atribuicao_proxima(pontos,ubs):
 d=distancias_haversine_km(pontos.lon,pontos.lat,ubs.lon,ubs.lat)
 prox=d.argmin(axis=1)
 carga=np.bincount(prox,weights=pontos.pessoas,minlength=len(ubs))
 assert np.isclose(carga.sum(),pontos.pessoas.sum())
 return carga,d[np.arange(len(pontos)),prox],prox

def utilizacao(pontos,u,saida):
 ex=u[u.status=='EXISTENTE'].copy()
 ca,da,ia=atribuicao_proxima(pontos,ex)
 cp,dp,ip=atribuicao_proxima(pontos,u)
 cap_a=np.minimum(3000*ex.esf,750*ex.acs_vinculos).to_numpy()
 cap_p=np.minimum(3000*u.n_esf,750*u.acs).to_numpy()
 assert (cap_a>0).all() and (cap_p>0).all()
 atual={uid:(e,a,c,d) for uid,e,a,c,d in zip(ex.id_ubs,ex.esf,ex.acs_vinculos,cap_a,ca)}
 linhas=[]
 for i,r in enumerate(u.itertuples()):
  novo=r.status=='NOVA'
  if novo:
   assert r.id_ubs in NOVAS,'Código novo não registrado: '+r.id_ubs
   codigo=NOVAS[r.id_ubs];n=r.nome[len('NOVA UBS ('):-1]
  else:codigo=r.id_ubs;n=nome(r.nome)
  e,a,c,d=atual.get(r.id_ubs,(np.nan,)*4)
  linhas.append(dict(unidade=n,codigo=codigo,status=r.status,esf_atual=e,acs_atual=a,
   capacidade_atual=c,demanda_potencial_atual=d,utilizacao_atual=100*d/c,
   esf_plano=r.n_esf,acs_plano=r.acs,capacidade_plano=cap_p[i],
   demanda_potencial_plano=cp[i],utilizacao_plano=100*cp[i]/cap_p[i]))
 tab=pd.DataFrame(linhas)
 tab=pd.concat([tab[tab.status=='EXISTENTE'].sort_values('utilizacao_atual',ascending=False),
  tab[tab.status=='NOVA'].sort_values('codigo',key=lambda s:s.str[1:].astype(int))],ignore_index=True)
 tab.to_csv(saida/'utilizacao_ubs_antes_depois.csv',sep=';',index=False,encoding='utf-8-sig')
 ids_a={r.id_ubs:j for j,r in enumerate(ex.itertuples())}
 vinc=pontos[['i','NM_BAIRRO','pessoas','lon','lat']].copy()
 vinc['ubs_atual']=ex.id_ubs.to_numpy()[ia];vinc['distancia_atual_km']=da
 vinc['ubs_plano']=u.id_ubs.to_numpy()[ip];vinc['distancia_plano_km']=dp
 vinc.to_csv(saida/'atribuicao_91_pontos_mais_proxima.csv',sep=';',index=False,encoding='utf-8-sig')
 fig,ax=plt.subplots(figsize=(LARGURA,9.2));fig.subplots_adjust(left=.43,right=.94,bottom=.075,top=.955)
 y=np.arange(len(tab));bar=.32
 mask=tab.status=='EXISTENTE'
 ax.barh(y[mask]-.25,tab.loc[mask,'utilizacao_atual'],height=bar,color=COR_ATUAL,label='Rede atual')
 ax.barh(y+.25,tab.utilizacao_plano,height=bar,color=AZUL,label='Plano proposto')
 labels=[]
 for r in tab.itertuples():
  labels.append(r.codigo if r.status=='NOVA' else '\n'.join(textwrap.wrap(r.unidade,width=28)))
 ax.set_yticks(y,labels,fontsize=9);ax.invert_yaxis();ax.set_ylim(len(tab)-.4,-1.1)
 ax.axvline(100,color='#9a3c27',ls='--',lw=1)
 maximo=float(np.nanmax(tab[['utilizacao_atual','utilizacao_plano']].values))
 ax.set_xlim(0,max(120,maximo*1.18));ax.tick_params(axis='x',labelsize=9)
 for i,r in enumerate(tab.itertuples()):
  if r.status=='EXISTENTE':ax.text(r.utilizacao_atual+maximo*.012,i-.25,br(r.utilizacao_atual,0)+'%',va='center',fontsize=9)
  ax.text(r.utilizacao_plano+maximo*.012,i+.25,br(r.utilizacao_plano,0)+'%',va='center',fontsize=9)
 ax.set_xlabel('Demanda potencial / capacidade efetiva (%)',fontsize=9)
 ax.legend(loc='lower left',bbox_to_anchor=(-.80,1.005),ncol=2,frameon=False,fontsize=9,
           handlelength=1.3,columnspacing=1.5)
 ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 ax.axhline(int(mask.sum())-.5,color='#aaaaaa',lw=.7)
 salvar(fig,saida,'utilizacao_ubs_antes_depois')
 resumo=dict(populacao=float(pontos.pessoas.sum()),pontos=len(pontos),
  acima_100_atual=int((100*ca/cap_a>100+1e-7).sum()),
  acima_100_plano=int((100*cp/cap_p>100+1e-7).sum()),
  acima_100_plano_existentes=int((tab.loc[mask,'utilizacao_plano']>100+1e-7).sum()),
  media_ponderada_capacidade_atual=100*ca.sum()/cap_a.sum(),
  media_ponderada_capacidade_plano=100*cp.sum()/cap_p.sum(),
  media_ponderada_populacao_atual=float(np.average(100*ca/cap_a,weights=ca)),
  media_ponderada_populacao_plano=float(np.average(100*cp/cap_p,weights=cp)),
  capacidade_atual=float(cap_a.sum()),capacidade_plano=float(cap_p.sum()))
 return tab,resumo,da,dp

def curva(pontos,da,dp,saida):
 fig,ax=plt.subplots(figsize=(LARGURA,3.8));fig.subplots_adjust(left=.13,right=.97,bottom=.23,top=.96)
 csv=[]
 for dist,rotulo,cor in [(da,'Rede atual (22 UBS)',COR_ATUAL),(dp,'Plano proposto (31 UBS)',AZUL)]:
  ordem=np.argsort(dist,kind='stable');d=dist[ordem];pop=pontos.pessoas.to_numpy()[ordem]
  acum=np.cumsum(pop);pct=100*acum/pop.sum()
  ax.step(np.r_[0,d],np.r_[0,pct],where='post',label=rotulo,color=cor,lw=1.8)
  for idx,v,a,p in zip(ordem,d,acum,pct):csv.append(dict(rede=rotulo,ponto=int(pontos.iloc[idx].i),distancia_km=v,populacao_acumulada=a,percentual_acumulado=p))
 ax.axvline(3,color='#9a3c27',ls='--',lw=1,label='Referência: 3 km')
 ax.set_xlabel('Distância em linha reta até a UBS mais próxima (km)',fontsize=9)
 ax.set_ylabel('População acumulada (%)',fontsize=9);ax.set_ylim(0,102);ax.set_xlim(left=0)
 ax.tick_params(labelsize=9);ax.legend(loc='lower right',fontsize=9,frameon=False)
 ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.2)
 salvar(fig,saida,'curva_acesso_geografico')
 pd.DataFrame(csv).to_csv(saida/'curva_acesso_geografico.csv',sep=';',index=False,encoding='utf-8-sig')

def mapa_rede(pontos,u,dist,saida,plano=False):
 # Par com a mesma escala e os mesmos estilos; sem pessoal móvel nas duas imagens.
 fig,ax=plt.subplots(figsize=(LARGURA,4.8));fig.subplots_adjust(left=.10,right=.59,bottom=.14,top=.97)
 lim,_=limite_municipal();geoms=[lim] if lim.geom_type=='Polygon' else list(lim.geoms)
 for g in geoms:ax.add_patch(Polygon(np.asarray(g.exterior.coords)/1000,fc='#f4f6f6',ec='#263746',lw=1))
 x,y=projetar(pontos.lon,pontos.lat);ux,uy=projetar(u.lon,u.lat)
 cob=dist<=3+1e-9
 ax.scatter(x[cob]/1000,y[cob]/1000,s=13,color=NO_RAIO,zorder=3)
 ax.scatter(x[~cob]/1000,y[~cob]/1000,s=23,facecolors='none',edgecolors=FORA_RAIO,zorder=3)
 for xx,yy,r in zip(ux/1000,uy/1000,u.itertuples()):
  novo=r.status=='NOVA';cor=cor_ubs(r.status,r.nome)
  ax.add_patch(plt.Circle((xx,yy),3,facecolor=cor,edgecolor=cor,alpha=.10,lw=.6))
  ax.scatter([xx],[yy],marker='*' if novo else 's',s=65 if novo else 22,color=cor,edgecolor='black',lw=.5,zorder=4)
  if novo:ax.annotate(NOVAS[r.id_ubs],(xx,yy),xytext=(4,4),textcoords='offset points',fontsize=9,zorder=5)
 bx0,by0,bx1,by1=np.array(lim.bounds)/1000
 ax.set_xlim(bx0-1.5,bx1+1.5);ax.set_ylim(by0-1.5,by1+1.5);ax.set_aspect('equal')
 ax.set_xlabel('Leste–Oeste (km)',fontsize=9);ax.set_ylabel('Norte–Sul (km)',fontsize=9);ax.tick_params(labelsize=9)
 handles=[Patch(fc='#f4f6f6',ec='#263746',label='Limite municipal'),
  Line2D([],[],marker='s',ls='',color=EXISTENTE,label='UBS existentes'),
  Line2D([],[],marker='*',ls='',color=URBANA,label='Novas UBS urbanas'),
  Line2D([],[],marker='*',ls='',color=RURAL,label='Novas UBS rurais'),
  Line2D([],[],marker='o',ls='',color=NO_RAIO,label='População no raio'),
  Line2D([],[],marker='o',ls='',mfc='none',color=FORA_RAIO,label='População fora do raio')]
 ax.legend(handles=handles,bbox_to_anchor=(1.01,1),loc='upper left',frameon=False,fontsize=9)
 ax.grid(alpha=.15)
 nome_arq='mapa_plano_par' if plano else 'mapa_rede_atual'
 salvar(fig,saida,nome_arq)
 pp=pontos.copy();pp['distancia_ubs_proxima_km']=dist;pp['cobertura_geografica']=cob.astype(int)
 pp['camada']='populacao';ubs=u.copy();ubs['camada']='ubs'
 pd.concat([pp,ubs],ignore_index=True).to_csv(saida/f'{nome_arq}.csv',sep=';',index=False,encoding='utf-8-sig')

def principal(plano,saida):
 saida.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
 pontos,u=entradas(plano)
 tab,resumo,da,dp=utilizacao(pontos,u,saida)
 curva(pontos,da,dp,saida)
 mapa_rede(pontos,u[u.status=='EXISTENTE'],da,saida)
 mapa_rede(pontos,u,dp,saida,plano=True)
 (saida/'resumo_utilizacao.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
 nova=tab[tab.status=='NOVA'][['codigo','unidade']]
 nova.to_csv(saida/'identificacao_N1_N9.csv',sep=';',index=False,encoding='utf-8-sig')
 return resumo

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plano',type=Path,default=RAIZ/'resultados/atual/plano');p.add_argument('--saida',type=Path,default=RAIZ/'resultados/atual/graficos_demanda')
 a=p.parse_args();print(json.dumps(principal(a.plano,a.saida),ensure_ascii=False,indent=2))
