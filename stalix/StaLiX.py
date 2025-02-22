import numpy as np
from scipy.signal import find_peaks

STAFF_LINES_IN_STAFF = 5


def binarize_image_from_array(img: np.ndarray, threshold=200) -> np.ndarray:
    """
    Convert the image to binary using a given threshold.

    :param img: image to be binarized, already loaded
    :param threshold: threshold to use for binarization
    :return: binarized image
    """
    binary = np.where(img > threshold, 255, 0).astype(np.uint8)
    return binary


def find_peaks_binary(binary_img: np.ndarray) -> np.ndarray:
    """
    Find peaks in rows of binary image.
    """
    black_pixel_counts = np.sum(binary_img == 0, axis=1)
    # find peaks (suspicious regions) using scipy
    valleys, properties = find_peaks(black_pixel_counts, prominence=100)

    # search fails
    if valleys is None or np.size(valleys) < STAFF_LINES_IN_STAFF:
        return np.array([])

    # np.size(valleys) >= STAFF_LINEX_IN_STAFF
    else:
        valleys: np.ndarray
        top_indices = np.argpartition(properties["prominences"], -STAFF_LINES_IN_STAFF)[-STAFF_LINES_IN_STAFF:]
        deepest_valleys = valleys[top_indices]

    return np.sort(deepest_valleys)


def staff_space_stddev(staff_y: np.ndarray) -> np.floating:
    """
    Normalizes given staff line y coordinates and computes their standard deviation.

    :param staff_y: staff line y coordinates
    :return: normalized std dev
    """
    assert len(staff_y) > 1 and staff_y.ndim == 1
    normalized = (staff_y - staff_y[0]) / staff_y[-1]
    diff = np.diff(normalized)
    return np.std(diff)


def check_proposed_staff_lines(
        staff_y: np.ndarray,
        crop_height: int,
        space_stddev_threshold: float = 0.02,
        shift_threshold_factor: float = 0.25,
        verbose: bool = False
) -> bool:
    """
    Checks proposed y coordinates for staff lines. Returns true if
    there are five staff lines,
    std dev of spaces between them is less than the threshold
    and if the proposed shifts of bounding box are less than the threshold.

    :param staff_y: staff line y coordinates
    :param crop_height: height of the cropped images (bbox height)
    :param space_stddev_threshold: threshold of std dev of staff line spacing
    :param shift_threshold_factor: shift threshold factor
    :param verbose: make script verbose
    :return: true if proposed staff lines pass all checks
    """
    # valid staff line system
    if len(staff_y) == STAFF_LINES_IN_STAFF and staff_space_stddev(staff_y) < space_stddev_threshold:
        top_offset = staff_y[0]
        bottom_offset = staff_y[-1]
        top_change, bottom_change = top_offset, crop_height - bottom_offset
        shift_limit = crop_height * shift_threshold_factor

        # shift is too large
        if top_change > shift_limit or bottom_change > shift_limit:
            if verbose:
                print(f"Proposed shift is too large: {top_change} > {shift_limit} or {bottom_change} > {shift_limit}")
            return False
        else:
            return True

    if verbose:
        print(
            f"Missing staff lines or std dev over threshold:"
            f"{len(staff_y)}, {staff_space_stddev(staff_y) if len(staff_y) > 1 else 'std err'}"
        )
    return False


def _refactor_single_measure_viz(
        cropped_image: np.ndarray,
        staff_y: np.ndarray,
        fig_width: int = 12
):
    import matplotlib.pyplot as plt

    height, width = cropped_image.shape
    # fixed aspect ratio
    fig_height = int(fig_width * (height / width))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fig_width, fig_height), sharey=True)

    # left plot, binarized image
    ax1.imshow(cropped_image, cmap="gray", origin="upper", aspect="auto")
    ax1.set_title("Binarized Image")

    # right plot, black pixel count
    black_pixel_counts = np.sum(cropped_image == 0, axis=1)
    x = np.arange(len(black_pixel_counts))
    ax2.plot(black_pixel_counts, x, color="blue")
    ax2.scatter(black_pixel_counts[staff_y], staff_y, color="red")
    ax2.set_title("Detected Staff Lines")
    ax2.grid(True)

    # horizontal red lines
    for valley in staff_y:
        ax2.axhline(y=valley, color="r", linestyle="-")
        ax1.axhline(y=valley, color="r", linestyle="-")

    # fix axis rotation and alignment
    ax1.set_ylim(0, height)
    ax2.set_ylim(0, height)
    ax2.invert_yaxis()  # convert from cv2 coordinate system

    # keep aspect ratios and match them
    for sp in [ax1, ax2]:
        sp.set_aspect("auto")

    plt.tight_layout()
    plt.show()


def compute_shift_for_measure(
        cropped_image: np.ndarray,
        bin_threshold: int = 200,
        space_stddev_threshold: float = 0.02,
        shift_threshold_factor: float = 0.25,
        verbose: bool = False,
        visualize: bool = False
) -> tuple[int, int]:
    """
    Proposes shifts for bounding box of inputted image if conditions are met.

    Binarizes image and finds peaks in sums over black pixels in its horizontal rows.
    If staff space height have std dev less than ``space_stddev_threshold``
    and the proposed shifts are not bigger than ``shift_threshold_factor`` times the cropped image height,
    the proposed shift from top and bottom is returned
    as two positive numbers in the format ``(top_shift, bottom_shift)``.

    If no viable shift is found, ``(0, 0)`` will be returned.

    :param cropped_image: loaded gray image
    :param bin_threshold: threshold to use for binarization
    :param space_stddev_threshold: staff space height std dev threshold
    :param shift_threshold_factor: maximal allowed shift
    :param verbose: make script verbose
    :param visualize: visualize process
    """
    crop_height = cropped_image.shape[0]
    binary = binarize_image_from_array(cropped_image, threshold=bin_threshold)
    staff_y = find_peaks_binary(binary)
    if check_proposed_staff_lines(
            staff_y,
            crop_height,
            space_stddev_threshold=space_stddev_threshold,
            shift_threshold_factor=shift_threshold_factor,
            verbose=verbose
    ):
        top_shift = int(staff_y[0])
        bottom_shift = crop_height - int(staff_y[-1])

        if verbose:
            print(f"Refactoring image bounding box: {top_shift=}, {bottom_shift=}")
        if visualize:
            _refactor_single_measure_viz(binary, staff_y)

        return top_shift, bottom_shift

    return 0, 0
