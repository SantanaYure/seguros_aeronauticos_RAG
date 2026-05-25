# Dataset oficial preliminar — revisão humana

Versão legível de `eval/evaluation_dataset.csv`. Cada entrada abaixo corresponde a uma linha do CSV.

Use este arquivo para uma leitura rápida durante a revisão. As edições devem ser feitas no CSV oficial, não aqui.

---

## Q_manual_001

**Pergunta:**

O que é casco aeronáutico?

**Tipo:**

conceitual

**Escopo:**

geral

**Seguradora / órgão:**

TODAS

**Fonte esperada:**

—

**Termos esperados:**

casco aeronáutico; aeronave; cobertura; danos materiais; responsabilidade

**Resposta ideal draft:**

Revisar manualmente: casco aeronáutico é tipicamente coberto em apólice de Casco, não em RC Hangar. A resposta ideal deve reconhecer ausência de base nesta coleção e sugerir o produto correto.

**Critério de sucesso:**

Passa se o agente reconhecer ausência de base suficiente nestes documentos e responder com cautela.

**Nível de dificuldade:**

dificil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta manual reutilizada do test_match.py. Pode estar fora do escopo de RC Hangar; serve para testar comportamento seguro do agente.

**Observações de revisão:**

resposta ideal ainda é instrução de revisão

---

## Q_manual_002

**Pergunta:**

O seguro cobre pane seca?

**Tipo:**

exclusao

**Escopo:**

geral

**Seguradora / órgão:**

TODAS

**Fonte esperada:**

—

**Termos esperados:**

pane seca; falta de combustível; operação irregular; inobservância de normas; agravamento de risco

**Resposta ideal draft:**

Revisar manualmente: termo coloquial. A resposta ideal deve verificar se há exclusão expressa ou se a situação cai em operação irregular, falta de combustível, agravamento de risco ou inobservância de normas aeronáuticas.

**Critério de sucesso:**

Passa se recuperar exclusões/cláusulas que tratem de falta de combustível, operação irregular ou agravamento de risco.

**Nível de dificuldade:**

dificil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta manual. Pode exigir busca híbrida ou expansão de query (sinônimos do mercado securitário).

**Observações de revisão:**

resposta ideal ainda é instrução de revisão

---

## Q_manual_003

**Pergunta:**

O que significa exclusão operacional?

**Tipo:**

exclusao

**Escopo:**

geral

**Seguradora / órgão:**

TODAS

**Fonte esperada:**

—

**Termos esperados:**

exclusão; operacional; riscos excluídos; autorização; licença; normas

**Resposta ideal draft:**

Revisar manualmente: a expressão pode não aparecer literalmente. A resposta ideal deve mapear equivalentes ligados a riscos excluídos, autorização, licença e normas operacionais.

**Critério de sucesso:**

Passa se recuperar trechos de riscos excluídos vinculados a operação irregular, falta de licença ou inobservância de normas.

**Nível de dificuldade:**

dificil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta manual. Boa para validar capacidade do agente de encontrar equivalentes lexicais.

**Observações de revisão:**

resposta ideal ainda é instrução de revisão

---

## Q_manual_004

**Pergunta:**

O que é responsabilidade civil no seguro aeronáutico?

**Tipo:**

conceitual

**Escopo:**

geral

**Seguradora / órgão:**

TODAS

**Fonte esperada:**

—

**Termos esperados:**

responsabilidade civil; danos; terceiros; cobertura; segurado; aeronáutico

**Resposta ideal draft:**

Revisar manualmente: definir RC com base nas Condições Gerais das seguradoras e, quando cabível, na Resolução CNSP/SUSEP 407/2021. Resposta deve citar danos a terceiros e fonte específica.

**Critério de sucesso:**

Passa se recuperar definição ou descrição contratual de responsabilidade civil em ao menos uma fonte.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta manual. Deve funcionar bem na base atual.

**Observações de revisão:**

resposta ideal ainda é instrução de revisão

---

## Q_manual_005

**Pergunta:**

Quando a seguradora pode negar indenização?

**Tipo:**

sinistro

**Escopo:**

geral

**Seguradora / órgão:**

TODAS

**Fonte esperada:**

—

**Termos esperados:**

negativa; indenização; recusa; perda de direito; fraude; agravamento de risco; exclusões; obrigações do segurado

**Resposta ideal draft:**

Revisar manualmente: a resposta ideal deve enumerar hipóteses de recusa, perda de direito, fraude, agravamento de risco, exclusões expressas e descumprimento de obrigações do segurado, citando fonte específica.

