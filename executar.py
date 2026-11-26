"""Entrada do projeto: planejamento, diagnostico, orcamento e verificacoes."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys

RAIZ = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for pasta in ['codigos','modelos']:
    sys.path.insert(0,str(RAIZ/pasta))
from caminhos import CACHE
os.environ.setdefault('MPLCONFIGDIR',str(CACHE/'matplotlib'))


def verificar():
    """Confere dependencias sem iniciar a otimizacao ou acessar a internet."""
    print('Python:',sys.version.split()[0])
    print('Projeto:',RAIZ)
    faltam=[]
    for modulo in ['numpy','pandas','pulp','highspy','matplotlib','folium','openpyxl']:
        ok=importlib.util.find_spec(modulo) is not None
        print(modulo+':', 'OK' if ok else 'instalar com requirements.txt')
        if not ok:faltam.append(modulo)
    solver=shutil.which('glpsol')
    if solver is None and (RAIZ/'ferramentas/glpk/glpsol.exe').is_file():
        solver=str(RAIZ/'ferramentas/glpk/glpsol.exe')
    print('GLPK/glpsol:',solver or 'instalar GLPK e adicionar glpsol ao PATH')
    if not solver:faltam.append('glpsol')
    from preparar import hashes
    import json
    assert hashes()==json.loads((RAIZ/'documentacao/entradas_sha256.json').read_text())
    print('Entradas territoriais: OK')
    return 1 if faltam else 0


if __name__=='__main__':
    if '--verificar' in sys.argv:
        sys.exit(verificar())
    acoes={'--graficos':'organizar_resultados','--investimento':'calcular_investimento','--diagnostico':'diagnosticar','--orcamento':'comparar_orcamento',
           '--auditar':'auditar_plano_completo','--preparar':'preparar','--custo-equipes':'custo_equipes'}
    selecionadas=[a for a in acoes if a in sys.argv]
    if len(selecionadas)>1:
        raise SystemExit('Escolha uma acao por comando.')
    if selecionadas:
        import runpy
        acao=selecionadas[0]
        sys.argv.remove(acao)
        if acao=='--graficos':sys.argv.append('--completos')
        runpy.run_module(acoes[acao],run_name='__main__')
    else:
        from planejar import iniciar
        iniciar()
