"""
Title: QR Code lite
Author: David Zhang
Date: 8/18/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

from qrlite.DataAnalysis import DataAnalysis
from qrlite.DataEncoding import DataEncoding
from qrlite.DataPlacement import DataPlacement


class QRlite(object):
    """
    A light-weight version of the original QR Code Generator Library created by
    Project Nayuki <https://www.nayuki.io/page/qr-code-generator-library>

    Generalized into 3 main steps (incorporating the tutorial by Thonky.com
    <https://www.thonky.com/qr-code-tutorial>):
    1. Data Analysis
        - Determine the mode for the given data string (numeric, alphanumeric,
          or utf-8, note that other modes i.e. kanji, are not supported)
        - Determine the best version, error correction level (ecl) for the given
          data string.
        - Convert the raw data input into a list of binary encoding
        - Determine the required data length for the given version and ecl
    2. Data Encoding
        - Prepend data length indicators and mode indicators to the binary data
        - Append terminators and padding until the capacity is reached
        - Use Reed Solomon to apply error correction and interleave the data
    3. Data Placement
        - Structure the encoded data onto the squared area (size determined by
          the version)
        - Choose the best mask (0 to 7) by minimize the penalty score

    The generate_qr_code() method returns a instance created by QRlite. The user
    can access most of the data information that are essential for generating
    the resulting QR code. The get_qr_matrix() method will return binary matrix
    with built-in border, that is ready for converting into a image
    """

    @staticmethod
    def generate_qr_code(text, ecl=-1):
        """ Returns a QR Code representing the given Unicode textstring """
        bits, ecl, version, datalen = DataAnalysis.analyze(text, ecl)
        codewords = DataEncoding.encode_data(bits, ecl, version, datalen)
        modules = DataPlacement.place_data(version, ecl, codewords)
        return QRlite(text, ecl, version, modules)

    def __init__(self, text, ecl, version, modules):
        self._input_string = text
        self._ecl = ecl
        self._version = version
        self._modules = modules
        self._side_length = version * 4 + 17

    def info(self):
        print("\nInput text: {}".format(self.get_input_string()))
        print("QR code size: {} x {}".format(self.get_side_length(),
                                             self.get_side_length()))
        print("Version: {}".format(self.get_version()))
        print("Error Correction Lvl: {}\n".format(self.get_ecl()))

    def show_qr_in_terminal(self):
        """Prints the given QrCode object to the console."""
        side = self.get_side_length()
        border = side // 8
        for y in range(-border, side + border):
            for x in range(-border, side + border):
                print(u"\u2588 "[1 if self.get_pixel(x, y) else 0] * 2,
                      end="")
            print()
        print()

    def get_qr_matrix_with_margins(self):
        """ get the matrix with border set to 1/8 of total width of modules """
        side = self.get_side_length()
        border = side // 8
        matrix = [[1 if self.get_pixel(x, y) else 0
                   for x in range(-border, side + border)]
                  for y in range(-border, side + border)]
        return matrix

    def get_input_string(self):
        return self._input_string

    def get_ecl(self):
        return self._ecl.get_lv()

    def get_version(self):
        return self._version

    def get_modules(self):
        return self._modules

    def get_side_length(self):
        return self._side_length

    def get_pixel(self, x, y):
        """
        Returns the color of the module (pixel) at the given coordinates,
        which is False for white or True for black. The top left corner has the
        coordinates (x=0, y=0). If the given coordinates are out of bounds,
        then False (white) is returned.
        """
        return (0 <= x < self._side_length) and \
               (0 <= y < self._side_length) and \
               (self._modules[y][x])