**Critério de sucesso:**

Passa se recuperar trechos cobrindo recusa de sinistro, perda de direito, fraude, agravamento de risco, exclusões ou obrigações do segurado.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta manual. Verifica capacidade de cobertura ampla sobre razões de negativa.

**Observações de revisão:**

resposta ideal ainda é instrução de revisão

---

## Q001

**Pergunta:**

Como a fraude pode afetar o direito à indenização na EZZE?

**Tipo:**

sinistro

**Escopo:**

seguradora

**Seguradora / órgão:**

EZZE

**Fonte esperada:**

CG_EZZE_Hangar.pdf, página 19

**Termos esperados:**

fraude; indenização; negativa; segurado; perda

**Resposta ideal draft:**

ou responsabilidade (quer por contrato, delito civil, negligência, responsabilidade civil de produto, informação falsa, fraude ou outra forma) de qualquer natureza, decorrente de ou causada por ou em consequência de (direta ou indiretamente e no todo ou em parte): a) falha, inabilidade ou mau funcionamento de qualquer hardware, software, circuito integrado, chip ou equipamento tecnológico de informação ou sistema (quer esteja sob a posse do segurado ou de terceiros) precisamente ou completamente para processar, compartilhar ou transferir ano, informações de data ou hora ou informação...

**Critério de sucesso:**

Passa se recuperar trecho sobre recusa, perda de direito, liquidação, fraude, agravamento de risco ou obrigações em sinistro.

**Nível de dificuldade:**

dificil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'fraude'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q002

**Pergunta:**

Quais exclusões são previstas nas condições gerais da AXA?

**Tipo:**

exclusao

**Escopo:**

seguradora

**Seguradora / órgão:**

AXA

**Fonte esperada:**

CG_AXA_RC Hangar.pdf, página 23

**Termos esperados:**

exclusões; condições gerais; seguradora; riscos; segurado

**Resposta ideal draft:**

do subitem 2 3.2, serão cobertos pelo presente seguro (respeitados os demais termos, condições, limitações, garantias e exclusões deste contrato), desde que: a) no caso de qualquer reclamação a respeito de material radioativo, durante o seu transporte como carga, incluindo armazenamento e/ou manuseio eventual, tal transporte tenha obedecido, em todos os aspectos, as “Instruções Técnicas para o Transporte Seguro de Mercadorias Perigosas por Ar”, da Organização Internacional de Aviação Civil, a menos que o transporte tenha obedecido a uma legislação mais restritiva e, neste caso, que tenham...

**Critério de sucesso:**

Passa se recuperar trecho de riscos excluídos ou situação expressamente não garantida.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'exclusões'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q003

**Pergunta:**

Qual é o âmbito geográfico da cobertura na Essor?

**Tipo:**

cobertura

**Escopo:**

seguradora

**Seguradora / órgão:**

Essor

**Fonte esperada:**

CG_Essor_RC Hangar.pdf, página 22

**Termos esperados:**

âmbito geográfico; território; cobertura; Brasil; seguro

**Resposta ideal draft:**

22 RESPONSABILIDADE CIVIL DE HANGARES E OPERAÇÕES AEROPORTUÁRIAS – CONDIÇÕES GERAIS 4. ÂMBITO GEOGRÁFICO 4.1. As disposições deste contrato de seguro aplicam-se exclusivamente a danos ocorridos e reclamados no perímetro indicado na Apólice. 5. RISCOS EXCLUÍDOS 5.1. NÃO EST ÃO GARANTIDAS POR ESTE SEGURO AS QUANTIAS DEVIDAS E/OU AS DESPENDIDAS, PELO SEGURADO, PARA REPARAR, EVIT AR E/OU MINORAR DANOS, DE QUALQUER ESPÉCIE, DECORRENTES: a) De atos ilícitos dolosos praticados pelos sócios controladores do Segurado, por seus dirigentes, administradores, e por representantes destas pessoas; b) De...

**Critério de sucesso:**

Passa se recuperar trecho que descreva cobertura, limite, franquia ou alcance da garantia.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'âmbito geográfico'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q004

**Pergunta:**

O que o segurado deve fazer em caso de sinistro segundo a Mapfre?

**Tipo:**

obrigacao

**Escopo:**

seguradora

**Seguradora / órgão:**

Mapfre

**Fonte esperada:**

CG_Mapfre_RC_HANGAR.pdf, página 16

