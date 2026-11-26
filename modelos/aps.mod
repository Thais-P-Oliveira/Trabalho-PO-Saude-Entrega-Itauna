# Localizacao e dimensionamento das UBS.
# Fase 1: cobertura; fase 2: custo em cinco anos; fase 3: deslocamento.
set I;
set J;
set C within J;
set E := J diff C;
set P := 1..4;
param pop{I}, >=0;
param dist{I,J}, >=0;
param cob{I,J}, binary;
param emin{J}, integer, >=0;
param emax{J}, integer, >=1;
param acs0{J}, integer, >=0;
param minimo{C}, >=0;
param fixo{J}, >=0;
param pessoal{J}, >=0;
param obra{P}, >=0;
param hab_esf >0;
param hab_acs >0;
param custo_esf >=0;
param custo_acs >=0;
param custo_km >=0;
param meses >0;
param max_novas integer >=0;
param usar_orcamento binary;
param disponivel_anual;
param fase integer >=1, <=3;
param alvo >=0, default 0;
param operacao_referencia >=0, default 1e15;
param obra_referencia >=0, default 1e15;
param folga >=0;

var x{I,J}, >=0;
var y{C}, binary;
var esf{j in J}, integer, >=emin[j], <=emax[j];
var acs{j in J}, integer, >=acs0[j];
var porte{C,P}, binary;
var cobertura;
var operacional;
var investimento;
var deslocamento;

s.t. demanda{i in I}: sum{j in J}x[i,j] = pop[i];
s.t. capacidade_esf{j in J}: sum{i in I}x[i,j] <= hab_esf*esf[j];
s.t. capacidade_acs{j in J}: sum{i in I}x[i,j] <= hab_acs*acs[j];
s.t. porte_unico{j in C}: sum{p in P}porte[j,p] = y[j];
s.t. equipes_porte{j in C}: esf[j] = sum{p in P}p*porte[j,p];
s.t. porte_permitido{j in C,p in P: p > emax[j]}: porte[j,p] = 0;
s.t. abre_max{j in C}: esf[j] <= emax[j]*y[j];
s.t. abre_min{j in C}: esf[j] >= y[j];
s.t. minimo_abertura{j in C}: sum{i in I}cob[i,j]*x[i,j] >= minimo[j]*y[j];
s.t. limite_novas: sum{j in C}y[j] <= max_novas;
s.t. calcula_cobertura: cobertura = sum{i in I,j in J}cob[i,j]*x[i,j];
s.t. calcula_operacional: operacional =
 sum{j in E}fixo[j] + sum{j in C}fixo[j]*y[j]
 + sum{j in J}(pessoal[j]+custo_esf*(esf[j]-emin[j])+custo_acs*acs[j]);
s.t. calcula_obra: investimento = sum{j in C,p in P}obra[p]*porte[j,p];
s.t. calcula_deslocamento: deslocamento = custo_km*sum{i in I,j in J}dist[i,j]*x[i,j];
s.t. orcamento{t in 1..1: usar_orcamento = 1}:
 12*(sum{j in C}fixo[j]*y[j] + sum{j in J}
 (custo_esf*(esf[j]-emin[j])+custo_acs*(acs[j]-acs0[j]))) <= disponivel_anual;
s.t. preserva_cobertura{t in 1..1: fase >= 2}: cobertura >= alvo;
s.t. teto_operacional{t in 1..1: fase = 3}: operacional <= operacao_referencia*(1+folga);
s.t. teto_obra{t in 1..1: fase = 3}: investimento <= obra_referencia+0.001;

minimize objetivo:
 if fase = 1 then -cobertura
 else if fase = 2 then investimento+meses*operacional
 else deslocamento;
solve;
printf "RESUMO;%.12g;%.12g;%.12g;%.12g\n", cobertura,operacional,investimento,deslocamento;
printf{j in J: esf[j] > 0} "UBS;%s;%g;%g;%g\n", j,esf[j],acs[j],sum{i in I}x[i,j];
end;
