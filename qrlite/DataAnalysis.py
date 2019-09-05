"""
Title: QR Code lite
Author: David Zhang
Date: 8/18/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

from sys import version_info as python_version
from qrlite.params import (ALPHANUMERIC_ENCODING_TABLE,
                           ALPHANUMERIC_REGEX,
                           MAX_VERSION,
                           MIN_VERSION,
                           NUMERIC_REGEX)
from qrlite.util import BitBuffer, countDataCodewords


class DataAnalysis(object):
    """ Error checking the data input, and convert data into a bit array """

    @staticmethod
    def analyze(text, ecl=-1, boost=True):
        """
        Returns a tuple of parameters for generating QR module:
            - A bit array converted from the input_string
            - Error correction level (optimizied if boost=True)
            - Version number (1 - 40)
            - Data length (number of characters)
        """
        DataAnalysis._validate_input(text, ecl)
        mode = DataAnalysis._find_proper_mode(text)
        bitdata = DataAnalysis._convert_to_binary(text, mode)
        version, datalen = DataAnalysis._find_version_len(bitdata, ecl)
        DataAnalysis._boost_error_correction_lv(boost, datalen, version, ecl)
        return bitdata, ecl, version, datalen

    # for debugging
    def __init__(self, mode, length, bitbuffer):
        """ Make a bit array segment representing the QR code module """
        self._mode = mode
        self._length = length
        self._bitdata = list(bitbuffer)

    def get_data(self):
        """Returns a new copy of the data bits of this segment."""
        return self._bitdata

    def get_num_chars(self):
        """Returns the character count field of this segment."""
        return self._length

    def get_mode(self):
        """Returns the mode field of this segment."""
        return self._mode

    @staticmethod
    def _validate_input(text, ecl):
        """ validate input and ecl format """
        if not (isinstance(text, str)):
            raise TypeError("Text string expected")

        if text == "":
            raise ValueError("Empty string")

        ecl = ErrorCorrectionLevel.LOW if ecl == -1 else ecl
        if not isinstance(ecl, ErrorCorrectionLevel) \
                and ecl != -1:
            raise TypeError("ErrorCorrectionLevel expected")

    @staticmethod
    def _find_proper_mode(text):
        """ determine which mode to use based on the input """
        bitdata, mode, length = [], 0, 0
        for character in text:
            length += 1
            if mode < 2 and str.isdigit(character):
                mode = 1  # numeric mode
            elif mode < 4 and (str.isupper(character) or
                               character in " $%*+./:"):
                mode = 2  # QR alphanumeric mode, different from str.isalnum()
            else:
                mode = 4  # byte mode (utf-8)
                break
        return mode

    @staticmethod
    def _convert_to_binary(text, mode):
        """ convert the text input to binary form """
        if mode == 1:
            return [DataAnalysis.make_numeric(text)]
        elif mode == 2:
            return [DataAnalysis.make_alphanumeric(text)]
        else:
            return [DataAnalysis.make_bytes(text.encode("UTF-8"))]

    @staticmethod
    def make_numeric(digits):
        """ Returns a bit array segment in numeric mode. """
        if NUMERIC_REGEX.match(digits) is None:  # double check input
            raise ValueError("String contains non-numeric characters")
        bb = BitBuffer()
        i = 0
        while i < len(digits):  # up to 3 digits at a time, each digit is 3 bits
            n = min(len(digits) - i, 3)
            bb.append_bits(int(digits[i: i + n]), n * 3 + 1)
            i += n
        return DataAnalysis(DataAnalysis.Mode.NUMERIC, len(digits), bb)

    @staticmethod
    def make_alphanumeric(text):
        """ Returns a bit array segment in alphanumeric mode. """
        if ALPHANUMERIC_REGEX.match(text) is None:
            raise ValueError(  # double check input
                "String contains unencodable characters in alphanumeric mode")
        bb = BitBuffer()
        # Process groups of 2 characers at a time (use the encoding table)
        # Multiply the first number by 45, then add to the second
        for i in range(0, len(text) - 1, 2):
            temp = ALPHANUMERIC_ENCODING_TABLE[text[i]] * 45
            temp += ALPHANUMERIC_ENCODING_TABLE[text[i + 1]]
            bb.append_bits(temp, 11)
        if len(text) % 2 > 0:  # 1 character remaining
            bb.append_bits(ALPHANUMERIC_ENCODING_TABLE[text[-1]], 6)
        return DataAnalysis(DataAnalysis.Mode.ALPHANUMERIC, len(text), bb)

    @staticmethod
    def make_bytes(data):
        """ Returns a bit array segment in byte mode """
        if python_version.major >= 3 and isinstance(data, str):
            raise TypeError("Byte string/list expected")  # double check input
        bb = BitBuffer()
        for b in data:  # 8 bits per character
            bb.append_bits(b, 8)
        return DataAnalysis(DataAnalysis.Mode.BYTE, len(data), bb)

    @staticmethod
    def _get_total_bits(segments, version):
        """
        Calculates the number of bits needed to encode the given segments at
        given version. Returns a non-negative number if success else 0
        """
        result = 0
        for segment in segments:
            ccbits = segment.get_mode().num_char_count_bits(version)
            if segment.get_num_chars() >= (1 << ccbits):
                return 0
            result += 4 + ccbits + len(segment.get_data())
        return result

    @staticmethod
    def _find_version_len(bitdata, ecl):
        version, datalen = 1, 0
        for version in range(MIN_VERSION, MAX_VERSION + 1):
            capacity = countDataCodewords(version, ecl) * 8
            datalen = DataAnalysis._get_total_bits(bitdata, version)
            if datalen != 0 and datalen <= capacity:
                return version, datalen  # found suitable version
            if version >= MAX_VERSION:
                msg = "ERROR - data is too long\n"
                if datalen != 0:
                    msg = ("Data length = {} bits,"
                           "Max capacity = {} bits".format(datalen, capacity))
                raise DataAnalysis.DataTooLongError(msg)
        assert datalen != 0, "make_segments error"

    @staticmethod
    def _boost_error_correction_lv(boost, datalen, version, ecl):
        """ check if there's room to boost the level of error correction """
        for newecl in (ErrorCorrectionLevel.MEDIUM,
                       ErrorCorrectionLevel.QUARTILE,
                       ErrorCorrectionLevel.HIGH):
            if boost and datalen <= countDataCodewords(version, newecl) * 8:
                ecl = newecl

    class Mode(object):
        """Describes how a segment's data bits are interpreted. Immutable."""

        def __init__(self, modebits, charcounts):
            # I could be wrong but i thought python style guide was for camel case
            self._modebits = modebits  # The mode indicator bits - uint4
            self._charcounts = charcounts  # Number of character count bits

        # Package-private method
        def get_mode_bits(self):
            """
            Returns an unsigned 4-bit integer value (range 0 to 15)
            representing the mode indicator bits for this mode object.
            """
            return self._modebits

        # Package-private method
        def num_char_count_bits(self, ver):
            """
            Returns the bit width of the character count field for a
            segment in this mode in a QR Code at the given version number.
            The result is in the range [0, 16].
            """
            return self._charcounts[(ver + 7) // 17]

    # Public constants. Create them outside the class.
    Mode.NUMERIC = Mode(0x1, (10, 12, 14))
    Mode.ALPHANUMERIC = Mode(0x2, (9, 11, 13))
    Mode.BYTE = Mode(0x4, (8, 16, 16))

    class DataTooLongError(ValueError):
        """
        Raised when the supplied data does not fit any QR Code version.
        Ways to handle this exception include:
        - Decrease the error correction level if it was greater than Ecc.LOW.
        - If the encode_segments() function was called with a maxversion argument,
            then increase it if it was less than QrCode.MAX_VERSION. (This advice
            does not apply to the other factory functions because they search all
            versions up to QrCode.MAX_VERSION.)
        - Split the text data into better or optimal segments in order to reduce
            the number of bits required.
        - Change the text or binary data to be shorter.
        - Change the text to fit the character set of a particular segment mode
            (e.g. alphanumeric).
        - Propagate the error upward to the caller/user.
        """
        pass


class ErrorCorrectionLevel(object):
    """The error correction level in a QR Code symbol. Immutable."""

    def __init__(self, i, fb):
        self.ordinal = i  # uint2
        self.formatbits = fb  # uint2

    def get_lv(self):
        if self.ordinal == 0:
            return "LOW"
        elif self.ordinal == 1:
            return "MEDIUM"
        elif self.ordinal == 2:
            return "QUARTILE"
        else:
            return "HIGH"


# Percentage of erroneous codewords that the QR can tolorate
ErrorCorrectionLevel.LOW = ErrorCorrectionLevel(0, 1)  # 7%
ErrorCorrectionLevel.MEDIUM = ErrorCorrectionLevel(1, 0)  # 15%
ErrorCorrectionLevel.QUARTILE = ErrorCorrectionLevel(2, 3)  # 25%
ErrorCorrectionLevel.HIGH = ErrorCorrectionLevel(3, 2)  # 30%