**Termos esperados:**

obrigações do segurado; obrigações; segurado; deveres; sinistro; comunicação

**Resposta ideal draft:**

cam-se exclusivamente a danos ocorridos no Território Nacional, salvo disposição em contrário na Apólice. CLÁUSULA 13 – OBRIGAÇÕES DO SEGURADO 13.1. Sob pena de perder o direito a qualquer indenização, nos termos da Cláusula 22 – PERDA DE DIREITOS, o Segurado, por si ou por seu representante legal, obriga-se a: 13.1.1. Prestar à Seguradora todas as informações necessárias à Aceitação do Risco e à fixação da taxa para cálculo do valor do Prêmio; 13.1.2. Dar ciência à Seguradora acerca da contratação, cancelamento ou rescisão de qual quer outro seguro referente aos mesmos riscos previstos...

**Critério de sucesso:**

Passa se recuperar trecho com deveres ou obrigações do segurado.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'obrigações do segurado'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q005

**Pergunta:**

Como a norma de grandes riscos se relaciona com estes seguros aeronáuticos?

**Tipo:**

regulatorio

**Escopo:**

regulatorio

**Seguradora / órgão:**

CNSP_SUSEP

**Fonte esperada:**

SUSEP 407_2021.pdf, página 2

**Termos esperados:**

grandes riscos; Resolução 407; SUSEP; CNSP; enquadramento

**Resposta ideal draft:**

ondições contratuais o conjunto de disposições que regem a contratação de um plano de seguro de danos para cobertura de grandes riscos. CAPÍTULO I DISPOSIÇÕES INICIAIS Art. 4 º Os contratos de seguro de danos para cobertura de grandes riscos serão regidos por condições contratuais livremente pactuadas entre segurados e tomadores, ou seus representantes legais, e a sociedade seguradora, devendo observar, no mínimo, os seguintes princípios e valores básicos: I - liberdade negocial ampla; II - boa fé; III - transparência e objetividade nas informações; IV - tratamento paritário entre as partes...

**Critério de sucesso:**

Passa se recuperar trecho da Resolução CNSP/SUSEP 407/2021 relacionado ao tema.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'grandes riscos'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q006

**Pergunta:**

O que é responsabilidade civil no seguro aeronáutico segundo a Excelsior?

**Tipo:**

conceitual

**Escopo:**

seguradora

**Seguradora / órgão:**

Excelsior

**Fonte esperada:**

CG_Excelsior-RC-Hangar.pdf, página 18

**Termos esperados:**

responsabilidade civil; danos; terceiros; cobertura; segurado

**Resposta ideal draft:**

da ou dano de qualquer aeronave em v oo (exceto se contratado cobertura específica. 1.3. Riscos Específicos – SEÇÃO 3 - RESPONSABILIDADE CIVIL DE PRODUTOS 1.3.1. Riscos Cobertos . Esta Seção cobre as lesões corporais ou danos materiais decorrentes da posse, uso, consumo ou manuseio de quaisquer bens ou produtos fabricados, construídos, alterados, reparados, trabalhados, tratados, vendidos, fornecidos ou distribuídos pelo Segurado ou seus empregados, mas apenas em relação aos bens ou produtos que fazem parte ou são usados em conjunto com aeronaves, e apenas depois que tais bens ou produtos...

**Critério de sucesso:**

Passa se recuperar definição ou descrição contratual suficiente do conceito.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'responsabilidade civil'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q007

**Pergunta:**

Como funciona a liquidação de sinistros na Mapfre?

**Tipo:**

sinistro

**Escopo:**

seguradora

**Seguradora / órgão:**

Mapfre

**Fonte esperada:**

CG_Mapfre_RC_HANGAR.pdf, página 19

**Termos esperados:**

liquidação de sinistros; liquidação; sinistro; documentos; indenização; prazo

**Resposta ideal draft:**

o serão expressos em moeda nacional, ainda que o seguro seja contratado em moeda estrangeira. CLÁUSULA 16 – REGULAÇÃO E LIQUIDAÇÃO DE SINISTROS 16.1. REGULAÇÃO DE SINISTROS: 16.1.1. Ocorrendo um Sinistro, o Segurado, o Beneficiário, ou representante legal de um ou de outro, deverá comunicar imediatamente a Seguradora, fornecendo, nessa oportunidade, tod os os documentos comprobatórios da causa, natureza e extensão da perda ou dano sofrid o , incluindo, mas não se limitando à relação dos bens sinistrados, dos Salvados, estimativa dos prejuízos, data, hora e causas prováveis do Sinistro,...

**Critério de sucesso:**

Passa se recuperar trecho sobre recusa, perda de direito, liquidação, fraude, agravamento de risco ou obrigações em sinistro.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'liquidação de sinistros'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q008

**Pergunta:**

O que não está garantido pelo seguro da Essor?

**Tipo:**

exclusao

**Escopo:**

seguradora

**Seguradora / órgão:**

Essor

**Fonte esperada:**

CG_Essor_RC Hangar.pdf, página 22

**Termos esperados:**

riscos excluídos; não garantidos; segurado; danos; operação

**Resposta ideal draft:**

deste contrato de seguro aplicam-se exclusivamente a danos ocorridos e reclamados no perímetro indicado na Apólice. 5. RISCOS EXCLUÍDOS 5.1. NÃO EST ÃO GARANTIDAS POR ESTE SEGURO AS QUANTIAS DEVIDAS E/OU AS DESPENDIDAS, PELO SEGURADO, PARA REPARAR, EVIT AR E/OU MINORAR DANOS, DE QUALQUER ESPÉCIE, DECORRENTES: a) De atos ilícitos dolosos praticados pelos sócios controladores do Segurado, por seus dirigentes, administradores, e por representantes destas pessoas; b) De detonação de minas, torpedos, bombas, granadas e outros engenhos de guerra; c) De campos eletromagnéticos e/ou de radiação...

