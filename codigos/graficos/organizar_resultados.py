"""Imagens e apresentacao de uma unica execucao, sem referencias a planos antigos."""
from pathlib import Path as _Caminho
import sys as _sistema
_sistema.path.insert(0, str(_Caminho(__file__).resolve().parents[1]))
from caminhos import RAIZ
import argparse
import csv
import html
import json
import os
from pathlib import Path
from caminhos import RAIZ,CACHE
os.environ.setdefault('MPLCONFIGDIR',str(CACHE/'matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


from tabelas import ler_tabela

def br(v,n=2):
    return f'{v:,.{n}f}'.replace(',','X').replace('.',',').replace('X','.')


def barras(destino,nome,titulo,rotulos,valores,unidade,nota):
    fig,ax=plt.subplots(figsize=(10,5))
    ax.barh(range(len(valores)),valores,color=['#52627a','#3864be','#c32562','#008060'][:len(valores)])
    ax.set_yticks(range(len(valores)),rotulos)
    ax.invert_yaxis()
    ax.set_xlabel(unidade)
    ax.set_xlim(0,max(valores)*1.22 if max(valores)>0 else 1)
    if '%' in unidade:
        ax.set_xlim(0,108)
        ax.set_xticks([0,20,40,60,80,100])
    for i,v in enumerate(valores):ax.text(v+max(valores)*.015,i,br(v),va='center')
    for lado in ['top','right']:ax.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino/nome,dpi=160);plt.close(fig)



def gerar_todas():
    """Reproduz as figuras do artigo e da consulta a partir dos resultados salvos."""
    import subprocess
    import sys
    import shutil
    scripts = [
        ['graficos_demanda.py'], ['graficos_itauna.py', '--saida', 'imagens'],
        ['graficos_comparacao.py'], ['figuras_artigo.py'],
        ['grafico_sensibilidade.py'], ['comparacoes_artigo.py']]
    for argumentos in scripts:
        subprocess.run([sys.executable, '-B', str(RAIZ/'codigos/graficos'/argumentos[0]),
                        *argumentos[1:]], cwd=RAIZ, check=True)
    imagens = RAIZ/'imagens'
    artigo = RAIZ/'documentacao/artigo/figuras'
    plano = RAIZ/'resultados/atual/plano/aps'
    for nome in ['mapa_itauna_rede_atual.png', 'mapa_itauna_ubs.png',
                 'mapa_itauna_zoom_urbano.png', 'painel_resultados.png']:
        shutil.copy2(imagens/nome, plano/nome)
    for nome in ['mapa_rede_atual', 'mapa_plano_par', 'curva_acesso_geografico']:
        for extensao in ['png', 'pdf', 'csv']:
            origem = RAIZ/f'resultados/atual/graficos_demanda/{nome}.{extensao}'
            if origem.exists():
                shutil.copy2(origem, imagens/f'acesso_e_mapas/{nome}.{extensao}')
        shutil.copy2(imagens/f'acesso_e_mapas/{nome}.pdf', artigo/f'{nome}.pdf')
    for nome in ['extra_raios_01_custo', 'extra_raios_02_cobertura',
                 'extra_raios_03_distancia', 'curva_cobertura_custo']:
        for extensao in ['png', 'pdf']:
            shutil.copy2(RAIZ/f'resultados/atual/sensibilidade/{nome}.{extensao}',
                         imagens/f'{nome}.{extensao}')
        if nome in ['extra_raios_02_cobertura', 'curva_cobertura_custo']:
            shutil.copy2(imagens/f'{nome}.pdf', artigo/f'{nome}.pdf')
    shutil.copy2(RAIZ/'resultados/atual/figuras_artigo/capacidades.pdf', artigo/'capacidades.pdf')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--completos',action='store_true',help='Regera todas as figuras e atualiza as usadas no artigo.')
    ap.add_argument('--resultado',type=Path,default=RAIZ/'resultados/atual')
    ap.add_argument('--imagens',type=Path,default=RAIZ/'imagens')
    ap.add_argument('--html',type=Path,default=RAIZ/'ABRIR_RESULTADOS.html')
    a=ap.parse_args();resultado=a.resultado.resolve();plano=resultado/'plano';imagens=a.imagens.resolve()
    estado=json.loads((plano/'status.json').read_text(encoding='utf-8'))
    if estado.get('status')!='plano_completo_validado' or estado.get('auditoria_integracao')!='PASSOU':
        raise ValueError('O plano completo deve estar concluido e auditado.')
    if a.completos:
        if resultado != (RAIZ/'resultados/atual').resolve() or imagens != (RAIZ/'imagens').resolve():
            raise ValueError('A reproducao completa usa os resultados consolidados em resultados/atual.')
        gerar_todas()
    imagens.mkdir(parents=True,exist_ok=True)
    meta=json.loads((plano/'plano_aps.json').read_text(encoding='utf-8'))
    ubs=ler_tabela(plano/'aps/ubs_completas.csv');novas=ubs[ubs.status=='NOVA']
    from integracao_resultados import integrar
    integrado=integrar(plano)
    cobertura=integrado['redes']['plano']['cobertura_efetiva_pct']
    anual=integrado['operacional_integrado_anual']
    inv=json.loads((resultado/'investimento/calculos.json').read_text(encoding='utf-8'))
    if inv['novas_ubs']!=len(novas) or Path(inv['plano']).resolve()!=plano:raise ValueError('Investimento de outro plano.')
    obra=float(inv['investimento_construcao'])
    orc=json.loads((resultado/'orcamento/calculos.json').read_text(encoding='utf-8'))
    if abs(float(orc['custo_aps_anual'])-anual)>.01:raise ValueError('Orcamento desatualizado.')
    inicial=next(float(x['total']) for x in orc['dados_oficiais'] if x['conta']=='Atenção Básica' and x['coluna']=='DOTAÇÃO INICIAL')
    diagnostico=plano/'aps/diagnostico'
    diag=ler_tabela(diagnostico/'cobertura_por_zona.csv',sep=';')
    atual=integrado['redes']['atual']['cobertura_efetiva_pct']
    p=meta['parametros'];raio=p['raio'];rural=p.get('raio_rural') or raio
    raios=f'{raio:g} km' if raio==rural else f'{raio:g} km urbano / {rural:g} km rural'
    barras(imagens,'cobertura.png',f'Cobertura: rede atual e plano ({raios})',
           ['Atual: UBS existentes','Atual + móveis (simulação)','Proposta: UBS','Proposta: UBS + móveis'],
           [atual,integrado['redes']['atual']['cobertura_efetiva_com_moveis_pct'],
            cobertura,integrado['redes']['plano']['cobertura_efetiva_com_moveis_pct']],
           'População com cobertura efetiva (%)',
           'Mesmo cálculo: raio + mín(3.000 × eSF; 750 × ACS). Móveis são recursos adicionais propostos.')
    if abs(float(orc['investimento_construcao'])-obra)>.01:raise ValueError('Construcao orcamentaria desatualizada')
    grupos=orc['operacao_por_grupo']
    barras(imagens,'funcionamento_mensal.png','Funcionamento mensal: existentes, novas e rede completa',
           [g['grupo'] for g in grupos]+['Rede completa'],
           [float(g['total_mensal'])/1e6 for g in grupos]+[anual/12e6],
           'R$ milhões/mês','Inclui UBS, eSF, ACS e pessoal móvel adicional. Construção e veículos separados.')
    barras(imagens,'orcamento.png','Funcionamento anual e orçamento da Atenção Básica',
           ['Operação anual','Orçamento atualizado Atenção Básica'],
           [anual/1e6,float(next(x['total'] for x in orc['dados_oficiais'] if x['conta']=='Atenção Básica' and x['coluna']=='DOTAÇÃO ATUALIZADA (a)'))/1e6],'R$ milhões',
           'Comparação apenas do funcionamento anual. Construção apresentada separadamente; orçamento inclui outras despesas.')
    barras(imagens,'construcao.png',f'Construção de {len(novas)} novas UBS',
           ['Investimento único'],[obra/1e6],
           'R$ milhões','Construção por porte; sem terrenos e equipamentos. Prazo de pagamento depende do contrato.')
    acess=ler_tabela(diagnostico/'acessibilidade_por_zona.csv',sep=';')
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for ax,beta in zip(axes,[1,2]):
        for k,(rede,cor,rotulo) in enumerate([('atual_cnes_202607','#52627a','Atual'),('plano_salvo','#3864be','Proposta')]):
            vals=[float(acess[(acess.rede==rede)&(acess.beta==beta)&(acess.zona==z)].acessibilidade_media_ponderada.iloc[0]) for z in ['urbana','rural']]
            xs=[i+(k-.5)*.34 for i in range(2)];ax.bar(xs,vals,width=.34,color=cor,label=rotulo)
            for x,v in zip(xs,vals):ax.text(x,v+max(vals)*.025,br(v,3),ha='center',fontsize=9)
        ax.set_xticks([0,1],['Urbana','Rural'])
        ax.set_ylabel(f'Índice de acessibilidade (β = {beta})')
        ax.margins(y=.18)
        ax.legend()
    fig.tight_layout(rect=[0,.06,1,.93]);fig.savefig(imagens/'acessibilidade.png',dpi=160);plt.close(fig)
    itens=[('Visão geral das UBS','painel_resultados.png'),('Mapa do município','mapa_itauna_ubs.png'),
           ('Rede atual e simulação do complemento móvel','mapa_itauna_rede_atual.png'),
           ('Detalhe urbano','mapa_itauna_zoom_urbano.png'),('Cobertura','cobertura.png'),
           ('Acessibilidade','acessibilidade.png'),('Encaminhamentos: distâncias','distancias.png'),
           ('Percursos','percursos.png'),('Capacidade ambulatorial','capacidades.png'),
           ('Funcionamento mensal','funcionamento_mensal.png'),('Custo e orçamento','orcamento.png'),('Construção','construcao.png')]
    itens += [('Comparação das UBS existentes', 'comparacao/mudancas_ubs_existentes_colunas.png'),
              ('Novas UBS por porte', 'comparacao/novas_ubs_por_porte.png'),
              ('Curva de acesso geográfico', 'acesso_e_mapas/curva_acesso_geografico.png'),
              ('Rede atual: cobertura geográfica', 'acesso_e_mapas/mapa_rede_atual.png'),
              ('Rede proposta: cobertura geográfica', 'acesso_e_mapas/mapa_plano_par.png')]
    itens += [('Investimento e cobertura', 'comparacoes_artigo/investimento_cobertura.png'),
              ('Pressão territorial antes e depois', 'comparacoes_artigo/pressao_territorial.png'),
              ('Ocupação das equipes fixas', 'comparacoes_artigo/ocupacao_equipes.png')]
    if (imagens/'curva_cobertura_custo.png').exists():itens.append(('Sensibilidade: cobertura e custo','curva_cobertura_custo.png'))
    extras=[('Custo operacional','extra_raios_01_custo.png'),('Cobertura total, urbana e rural','extra_raios_02_cobertura.png'),('Distância média','extra_raios_03_distancia.png')]
    for _,arquivo in itens+extras:
        if not (imagens/arquivo).is_file():raise FileNotFoundError(imagens/arquivo)
    cards=''.join(f'<section id="fig{i}"><h2>{i}. {html.escape(t)}</h2><a href="imagens/{arq}"><img loading="lazy" src="imagens/{arq}" alt="{html.escape(t)}"></a></section>' for i,(t,arq) in enumerate(itens,1))
    cards+='<section id="extra"><h2>Análise extra: raios 3–3, 3–5 e 5–5 km</h2><p>Mínimo rural de 500 habitantes nos três cenários. A análise principal permanece separada.</p>'
    cards+=''.join(f'<h3>{html.escape(t)}</h3><a href="imagens/{arq}"><img loading="lazy" src="imagens/{arq}" alt="{html.escape(t)}"></a>' for t,arq in extras)+'</section>'
    base='resultados/atual'
    links=[('Detalhamento das UBS fixas (sem móveis)',f'{base}/plano/aps/relatorio_itauna.txt'),('Planilha das UBS e alocações',f'{base}/plano/aps/resultado_itauna.xlsx'),
           ('Mapa interativo',f'{base}/plano/aps/mapa_interativo.html'),('Principal: nível único; complementar: múltiplos níveis',f'{base}/plano/comparacao_completa.csv'),
           ('Cobertura e acessibilidade',f'{base}/plano/aps/diagnostico/relatorio.txt'),('Orçamento',f'{base}/orcamento/relatorio.txt'),
           ('Construção por UBS e porte',f'{base}/investimento/construcao_por_ubs.csv'),('Sensibilidade',f'{base}/sensibilidade/resumo.csv'),
           ('Artigo revisado','planejamento_rede_saude_itauna.pdf')]
    links += [('Cobertura efetiva comparável',f'{base}/plano/aps/cobertura_efetiva/comparacao_cobertura.csv'),
              ('Relatório integrado: UBS e equipes móveis',f'{base}/plano/relatorio_integrado.txt'),
              ('Custos integrados com equipes móveis',f'{base}/orcamento/funcionamento_existentes_e_novas.csv'),
              ('Pessoal observado e estimativa das equipes',f'{base}/financeiro/relatorio_custo_equipes.txt')]
    docs=''.join(f'<li><a href="{path}">{html.escape(t)}</a></li>' for t,path in links)
    comp=ler_tabela(plano/'comparacao_completa.csv',sep=';')
    campos=['cenario','via_percentual','distancia_media_por_percurso','termina2','direto3','via23']
    amb=comp.loc[comp.tipo=='AMB',campos].to_dict('records')
    interativo=(RAIZ/'codigos/graficos/comparador.html').read_text(encoding='utf-8').replace('__DADOS_AMBULATORIAIS__',json.dumps(amb,ensure_ascii=False,allow_nan=False))
    certificado='Ótimo confirmado nas fases da APS, dentro da tolerância configurada.' if meta['otimalidade_confirmada'] else 'Solução viável; há fase da APS sem prova de ótimo. Consulte os certificados.'
    menu='<a href="#comparador">Comparador interativo</a>'+''.join(f'<a href="#fig{i}">{i}. {html.escape(t)}</a>' for i,(t,_) in enumerate(itens,1))+'<a href="#extra">Análise extra dos raios</a>'
    pagina=f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Resultados — PO Saúde Itaúna</title>
<style>body{{font:17px/1.6 system-ui;background:#f3f5fa;color:#202944;margin:0}}main{{max-width:1150px;margin:auto;padding:28px}}section,header{{background:white;padding:25px;margin-bottom:22px;border-radius:14px}}.resumo{{font-size:23px;color:#254db3;font-weight:700}}img{{max-width:100%;height:auto}}a{{color:#214da6}}nav{{display:flex;flex-wrap:wrap;gap:10px}}nav a{{background:#eaf0ff;padding:7px 12px;border-radius:7px}}small{{color:#536078}}</style>
<main><header><h1>Planejamento da rede de saúde de Itaúna</h1><p class="resumo">{len(novas)} novas UBS · {int(ubs.n_esf.sum())} eSF · {int(ubs.acs.sum())} ACS · {br(cobertura)}% de cobertura</p>
<p>População: {br(meta['total'],0)} habitantes. Raio principal: {raios}. Mínimo rural: {br(p.get('hab_min_nova_rural',0),0)} habitantes.</p>
<p>Operação: R$ {br(anual/1e6)} milhões/ano. Construção: R$ {br(obra/1e6)} milhões, investimento único. Construção apresentada separadamente da comparação do funcionamento com o orçamento.</p><p>{certificado}</p>
<p>Cobertura efetiva com equipes móveis propostas: {br(integrado['redes']['plano']['cobertura_efetiva_com_moveis_pct'])}%. Equipes móveis adicionais: {integrado['custos_moveis']['plano']['equipes']} equipes e {integrado['custos_moveis']['plano']['acs']} ACS.</p>
<p>Inclui pessoal móvel adicional. Veículos, combustível e equipamentos ainda não foram precificados. A demanda especializada dos atendidos por equipes móveis parte da UBS-base. Resultado principal: nível único; múltiplos níveis são análise complementar.</p>
<p>Resultado hospitalar exploratório: leitos gerais e UTI separados. A carga de outros atendimentos não está discriminada por tipo de leito; o limite residual conservador não mede a disponibilidade real nem uma fila hospitalar.</p><p>Todas as imagens, tabelas e o comparador utilizam a mesma execução.</p><nav>{menu}</nav><h2>Relatórios e arquivos</h2><ul>{docs}</ul>
<small>O mapa-base interativo pode precisar de internet. As figuras do artigo são renovadas; o texto deve ser revisado quando os resultados mudarem.</small></header>{interativo}{cards}</main></html>'''
    a.html.parent.mkdir(parents=True,exist_ok=True);a.html.write_text(pagina,encoding='utf-8')
    with (imagens/'INDICE.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['ordem','titulo','arquivo'])
        w.writerows((i,t,arq) for i,(t,arq) in enumerate(itens,1));w.writerows(('extra',t,arq) for t,arq in extras)
    print('Imagens e página da nova execução geradas:',a.html)


if __name__=='__main__':main()
