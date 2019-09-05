"""
Title: QR Code lite
Author: David Zhang
Date: 8/18/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

from itertools import cycle as itercycle
from qrlite.util import (BitBuffer,
                         countRawDataModules,
                         countDataCodewords,
                         rsComputeDivisor,
                         rsComputeRemainder,
                         NUM_ERROR_CORRECTION_BLOCKS,
                         ECC_CODEWORDS_PER_BLOCK)


class DataEncoding(object):
    """
    Encode the data on the given the binary data, and other parameters from
    DataAnalysis: ecl, version and required data length

    Basic idea is to expand the data by adding error correction coding
    (redundent information) to ensure the integrity of the original data input
    """
    @staticmethod
    def encode_data(segments, ecl, version, datalen):
        """ Returns a QR Code representing the given segments """

        capacity = countDataCodewords(version, ecl) * 8
        bitBuffer = DataEncoding._create_bit_string(segments,
                                                    version,
                                                    datalen,
                                                    capacity)

        # Pack bits into bytes in big endian
        datacodewords = [0] * (len(bitBuffer) // 8)
        for (i, bit) in enumerate(bitBuffer):
            datacodewords[i >> 3] |= bit << (7 - (i & 7))

        # Create the QR Code object
        return DataEncoding._add_ErrorCorrection_and_interleave(
            datacodewords, ecl, version)

    @staticmethod
    def _create_bit_string(segments, version, datalen, capacity):
        """ Concatenate all segments to create the data bit string """
        # prepend the indicators (mode indicator, data length) to the datablock
        bitBuffer = BitBuffer()
        for segment in segments:
            bitBuffer.append_bits(segment.get_mode().get_mode_bits(), 4)
            bitBuffer.append_bits(segment.get_num_chars(),
                                  segment.get_mode().num_char_count_bits(
                                      version))
            bitBuffer.extend(segment.get_data())
        assert datalen == len(bitBuffer) <= capacity

        # Append terminator and pad up to a byte if applicable to the data
        bitBuffer.append_bits(0, min(4, capacity - len(bitBuffer)))
        bitBuffer.append_bits(0, -len(bitBuffer) % 8)
        assert len(bitBuffer) % 8 == 0  # assert in bytes

        # Pad with alternating bytes (236 and 17) until capacity is reached
        for padbyte in itercycle((0xEC, 0x11)):
            if len(bitBuffer) >= capacity:
                break
            bitBuffer.append_bits(padbyte, 8)
        return bitBuffer

    # Every where you have a comment should probably be its own method
    @staticmethod
    def _add_ErrorCorrection_and_interleave(datacodewords, ecl, version):
        """
        Returns a new byte string representing the given data with the
        appropriate error correction codewords appended to it, based on this
        object's version and error correction level
        """
        assert len(datacodewords) == countDataCodewords(version, ecl)

        # Calculate parameter numbers
        numblocks = NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][version]
        blockErrorCorrectionLevellen = \
            ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][version]
        rawcodewords = countRawDataModules(version) // 8
        numshortblocks = numblocks - rawcodewords % numblocks
        shortblocklen = rawcodewords // numblocks

        # Split data into blocks and append ErrorCorrectionLevel to each block
        blocks = []
        rsdiv = rsComputeDivisor(blockErrorCorrectionLevellen)
        k = 0
        for i in range(numblocks):
            dat = datacodewords[
                  k: k + shortblocklen - blockErrorCorrectionLevellen + (
                      0 if i < numshortblocks else 1)]
            k += len(dat)
            ErrorCorrectionLevel = rsComputeRemainder(dat, rsdiv)
            if i < numshortblocks:
                dat.append(0)
            blocks.append(dat + ErrorCorrectionLevel)
        assert k == len(datacodewords)

        # Interleave the bytes from every block into a single sequence
        result = []
        for i in range(len(blocks[0])):
            for (j, blk) in enumerate(blocks):
                # Skip the padding byte in short blocks
                if i != shortblocklen - blockErrorCorrectionLevellen or \
                        j >= numshortblocks:
                    result.append(blk[i])
        assert len(result) == rawcodewords
        return result