**Critério de sucesso:**

Passa se recuperar trecho de riscos excluídos ou situação expressamente não garantida.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'riscos excluídos'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q009

**Pergunta:**

Como o limite máximo de indenização afeta o pagamento do sinistro na Excelsior?

**Tipo:**

cobertura

**Escopo:**

seguradora

**Seguradora / órgão:**

Excelsior

**Fonte esperada:**

CG_Excelsior-RC-Hangar.pdf, página 21

**Termos esperados:**

limite máximo de indenização; limite máximo; indenização; garantia; cobertura; valor

**Resposta ideal draft:**

de qualquer processo; b) o pagamento de prêmios de seguro garantia para liberar penhoras de quantias não superiores ao Limite Máximo de Indenização (LMI) desta Cobertura, e fianças ou custas necessárias para a defesa em qualquer processo judicial, mas sem qualquer obrigação de contratar ou apresentar tal seguro garantia e fiança; c) os custos recuperáveis contra o Segurado e juros acumulados após o início do julgamento até que a Seguradora tenha pagado, entregue , ou depositado em juízo , parte de tal condenação se não exceder o limite de responsabilidade das Seguradoras. No caso em que o...

**Critério de sucesso:**

Passa se recuperar trecho que descreva cobertura, limite, franquia ou alcance da garantia.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'limite máximo de indenização'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q010

**Pergunta:**

Quais são as principais obrigações do segurado na EZZE?

**Tipo:**

obrigacao

**Escopo:**

seguradora

**Seguradora / órgão:**

EZZE

**Fonte esperada:**

CG_EZZE_Hangar.pdf, página 24

**Termos esperados:**

obrigações do segurado; obrigações; segurado; deveres; sinistro; comunicação

**Resposta ideal draft:**

tem da Proposta de Seguro e daquelas que não lhe tenham sido comunicadas posteriormente, conforme previsto na Cláusula “OBRIGAÇÕES DO SEGURADO”. 11.16 As apólices, os endossos e os certificados eventualmente emitidos terão seu início e término de vigência às 24 (vinte e quatro) horas das datas para tal fim neles indicadas. 11.17 O Segurado, a qualquer tempo, poderá subscrever nova proposta ou solicitar emissão de endosso, para alteração do limite da garantia contratualmente previsto, ficando a critério da Seguradora sua aceitação e alteração do prêmio, quando couber. 11.18 Se houver algum...

**Critério de sucesso:**

Passa se recuperar trecho com deveres ou obrigações do segurado.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'obrigações do segurado'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q011

**Pergunta:**

O que a Resolução CNSP/SUSEP 407/2021 trata sobre grandes riscos?

**Tipo:**

regulatorio

**Escopo:**

regulatorio

**Seguradora / órgão:**

CNSP_SUSEP

**Fonte esperada:**

SUSEP 407_2021.pdf, página 1

**Termos esperados:**

grandes riscos; Resolução 407; SUSEP; CNSP; enquadramento

