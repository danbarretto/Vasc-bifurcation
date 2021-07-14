'''
Projeto final: Uso de Segmentação de Imagens para Identificação de Bifurcações em Vasos Sanguíneos em Imagens de Retina
Alunos:
    Alexandre Galocha Pinto Junior (10734706) -SCC0251- BCC 2018 (4º ano/7º semestre)
    Daniel Sá Barretto Prado Garcia (10374344) -SCC0251- BCC 2018 (4º ano/7º semestre)
'''
import imageio
import numpy as np
from scipy.ndimage.filters import median_filter, convolve
from skimage.morphology import opening, closing, skeletonize
from skimage.filters import gaussian
from skimage import measure
import sys

import cv2


def filter_img(img, kernel_size=3, filter_type="mean"):
    """
        Realiza a filtragem de uma imagem, utilizando um dos três filtros:
        média, mediana ou gaussiano.

        :param img: imagem a ser filtrada
        :param kernel_size: tamanho do filtro (lado)
        :param filter_type: tipo do filtro ("mean" | "median" | "gaussian")

        :return: imagem filtrada com o filtro especificado
    """
    if filter_type == "mean":
        weights = np.full((kernel_size, kernel_size), 1.0/(kernel_size**2))
        return convolve(img, weights=weights, mode="constant", cval=0)
    elif filter_type == "median":
        return median_filter(img, size=kernel_size)
    elif filter_type == "gaussian":
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[kernel_size//2, kernel_size//2] = 1
        kernel = gaussian(kernel, sigma=1, mode='reflect')
        return convolve(img, weights=kernel, mode="constant", cval=0)
    else:
        print('Error! Filter should be either mean, median or gaussian!')
        return None


def calculate_background(opened_img):
    """
        Calcula o background de uma imagem, borrando, para perder os detalhes.

        :param opened_img: imagem da qual será calculado o background

        :return: background da imagem
    """
    background = filter_img(opened_img, kernel_size=13, filter_type="mean")
    background = filter_img(background, kernel_size=15, filter_type="gaussian")
    background = filter_img(background, kernel_size=60, filter_type="median")

    return background


def pre_process(image):
    """
        Realiza o pré-processamento de uma imagem de exame de retina, removendo
        o background e sombras/brilhos através de aberturas.

        :param image: imagem do exame de retina a ser processada

        :return: imagem com background removido e sombras/brilhos diminuídos
    """
    image_g = image[:, :, 1].astype(np.uint8)
    image_g = opening(image_g, np.ones((13, 13)))
    background = calculate_background(image_g)

    diff_img = image_g.astype(np.int64) - background.astype(np.int64)
    # min max
    diff_img = ((diff_img - np.min(diff_img)) /
                (np.max(diff_img) - np.min(diff_img))*255).astype(np.uint8)
    return diff_img


def process_threshold(diff_img):
    """
        Realiza a segmentação da imagem utilizando um threshold adaptativo.

        :param diff_img: imagem já pré-processada, da qual será realizada a
            segmentação

        :return: imagem segmentada com threshold adaptativo
    """
    return cv2.adaptiveThreshold(diff_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 41, 5)


def remove_small_areas(img, min_area):
    """
        Segmenta uma imagem em várias regiões com propriedades em comum e gera
        uma imagem resultado, deixando de fora todas as regiões que possuam
        areas menores do que o limiar passado. Esse processo é realizado para
        remover áreas pequenas (no geral barulho).
        OBS: essa função foi inspirada no artigo que pode ser encontrado no
        link abaixo (medium).

        :param img: imagem a ser processada
        :param min_area: area minima das regiões utilizadas nas geração da
            imagem resultado

        :return: imagem com as areas pequenas removidas
    """
    # https://medium.com/swlh/image-processing-with-python-connected-components-and-region-labeling-3eef1864b951
    label_img = measure.label(img, background=0, connectivity=2)
    regions = measure.regionprops(label_img)

    masks = []
    bbox = []
    list_of_index = []
    for num, x in enumerate(regions):
        area = x.area
        if (area > min_area):
            masks.append(regions[num].convex_image)
            bbox.append(regions[num].bbox)
            list_of_index.append(num)

    for box, mask in zip(bbox, masks):
        reduced_img = img[box[0]:box[2], box[1]:box[3]] * mask

    mask = np.zeros_like(label_img)
    for x in list_of_index:
        mask += (label_img == x+1).astype(int)
    reduced_img = img * mask

    return reduced_img


def post_process(threshold_img):
    """
        Realiza o pós-processamento da imagem após a segmentação da mesma. A
        realização do closing e opening (como explicado no relatório) são para
        melhorar as ligações entre os vasos e remover parte do ruido,
        respectivamente. Após esses operadores morfológicos, a função de remoção
        de pequenas áreas é utilizada para remover o resto do barulho da imagem.
        Além disso é gerado um esqueleto da imagem que será utilizado para
        marcação de potenciais bifurcações e verificação do mesmo.

        :param threshold_img: imagem já segmentada (binária)

        :return: imagem com remoção de barulho e imagem esqueletizada
    """
    threshold_img = opening(closing(threshold_img.astype(
        np.uint8), np.ones((7, 7))), np.ones((3, 3)))
    reduced_threshold = remove_small_areas(threshold_img, 150)
    return reduced_threshold, skeletonize(reduced_threshold.astype(bool))


def mark_potential_landmark(skeleton_img):
    """
        Realiza a marcação das potenciais bifurcações ou intersecções de vasos
        na imagem. Isso é feito através da aplicação de uma máscara, buscando
        pontos da imagem que possuam 3 (bifurcação) ou 4 (intersecção) linhas
        saindo. A máscara utilizada é uma 3x3, que obteve um melhor resultado.

        :param skeleton_img: imagem esqueletizada para marcação

        :return: conjunto de potenciais pontos com bifurcações ou intersecções
    """
    size = 3
    a = size//2
    mask = np.ones((size, size))
    mask[1:-1, 1:-1] = 0
    mask = mask.astype(bool)
    N, M = skeleton_img.shape
    landmarks = []
    coords = np.argwhere(skeleton_img)
    for (x, y) in coords:
        # inside circle
        if(x-a < 0 or y-a < 0 or x+a+1 > N or y+a+1 > M):
            continue
        sub_img = skeleton_img[x-a:x+a+1, y-a:y+a+1]
        img_sum = np.sum(np.bitwise_and(sub_img, mask))
        if(img_sum == 3 or img_sum == 4):
            landmarks.append((x, y, img_sum))
    return landmarks


def calculate_widths(threshold_img, landmarks):
    """
        Calcula a largura dos vasos sanguíneos nos pontos de potenciais
        bifurcação. Esse cálculo é feito pegando a menor distância percorrida
        a partir do ponto em cada uma das direções (8 direções são utilizadas).
        A função retorna o que seria equivalente ao diametro do vasos em cada 
        ponto.

        :param threshold_img: imagem (binária) usada para calculo da largura dos 
            vasos sanguíneos
        :param landmarks: pontos onde calcular as larguras

        :return: vetor com larguras de cada um dos pontos (diametro dos vasos)
    """
    N, M = threshold_img.shape

    widths = []
    for x, y, mark_type in landmarks:
        # down
        i = x
        j = y
        vert_dist = 0
        while(j < M and threshold_img[i, j] != 0):
            vert_dist += 1
            j += 1

        # up
        i = x
        j = y
        while(j >= 0 and threshold_img[i, j] != 0):
            vert_dist += 1
            j -= 1

        # right
        horiz_dist = 0
        i = x
        j = y
        while(i < N and threshold_img[i, j] != 0):
            horiz_dist += 1
            i += 1

        # left
        i = x
        j = y
        while(i >= 0 and threshold_img[i, j] != 0):
            horiz_dist += 1
            i -= 1

        # down right
        i = x
        j = y
        s_diag_dist = 0
        while(i < N and j < M and threshold_img[i, j] != 0):
            i += 1
            j += 1
            s_diag_dist += 1

        # up left
        i = x
        j = y
        while(i >= 0 and j >= 0 and threshold_img[i, j] != 0):
            i -= 1
            j -= 1
            s_diag_dist += 1

        # down left
        i = x
        j = y
        p_diag_dist = 0
        while(i >= 0 and j < M and threshold_img[i, j] != 0):
            i -= 1
            j += 1
            p_diag_dist += 1

        # up right
        i = x
        j = y
        while(i < N and j >= 0 and threshold_img[i, j] != 0):
            i += 1
            j -= 1
            p_diag_dist += 1

        min_width = np.min([vert_dist, horiz_dist, p_diag_dist, s_diag_dist])
        widths.append([(x, y), np.ceil(min_width).astype(int), mark_type])
    return widths


def make_circle(diameter):
    """
        Cria uma máscara circular (circulo vazio, apenas a borda) de acordo com
        o diâmetro escolhido.

        :param diameter: diametro do circulo

        :return: matriz diametro X diametro com o circulo desenhado
    """
    diameter += 2

    radius = diameter // 2

    circle = np.zeros((diameter, diameter)).astype(np.uint8)
    c = radius
    y, x = np.ogrid[-radius:radius, -radius:radius]
    index = x ** 2 + y ** 2 < radius ** 2
    circle[c - radius:c + radius, c - radius: c + radius][index] = 1

    diameter_in = diameter - 2
    radius_in = diameter_in // 2

    inside = np.zeros((diameter, diameter)).astype(np.uint8)
    c = radius
    y, x = np.ogrid[-radius:radius, -radius:radius]
    index = x ** 2 + y ** 2 < radius_in ** 2
    inside[c - radius:c + radius, c - radius: c + radius][index] = 1

    return np.bitwise_xor(circle, inside)[1:-1, 1:-1]


def validate_bifurcations_and_intersections(widths, skeleton_img):
    """
        Marca as intersecções e bifurcações verificando se de fato existem por
        meio das larguras de cada vaso sanguíneo calculadas. O processo é de
        desenhar um circulo com raio 1.5 vezes a largura do vaso em cada um dos
        pontos candidatos e verificar se existe o número certo de intersecções
        (no caso de bifurcações são 3 e intersecções, 4) entre o circulo e os
        traços definidos na imagem esqueletizada.

        :param widths: vetor com as larguras em cada um dos pontos
        :param skeleton_img: imagem esqueletizada para verificação

        :return: vetor com os pontos de bifurcação e vetor com os pontos de
            intersecção.
    """
    bifurcations = []
    intersections = []
    for (x, y), width, mark_type in widths:
        diam = 3 * width
        diam += 1 if diam % 2 == 0 else 0
        radius = diam // 2
        if(x-radius < 0 or y-radius < 0 or x+radius+1 > skeleton_img.shape[0] or y+radius+1 > skeleton_img.shape[1]):
            continue
        circle = make_circle(diam)
        sub_img = skeleton_img[x-radius:x+radius +
                               1, y-radius:y+radius+1].astype(bool)
        circle_sum = np.sum(np.bitwise_and(sub_img, circle))
        if(circle_sum == 3 and mark_type == 3):
            bifurcations.append((x, y))
        elif(circle_sum == 4 and mark_type == 4):
            intersections.append((x, y))
    return bifurcations, intersections


def draw_bifurcations(original_img, bifurcations, intersections):
    """
        Recebe os pontos em que existem bifurcações e intersecções nos vasos e
        os desenha na imagem passada. As marcações são feitas por quadrados com
        lado 20 pixels. Os quadrados azuis representam bifurcações, enquanto os
        verdes representam as intersecções.

        :param original_img: imagem original do exame de retina para marcação
        :param bifurcations: vetor com os pontos de bifurcação
        :param intersections: vetor com os pontos de intersecção

        :return: imagem com os pontos marcados
    """
    final_img = original_img.copy()
    for (y, x) in bifurcations:
        cv2.rectangle(final_img, (x-10, y-10), (x+10, y+10), (0, 0, 255), 2)
    for (y, x) in intersections:
        cv2.rectangle(final_img, (x-10, y-10), (x+10, y+10), (0, 255, 0), 2)
    return final_img


def calculate_bifurcations(skeleton, denoised, original_img):
    """
        Realiza o processo de calculo e marcação das bifurcações e intersecções
        presentes em um exame de retina. O processo utiliza o esqueleto da
        imagem para gerar pontos candidatos. Então verifica se os candidatos são
        de fato os pontos procurados se utilizando da largura calculada dos
        vasos sanguíneos em cada um desses pontos. Então, utilizando esses
        resultados, são desenhados os pontos na imagem.

        :param skeleton: imagem esqueletizada utilizada no calculo das
            bifurcações e intersecções
        :param denoised: imagem binária com os vasos, para calculo das larguras
        :param original_img: imagem original sobre a qual serão desenhados os
            pontos de bifurcação e intersecção

        :return: imagem com bifurcações e intersecções marcadas em azul e verde
            respectivamente
    """
    landmarks = mark_potential_landmark(skeleton)
    junction_widths = calculate_widths(denoised, landmarks)
    bifurcations, intersections = validate_bifurcations_and_intersections(
        junction_widths, skeleton)
    return draw_bifurcations(original_img, bifurcations, intersections)


def main():
    if len(sys.argv) != 2:
        print("Image path must be provided")
        print("Usage: python3 vasc_bifurcation.py <image_path>")
        return

    try:
        image_path = str(sys.argv[1])
        image = imageio.imread(image_path)
        diff_img = pre_process(image)
        threshold_img = process_threshold(diff_img)
        denoised, skeleton = post_process(threshold_img)
        final_img = calculate_bifurcations(skeleton, denoised, image)
        imageio.imwrite(image_path.split('.')[0]+"_calculated.jpg", final_img)
    except FileNotFoundError:
        print(f"File '{image_path}' not found")
    except:
        print("Runtime error.")


if __name__ == "__main__":
    main()
