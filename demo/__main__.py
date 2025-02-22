import cv2

from stalix import compute_shift_for_measure

SOURCE = "demo/demo-image.png"

loaded_image = cv2.imread(SOURCE, cv2.IMREAD_GRAYSCALE)

top_shift, bottom_shift = compute_shift_for_measure(
    loaded_image,
    visualize=True
)

print(f"{top_shift=}, {bottom_shift=}")