**Resposta ideal draft:**

os e as características gerais para a elaboração e a comercialização de contratos de seguros de danos para cobertura de grandes riscos. A SUPERINTENDÊNCIA DE SEGUROS PRIVADOS - SUSEP , no uso da atribuição que lhe confere o art. 34, inciso XI, do Decreto no 60.459, de 13 de março de 1967, torna público que o CONSELHO NACIONAL DE SEGUROS PRIVADOS – CNSP , em sessão ordinária realizada em 26 de março de 2021, tendo em vista o disposto no art. 32, incisos I e IV, do Decreto-Lei nº 73, de 21 de novembro de 1966 e na Lei nº 13.874, de 20 de novembro de 2019, e considerando o que consta do...

**Critério de sucesso:**

Passa se recuperar trecho da Resolução CNSP/SUSEP 407/2021 relacionado ao tema.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'grandes riscos'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q012

**Pergunta:**

Quais danos de responsabilidade civil são tratados pela Excelsior?

**Tipo:**

conceitual

**Escopo:**

seguradora

**Seguradora / órgão:**

Excelsior

**Fonte esperada:**

CG_Excelsior-RC-Hangar.pdf, página 17

**Termos esperados:**

responsabilidade civil; danos; terceiros; cobertura; segurado

**Resposta ideal draft:**

tratadas só serão válidas mediante o pagamento do prêmio correspondente e indicação na apólice. II – COBERTURA BÁSICA – RESPONSABILIDADE CIVIL OPERADOR AEROPORTUÁRIO Instalações Aeronáuticas, Aeronaves de Terceiros e Responsabilidade Civil de Produtos – Seções 1, 2 e 3. 1. Riscos Cobertos. Estão cobertos os riscos de: a) danos corporais , incluindo morte em qualquer momento dele resultante (doravante designado por lesão corporal); ou b) danos materiais , causados por acidente ocorrido durante o período de vigência desta apólice e decorrentes dos riscos definidos nas Seções 1, 2 e 3 a...

**Critério de sucesso:**

Passa se recuperar definição ou descrição contratual suficiente do conceito.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'responsabilidade civil'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q013

**Pergunta:**

Quando a seguradora AXA pode recusar um sinistro?

**Tipo:**

sinistro

**Escopo:**

seguradora

**Seguradora / órgão:**

AXA

**Fonte esperada:**

CG_AXA_RC Hangar.pdf, página 18

**Termos esperados:**

recusa de sinistro; recusa; sinistro; indenização; comunicação; seguradora

**Resposta ideal draft:**

a praticar após o Sinistro não im portam, por si só, no reconhecimento da obrigação de pagar qualquer Indenização. 13.4 RECUSA DE SINISTRO 13,4,1 Quando a Seguradora recusar um sinistro, deverá comunicar os motivos da recusa ao Segurado por escrito, dentro do praz o máximo de 30 (trinta) dias, ou em prazo maior determinado pelo Órgão Regulador, contados da entrega da documentação solicitad a.

**Critério de sucesso:**

Passa se recuperar trecho sobre recusa, perda de direito, liquidação, fraude, agravamento de risco ou obrigações em sinistro.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'recusa de sinistro'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q014

**Pergunta:**

Quais exclusões são previstas nas condições gerais da EZZE?

**Tipo:**

exclusao

**Escopo:**

seguradora

**Seguradora / órgão:**

EZZE

**Fonte esperada:**

CG_EZZE_Hangar.pdf, página 17

**Termos esperados:**

exclusões; condições gerais; seguradora; riscos; segurado

**Resposta ideal draft:**

cleares não excluídos por razões do subitem 9.2.2 acima (sujeitos aos demais termos, condições, limitações, garantias e exclusões dessa apólice) deverão ser cobertos desde que: a) no caso de qualquer reclamação em relação a material radioativo no curso do transporte de carga, incluindo armazenamento ou manuseio incidental, tal transporte deverá em todos os aspectos ter obedecido às “Instruções Técnicas para o Transporte Seguro de Mercadorias Perigosas por Ar” da Organização Internacional de Aviação Civil, a menos que o transporte tenha obedecido a uma legislação mais restritiva e, neste...

**Critério de sucesso:**

Passa se recuperar trecho de riscos excluídos ou situação expressamente não garantida.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'exclusões'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q015

**Pergunta:**

Como a franquia é tratada nas condições da AXA?

**Tipo:**

cobertura

**Escopo:**

seguradora

**Seguradora / órgão:**

