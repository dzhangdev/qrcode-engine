"""
Title: QR Code lite
Author: David Zhang
Date: 8/19/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

import os
import glob
import re
from PIL import Image
import numpy as np

from qrlite.params import MIN_VERSION, MAX_VERSION
from qrlite.params import NUM_ERROR_CORRECTION_BLOCKS, ECC_CODEWORDS_PER_BLOCK


def rsComputeDivisor(degree):
    """Returns a RS ecc generator polynomial for the given degree."""
    assert 1 <= degree <= 255, "Degree out of range"
    # Polynomial coefficients are stored from highest to lowest power,
    # excluding the leading term which is always 1.
    # For example the polynomial x^3 + 255x^2 + 8x + 93 is stored as
    # the uint8 array [255, 8, 93].
    result = [0] * (degree - 1) + [1]  # Start off with the monomial x^0

    # Comments like this are good
    # Compute the product polynomial
    # (x - r^0) * (x - r^1) * (x - r^2) * ... * (x - r^{degree-1}),
    # and drop the highest monomial term which is always 1x^degree.
    # Note that r = 0x02,
    #   which is a generator element of this field GF(2^8/0x11D).
    root = 1
    for _ in range(degree):  # Unused variable i
        # Multiply the current product by (x - r^i)
        for j in range(degree):
            result[j] = _rsMultiply(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _rsMultiply(root, 0x02)
    return result


def _rsMultiply(a, b):
    """ Return the product of the multiplication """
    # <www.wikipedia.org/wiki/Finite_field_arithmetic#C_programming_example>
    p = 0
    while a and b:
        if b & 1:
            p ^= a
        if a & 128:
            a = (a << 1) ^ 285
        else:
            a <<= 1
        b >>= 1
    return p


def rsComputeRemainder(data, divisor):
    """Returns the RS ec codeword for given data and divisor polynomials."""
    result = [0] * len(divisor)
    for b in data:  # Polynomial division
        factor = b ^ result.pop(0)
        result.append(0)
        for (i, coef) in enumerate(divisor):
            result[i] ^= _rsMultiply(coef, factor)
    return result


def countRawDataModules(ver):
    """
    Returns the number of data bits that can be stored in a QR Code.
    This includes remainder bits, so it might not be a multiple of 8.
    The result is in the range [208, 29648]. This could be implemented as
    a 40-entry lookup table.
    """
    if not (MIN_VERSION <= ver <= MAX_VERSION):
        raise ValueError("Version number out of range")
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        numalign = ver // 7 + 2
        result -= (25 * numalign - 10) * numalign - 55
        if ver >= 7:
            result -= 36
    return result


def countDataCodewords(ver, ecl):
    """ Returns # of codewords contained in any QR Code with remainder
    bits discarded """
    return countRawDataModules(ver) // 8 \
           - ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver] \
           * NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver]


class BitBuffer(list):
    """An appendable sequence of bits (0s and 1s). Mainly used by QrSegment."""

    def append_bits(self, k, n):
        """ Appends n number of low-order bits of k value to the buffer
        Requires n >= 0 and 0 <= val < 2^n."""
        if n < 0 or k >> n != 0:
            raise ValueError("Value out of range")
        self.extend(((k >> i) & 1) for i in reversed(range(n)))


def _getBit(x, i):
    """Returns true iff the i'th bit of x is set to 1."""
    return (x >> i) & 1 != 0


def makeImg(qr: object, filename: str) -> None:
    """ Convert the qr code into '*.png' format and save in under 'qr_img' """
    mat = _magnify(qr.get_qr_matrix_with_margins())
    img = Image.fromarray((mat*255).astype(np.uint8), 'L')
    _saveImg(img, filename)


def _magnify(qrmatrix, factor=10) -> np.array:
    """ Enlarge the input QR matrix by factor """
    width = len(qrmatrix)
    result_matrix = np.zeros((width * factor, width * factor), dtype=int)
    for i in range(width * factor):
        for j in range(width * factor):
            # invert the color by XOR with 1
            result_matrix[i][j] = qrmatrix[i // factor][j // factor] ^ 1
    return result_matrix


def _saveImg(img: object, raw: str) -> None:
    """ Save the qr code image as *.png format under the qr_img directory """
    # create qr_img directory if not exist
    dir_name = 'qr_img'
    if os.getcwd()[-6:] != dir_name:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        os.chdir(dir_name)  # change the current working directory to qr_img

    filename = _makeFilename(raw)
    _helperSaveImage(img, filename)


def _makeFilename(raw: str) -> str:
    """ make a file name based on the raw input text """
    # limit filename length, and get rid of illegal symbols for filename
    name_count = 8
    fname = ""
    FILENAME_REGEX = re.compile(r'[a-zA-Z0-9]')  # numbers and alphabets only
    for char in raw:
        if FILENAME_REGEX.match(char):
            name_count -= 1
            fname += char
            if name_count == 0:
                break
    if fname == "":
        fname = "untitled"
    return 'qr_{}'.format(fname)


def _helperSaveImage(img, filename) -> None:
    """ a helper function to save image with the given file name """
    # if the img file already exist, make a new filename with higher counter
    if os.path.exists(filename + '.jpg'):
        count_file_same_prefix = 0
        for _ in glob.glob(re.escape(filename) + "*.jpg"):
            count_file_same_prefix += 1
        newName = '{} ({}).jpg'.format(filename, count_file_same_prefix + 1)
        img.save(newName)
    else:
        img.save(filename + '.jpg')
