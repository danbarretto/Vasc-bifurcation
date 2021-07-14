# Uso de Segmentação de Imagens para Identificação de Bifurcações em Vasos Sanguíneos em Imagens de Retina

* Daniel Sá Barretto Prado Garcia 10374344
* Alexandre Galocha Pinto Jr 10734706

## Resumo do projeto
### Objetivo
O projeto busca identificar bifurcações de vasos sanguíneos em imagens de exames 
de retina para auxiliar o diagnóstico de doenças como glaucoma e diabetes. A
ideia principal é processar as imagens de exames de retina para obter imagens
com maior facilidade de identificação de bifurcação nos vasos sanguíneos e a 
partir dessas imagens processadas, calcular as bifurcações. Também serão calculadas
intersecções como resultado dos cálculos realizados e devido a facilidade de detecção.

### Métodos a serem utilizados
O projeto utilizará segmentação de imagem para identificar os vasos sanguíneos e, em seguida, suas bifurcações. Também serão utilizadas técnicas de filtragem e morfológicas para remoção de ruído e correção de cores e sombras. 
Os métodos são bem melhor especificados no notebook, onde existem descrições acima de cada bloco de código.

### Exemplos de imagens a serem utilizadas
As imagens utilizadas como entrada para o processamento são de exames de retina
(retinografia) obtidas no site da empresa [Phelcom](https://phelcom.com) 
(importante evidenciar que um dos membros da dupla atualmente trabalha na 
empresa e pediu permissão pra uso das imagens). Nessas imagens é possível ver a 
retina do olho com todos os seus vasos sanguíneos e as respectivas bifurcações. 

Exemplos de imagens de entrada podem ser vistos abaixo:
![](./images/1.jpg)
![](./images/2.jpg)
![](./images/3.jpg)
![](./images/4.jpg)

### Descrição das Etapas
Algumas das etapas realizadas foram:
1. Processamento inicial
    * Primeiramente foi separado o canal verde da imagem já que é o que mais possui informação sobre os vasos sanguíneos.
    * Em seguida, realiza-se uma operação de *opening* da imagem para remover certas reflexões.
    * O *background* da imagem é calculado com a aplicação sequêncial dos filtros de média, mediana e gaussiano com diferentes tamanhos de *kernel* sobre a imagem que sofreu a operação de *opening*.
    * Subtrai-se então o *background* da imagem de *opening*, afim de obter uma imagem resultante que trouxesse apenas os vasos sanguíneos (ou linhas no geral, por exemplo o contorno do olho). 
2. Segmentação
    * O processo de segmentação foi realizado por meio de um *threshold* adaptativo gaussiano, que visa trazer uma imagem mais pura, mostrando apenas os vasos. Mesmo assim, a imagem ainda apresenta ruído
3. Pós-Processamento
    * Foram realizadas operações morfológicas como abertura e fechamento da imagem a fim de obter uma imagem com menos ruído e com vasos melhor conectados, o que se mostrou bastante promissor, uma vez que removeu bastante ruído sem perca de muita informação dos vasos.
    * Com auxílio da biblioteca *skimage*, foi possível identificar as regiões conectadas da imagem. Deste modo foi possível filtrar estas regiões pela área total e montar uma imagem com menos ruído. 
    * Foi gerada uma esqueletização da imagem para mais fácil identificação dos vasos.
4. Identificação das Bifurcações
    * Foram calculados vários pontos candidatos a serem bifurcações com dados da vizinhança de cada pixel do esqueleto. Quando existiam 3 pixels brancos, era um candidato a bifurcação; quando existiam 4, intersecção.
    * Foram utilizadas as larguras de cada um dos vasos sanguíneos para verificar os candidatos
        * Era gerado em cada ponto um circulo de raio 1.5*L (L sendo a largura calculada);
        * Caso o circulo intersecte com o esqueleto em 3 pontos, é uma bifurcação; caso em 4, intersecção; caso contrário, não é nenhum dos dois.

Cada uma das etapas é descrita muito mais detalhadamente no notebook, onde explicamos inclusive o motivo de dadas escolhas.

Exemplo de imagem de saída
![](images/2_expected.jpg)
Na imagem acima, as bifurcações são marcadas com quadrados azuis e as intersecções de vasos são marcadas com quadrados vermelhos.

As bifurcações calculadas pelo nosso processamento para essa mesma imagem são mostradas abaixo. Nela os quadrados azuis são bifurcações e os verdes intersecções (utilizamos verde nesse caso para melhor visualização).
![](images/2_calculated.jpg)

### Papéis dos Alunos
Ambos os alunos implementaram código, e basicamente todo o trabalho foi desenvolvido em conjunto, compartilhando tela em uma chamada de vídeo. Escolhemos realizar o trabalho dessa forma para evitar conflitos de merge com o notebook, devido ao fato de termos usado a ferramenta para o desenvolvimento quase total. As documentações também foram praticamente igualmente divididas entre os alunos.