AXA

**Fonte esperada:**

CG_AXA_RC Hangar.pdf, página 21

**Termos esperados:**

franquia; indenização; valor; cobertura; sinistro

**Resposta ideal draft:**

o individual de cada cobertura como se o respectivo contrato fosse o único vigente, considerando-se, quando for o caso, franquias, participações obrigatórias do Segurado/Representante legal, limite máximo de indenização da cobertura e cláusulas de rateio. II- Será calculada a “indenização individual ajustada” de cada cobertura, na forma abaixo indicada: a) Se, para uma determinada apólice, for verificado que a soma das indenizações correspondentes às diversas coberturas abrangidas pelo sinistro é maior que seu respectivo limite máximo de garantia, a indenização individual de cada cobertura...

**Critério de sucesso:**

Passa se recuperar trecho que descreva cobertura, limite, franquia ou alcance da garantia.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'franquia'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q016

**Pergunta:**

Quais são as principais obrigações do segurado na Mapfre?

**Tipo:**

obrigacao

**Escopo:**

seguradora

**Seguradora / órgão:**

Mapfre

**Fonte esperada:**

CG_Mapfre_RC_HANGAR.pdf, página 15

**Termos esperados:**

obrigações do segurado; obrigações; segurado; deveres; sinistro; comunicação

**Resposta ideal draft:**

nálise de Risco, nem daquelas que não lhe ten ham sido comunicadas posteriormente, na forma estipulada na Cláusula 14 – OBRIGAÇÕES DO SEGURADO. 11.8. O prazo de Vigência da Apólice será aquele indicado nas especificações da Apólice.

**Critério de sucesso:**

Passa se recuperar trecho com deveres ou obrigações do segurado.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'obrigações do segurado'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q017

**Pergunta:**

Qual é o papel da Resolução CNSP/SUSEP 407/2021 no enquadramento do seguro?

**Tipo:**

regulatorio

**Escopo:**

regulatorio

**Seguradora / órgão:**

CNSP_SUSEP

**Fonte esperada:**

SUSEP 407_2021.pdf, página 1

**Termos esperados:**

cnsp; CNSP; SUSEP; regulação; enquadramento; grandes riscos

**Resposta ideal draft:**

MINISTÉRIO DA FAZENDA CONSELHO NACIONAL DE SEGUROS PRIVADOS RESOLUÇÃO CNSP Nº 407, DE 29 DE MARÇO DE 2021. Dispõe sobre os princípios e as características gerais para a elaboração e a comercialização de contratos de seguros de danos para cobertura de grandes riscos. A SUPERINTENDÊNCIA DE SEGUROS PRIVADOS - SUSEP , no uso da atribuição que lhe confere o art. 34, inciso XI, do Decreto no 60.459, de 13 de março de 1967, torna público que o CONSELHO NACIONAL DE SEGUROS PRIVADOS – CNSP , em sessão ordinária realizada em 26 de março de 2021, tendo em vista o disposto no art. 32, incisos I e IV

**Critério de sucesso:**

Passa se recuperar trecho da Resolução CNSP/SUSEP 407/2021 relacionado ao tema.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'cnsp'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q018

**Pergunta:**

O que é responsabilidade civil no seguro aeronáutico segundo a Essor?

**Tipo:**

conceitual

**Escopo:**

seguradora

**Seguradora / órgão:**

Essor

**Fonte esperada:**

CG_Essor_RC Hangar.pdf, página 11

**Termos esperados:**

responsabilidade civil; danos; terceiros; cobertura; segurado

**Resposta ideal draft:**

11 RESPONSABILIDADE CIVIL DE HANGARES E OPERAÇÕES AEROPORTUÁRIAS – CONDIÇÕES GERAIS DIREITOS T udo aquilo que tem existência imaterial e que pode ser objeto de uma relação jurídica. DIREITOS ECONÔMICOS Direitos aos quais pode ser atribuído um valor econômico. DOLO (ó) Má-fé. Qualquer ato consciente por meio do qual alguém induz, mantém ou confirma outrem em erro; vontade conscientemente dirigida com a finalidade de obter um resultado criminoso. DURAÇÃO DO SEGURO Expressão usada para indicar o período de vigência do seguro. EMPREGADO Pessoa

**Critério de sucesso:**

Passa se recuperar definição ou descrição contratual suficiente do conceito.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'responsabilidade civil'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q019

**Pergunta:**

Quando o segurado perde o direito à indenização na AXA?

