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
    background = filter_img(opened_img, kernel_size=13, filter_type="mean")
    background = filter_img(background, kernel_size=15, filter_type="gaussian")
    background = filter_img(background, kernel_size=60, filter_type="median")

    return background


def pre_process(image):
    image_g = image[:, :, 1].astype(np.uint8)
    image_g = opening(image_g, np.ones((13, 13)))
    background = calculate_background(image_g)

    diff_img = image_g.astype(np.int64) - background.astype(np.int64)
    # min max
    diff_img = ((diff_img - np.min(diff_img)) /
                (np.max(diff_img) - np.min(diff_img))*255).astype(np.uint8)
    return diff_img


def process_threshold(diff_img):
    return cv2.adaptiveThreshold(diff_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 5)


def remove_small_areas(img, min_area):
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
    threshold_img = opening(closing(threshold_img.astype(
        np.uint8), np.ones((7, 7))), np.ones((3, 3)))
    reduced_threshold = remove_small_areas(threshold_img, 150)
    return reduced_threshold, skeletonize(reduced_threshold.astype(bool))


def mark_potential_landmark(skeleton_img):
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
    widths = []
    for x, y, mark_type in landmarks:
        # down
        i = x
        j = y
        vert_dist = 0
        while(j < 1600 and threshold_img[i, j] != 0):
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
        while(i < 1600 and threshold_img[i, j] != 0):
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
        while(i < 1600 and j < 1600 and threshold_img[i, j] != 0):
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
        while(i >= 0 and j < 1600 and threshold_img[i, j] != 0):
            i -= 1
            j += 1
            p_diag_dist += 1

        # up right
        i = x
        j = y
        while(i < 1600 and j >= 0 and threshold_img[i, j] != 0):
            i += 1
            j -= 1
            p_diag_dist += 1
        min_width = np.min([vert_dist, horiz_dist, p_diag_dist, s_diag_dist])
        widths.append([(x, y), np.ceil(min_width).astype(int), mark_type])
    return widths


def make_circle(diameter):
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


def mark_intersections_and_intersections(widths, skeleton_img):
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
    final_img = original_img.copy()
    for (y, x) in bifurcations:
        cv2.rectangle(final_img, (x-10, y-10), (x+10, y+10), (0, 0, 255), 2)
    for (y, x) in intersections:
        cv2.rectangle(final_img, (x-10, y-10), (x+10, y+10), (0, 255, 0), 2)
    return final_img


def calculate_bifurcations(skeleton, denoised, original_img):
    landmarks = mark_potential_landmark(skeleton)
    junction_widths = calculate_widths(denoised, landmarks)
    bifurcations, intersections = mark_intersections_and_intersections(
        junction_widths, skeleton)
    return draw_bifurcations(original_img, bifurcations, intersections)


def main():
    if len(sys.argv) < 2:
        print("Image path must be provided")
        return

    image_path = str(sys.argv[1])
    image = imageio.imread(image_path)
    diff_img = pre_process(image)
    threshold_img = process_threshold(diff_img)
    denoised, skeleton = post_process(threshold_img)
    final_img = calculate_bifurcations(skeleton, denoised, image)
    imageio.imwrite(image_path.split('.')[0]+"final.jpg", final_img)


if __name__ == "__main__":
    main()
