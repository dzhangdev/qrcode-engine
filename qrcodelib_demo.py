"""
Title: QR Code lite
Author: David Zhang
Date: 8/19/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

from qrlite.DataAnalysis import ErrorCorrectionLevel
from qrlite.QRlite import QRlite
from qrlite.util import makeImg


def main():
    demo()


def demo():
    """ Creates QR Codes in the form of matrix, then convert to images """
    input_string = "asdlfhasdklfjasjdf"
    minimum_error_correction_level = ErrorCorrectionLevel.LOW

    # get the qr instance
    qr = QRlite.generate_qr_code(input_string, minimum_error_correction_level)
    # Show Error correction level, version, and size
    qr.info()
    # convert to image "png" format
    makeImg(qr, input_string)
    # print to terminal
    qr.show_qr_in_terminal()


if __name__ == "__main__":
    main()