**Tipo:**

sinistro

**Escopo:**

seguradora

**Seguradora / órgão:**

AXA

**Fonte esperada:**

CG_AXA_RC Hangar.pdf, página 16

**Termos esperados:**

perda de direito; indenização; segurado; conduta; agravamento

**Resposta ideal draft:**

os referidos bens; correrão por conta exclusiva do Segurado as despesas necessárias ao cumprimento dessas medidas. 12- PERDA DE DIREITO 12.1 Além dos casos previstos em lei, e nas demais cláusulas das Condições Contratuais o Segurado perderá o direito a qualquer indenização, bem como terá o seguro cancelado, sem direito a restituição do prêmio já pago, se agravar intencionalmente e de forma relevante o risco. 12.2 Será relevante o agravamento que conduza ao aumento significativo e continuado da probabilidade de realização do risco garantido ou da severidade de seus efeitos. 12.3 O Segurado...

**Critério de sucesso:**

Passa se recuperar trecho sobre recusa, perda de direito, liquidação, fraude, agravamento de risco ou obrigações em sinistro.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'perda de direito'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q020

**Pergunta:**

O que não está garantido pelo seguro da Excelsior?

**Tipo:**

exclusao

**Escopo:**

seguradora

**Seguradora / órgão:**

Excelsior

**Fonte esperada:**

CG_Excelsior-RC-Hangar.pdf, página 17

**Termos esperados:**

riscos excluídos; não garantidos; segurado; danos; operação

**Resposta ideal draft:**

feito nas instalações aeronáuticas, suas vias, oficinas, maquinário ou plantas inerentes ao negócio do Segurado. 1.1.2. Riscos Excluídos. Esta seção está sujeita às seguintes EXCLUSÕES, além do que consta na cláusula “RISCOS EXCLUÍDOS” das Condições Gerais: 1.1.2.1. Perda ou dano aos bens possuídos, alugados, arrendados ou ocupados por; enquanto sob os cuidados, custódia ou controle de; durante a manipulação, a manutenção ou mantidas pelo Segurado ou de qualquer empregado do segurado. Todavia, esta exclusão não será a plicada aos veículos que não sejam de propriedade do Segurado, enquanto...

**Critério de sucesso:**

Passa se recuperar trecho de riscos excluídos ou situação expressamente não garantida.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'riscos excluídos'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q021

**Pergunta:**

Como o limite máximo de indenização afeta o pagamento do sinistro na Mapfre?

**Tipo:**

cobertura

**Escopo:**

seguradora

**Seguradora / órgão:**

Mapfre

**Fonte esperada:**

CG_Mapfre_RC_HANGAR.pdf, página 21

**Termos esperados:**

limite máximo de indenização; limite máximo; indenização; garantia; cobertura; valor

**Resposta ideal draft:**

o Sinistro. 16.2.7. Em qualquer caso, independentemente do valor dos prejuízos, a Inde nização não poderá ultrapassar o Limite Máximo de Indenização por cobertura, nem o Limite Máximo de Garantia fixados na Apólice. 16.3. CONVERSÃO CAMBIAL PARA SINISTROS PARCIAIS: 16.3.1. Nos casos de sinistros com prejuízos parciais, referentes as apólices emitidas em dóla res norteamericanos (USD), a conversão dos valores em moeda nacional para dólare s norte-americanos será realizada com base na taxa de câmbio de venda do dólar comercial, vigen te na data do desembolso das despesas efetivamente...

**Critério de sucesso:**

Passa se recuperar trecho que descreva cobertura, limite, franquia ou alcance da garantia.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'limite máximo de indenização'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q022

**Pergunta:**

Quais são as principais obrigações do segurado na AXA?

**Tipo:**

obrigacao

**Escopo:**

seguradora

**Seguradora / órgão:**

AXA

**Fonte esperada:**

CG_AXA_RC Hangar.pdf, página 15

**Termos esperados:**

obrigações do segurado; obrigações; segurado; deveres; sinistro; comunicação

**Resposta ideal draft:**

tárias a partir da data de recebimento, até a data da devolução, com base na variação positiva do índice IPCA/IBGE. 11- OBRIGAÇÕES DO SEGURADO 11.1 - O Segurado se obriga: a) a dar imediato aviso à Seguradora, por carta registrada ou protocolada, da ocorrência de qualquer evento que, nos termos deste seguro, possa acarretar a reivindicação da garantia, tão logo dele tome conhecimento; b) a tomar todas as providências consideradas inadiáveis e ao seu alcance, para tentar evitar e/ou minorar os danos causados a terceiros;

**Critério de sucesso:**

Passa se recuperar trecho com deveres ou obrigações do segurado.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'obrigações do segurado'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q023

**Pergunta:**

Quais danos de responsabilidade civil são tratados pela EZZE?

**Tipo:**

conceitual

**Escopo:**

seguradora

**Seguradora / órgão:**

EZZE

**Fonte esperada:**

CG_EZZE_Hangar.pdf, página 13

**Termos esperados:**

responsabilidade civil; danos; terceiros; cobertura; segurado

**Resposta ideal draft:**

ressamente mencionadas na Especificação da Apólice e nas Condições Especiais e Particulares) i) COBERTURA BÁSICA Nº 1 – RESPONSABILIDADE CIVIL DE HANGARES, INSTALAÇÕES AERONÁUTICAS E DANOS A AERONAVES DE TERCEIROS (SEÇÕES 1 E 2) ii) COBERTURA BÁSICA Nº 2 – RESPONSABILIDADE CIVIL DE PRODUTOS AERONÁUTICOS (SEÇÃO 3) iii) COBERTURA BÁSICA Nº 3 – RESPONSABILIDADE CIVIL PARA ADMINISTRADORES DE AEROPORTOS (AVN 104)

**Critério de sucesso:**

Passa se recuperar definição ou descrição contratual suficiente do conceito.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'responsabilidade civil'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q024

**Pergunta:**

Como funciona a liquidação de sinistros na Essor?

**Tipo:**

sinistro

**Escopo:**

seguradora

**Seguradora / órgão:**

Essor

**Fonte esperada:**

CG_Essor_RC Hangar.pdf, página 14

**Termos esperados:**

liquidação de sinistros; liquidação; sinistro; documentos; indenização; prazo

**Resposta ideal draft:**

es máximos de indenização estabelecidos para coberturas distintas são independentes, não se somando nem se comunicando. LIQUIDAÇÃO DE SINISTROS Pagamento da indenização (ou reembolso) relativa a um sinistro. LOCK-OUT Paralisação dos serviços ou atividades de uma empresa ou empresas de atividades afins, por determinação de seus administradores ou do sindicato patronal respectivo. LUCROS CESSANTES São lucros que deixam de ser auferidos devido à paralisação de atividades e do movimento de negócios do Segurado, ou do terceiro prejudicado, no caso de Seguro de Responsabilidade Civil. Os “lucros...

**Critério de sucesso:**

Passa se recuperar trecho sobre recusa, perda de direito, liquidação, fraude, agravamento de risco ou obrigações em sinistro.

**Nível de dificuldade:**

medio

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'liquidação de sinistros'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---

## Q025

**Pergunta:**

O que não está garantido pelo seguro da EZZE?

**Tipo:**

exclusao

**Escopo:**

seguradora

**Seguradora / órgão:**

EZZE

**Fonte esperada:**

CG_EZZE_Hangar.pdf, página 14

**Termos esperados:**

riscos excluídos; não garantidos; segurado; danos; operação

**Resposta ideal draft:**

ntratadas isoladamente. 8.3.1 só serão válidas mediante o pagamento do prêmio correspondente e indicação na apólice. 9. RISCOS EXCLUÍDOS 9.1 NÃO ESTÃO GARANTIDOS POR ESTE SEGURO AS QUANTIAS DEVIDAS E/OU AS DESPENDIDAS, PELO SEGURADO, PARA REPARAR, EVITAR E/OU MINORAR DANOS, DE QUALQUER ESPÉCIE, DECORRENTES DE: a) de detonação de minas, torpedos, bombas, granadas e outros engenhos de guerra; b) de campos eletromagnéticos e/ou de radiação eletromagnética; c) de arresto, sequestro, detenção, embargo, penhora, ocupação, apreensão, confisco, nacionalização, destruição ou requisição, ordenadas...

**Critério de sucesso:**

Passa se recuperar trecho de riscos excluídos ou situação expressamente não garantida.

**Nível de dificuldade:**

facil

**Status:**

aprovado_preliminar

**Observações:**

Pergunta gerada automaticamente a partir do gatilho 'riscos excluídos'. Revisar pergunta, resposta e termos antes de aprovar. Selecionado automaticamente para revisão v1. Confirmar fonte, página e resposta ideal antes de aprovar.

**Observações de revisão:**

ok para avaliação preliminar

---
