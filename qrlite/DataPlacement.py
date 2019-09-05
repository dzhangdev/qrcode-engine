"""
Title: QR Code lite
Author: David Zhang
Date: 8/18/2019
Code version: 1.0

Adapted from: Project Nayuki (MIT License)
https://www.nayuki.io/page/qr-code-generator-library
"""

from collections import deque
from qrlite.util import _getBit, countRawDataModules
from qrlite.params import _MASK_PATTERNS, _PENALTIES


class DataPlacement(object):
    """
    Data block (module) placement in the N x N matrix and apply optimal
    masking (lowest penalty score) to the matrix
    """
    @staticmethod
    def place_data(version, ecl, allcodewords):
        return DataPlacement(version, ecl, allcodewords).get_modules()

    def __init__(self, version, ecl, allcodewords):
        self._version = version
        self._ecl = ecl
        self._allcodewords = allcodewords

        # The width and height of QR Code, measured in modules [21 and 177]
        self._side_len = version * 4 + 17
        self._modules = [[False] * self._side_len for _ in
                         range(self._side_len)]  # Initially all white

        # Indicates function modules that are not subjected to masking.
        self._isfunction = [[False] * self._side_len for _ in
                            range(self._side_len)]

        self._draw_function_patterns()
        self._draw_codewords(self._allcodewords)
        self._mask = self._apply_mask()

    def get_modules(self):
        return self._modules

    def _apply_mask(self, mask=0):
        """ Choose the best mask """
        minpenalty = 1 << 32
        for i in range(8):
            self._apply(i)
            self._draw_format_bits(i)
            penalty = self._get_penalty_score()
            if penalty < minpenalty:
                mask = i
                minpenalty = penalty
            self._apply(i)  # Undo
        assert 0 <= mask <= 7  # The mask should be between 0 and 7.
        self._apply(mask)  # Apply the final choice of mask
        self._draw_format_bits(mask)  # Overwrite old format bits
        return mask

    def _apply(self, mask):
        """
        XORs the codeword modules in this QR Code with the given mask
        pattern. The function modules must be marked and the codeword bits must
        be drawn before masking.

        Due to the arithmetic of XOR, calling applyMask() with the same mask
        value a second time will undo the mask. A final well-formed QR Code
        needs exactly one (not zero, two, etc.) mask applied.
        """
        if not (0 <= mask <= 7):
            raise ValueError("Mask value out of range")
        masker = _MASK_PATTERNS[mask]
        for y in range(self._side_len):
            for x in range(self._side_len):
                self._modules[y][x] ^= (masker(x, y) == 0) and \
                                       (not self._isfunction[y][x])

    def _draw_function_patterns(self):
        """ Reads this object's version, draws and marks all function modules """
        # Draw horizontal and vertical timing patterns
        for i in range(self._side_len):
            self._set_function_module(6, i, i % 2 == 0)
            self._set_function_module(i, 6, i % 2 == 0)

        # Draw 3 finder patterns
        # (all corners except bottom right; overwrites some timing modules)
        self._draw_finder_pattern(3, 3)
        self._draw_finder_pattern(self._side_len - 4, 3)
        self._draw_finder_pattern(3, self._side_len - 4)

        # Draw numerous alignment patterns
        alignpatpos = self._get_alignment_pattern_positions()
        numalign = len(alignpatpos)
        skips = ((0, 0), (0, numalign - 1), (numalign - 1, 0))
        for i in range(numalign):
            for j in range(numalign):
                if (i, j) not in skips:  # Don't draw on the 3 finder corners
                    self._draw_alignment_pattern(alignpatpos[i], alignpatpos[j])

        # Draw configuration data
        # Dummy mask value; overwritten later in the constructor
        self._draw_format_bits(0)
        self._draw_version()

    def _set_function_module(self, x, y, isblack):
        """
        Sets the color of a module and marks it as a function module.
        Only used by the constructor. Coordinates must be in bounds.
        """
        assert type(isblack) is bool
        self._modules[y][x] = isblack
        self._isfunction[y][x] = True

    def _get_alignment_pattern_positions(self):
        """
        Returns an ascending list of positions of alignment patterns for
        this version number. Each position is in the range [0,177), and are used
        on both the x and y axes. This could be implemented as lookup table of
        40 variable-length lists of integers.
        """
        ver = self._version
        if ver == 1:
            return []
        else:
            # Theres a lot of math here. I would expalin whats goin on with comments
            numalign = ver // 7 + 2
            step = 26 if (ver == 32) else \
                (ver * 4 + numalign * 2 + 1) // (numalign * 2 - 2) * 2
            result = [(self._side_len - 7 - i * step) for i in
                      range(numalign - 1)] + [6]
            return list(reversed(result))

    def _draw_finder_pattern(self, x, y):
        """
        Draws a 9*9 finder pattern including the border separator,
        with the center module at (x, y). Modules can be out of bounds.
        """
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                xx, yy = x + dx, y + dy
                if (0 <= xx < self._side_len) and (0 <= yy < self._side_len):
                    # Chebyshev/infinity norm
                    self._set_function_module(
                        xx, yy, max(abs(dx), abs(dy)) not in (2, 4))

    def _draw_alignment_pattern(self, x, y):
        """
        Draws a 5*5 alignment pattern, with the center module
        at (x, y). All modules must be in bounds.
        """
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                self._set_function_module(
                    x + dx, y + dy, max(abs(dx), abs(dy)) != 1)

    def _draw_format_bits(self, mask):
        """
        Draws 2 copies of the format bits (with its own ECL) based on the
        given mask and this object's error correction level field.
        """
        # Calculate error correction code and pack bits
        # errCorrLvl is uint2, mask is uint3
        data = self._ecl.formatbits << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412  # uint15
        assert bits >> 15 == 0

        # Draw first copy
        for i in range(0, 6):
            self._set_function_module(8, i, _getBit(bits, i))
        self._set_function_module(8, 7, _getBit(bits, 6))
        self._set_function_module(8, 8, _getBit(bits, 7))
        self._set_function_module(7, 8, _getBit(bits, 8))
        for i in range(9, 15):
            self._set_function_module(14 - i, 8, _getBit(bits, i))

        # Draw second copy
        for i in range(0, 8):
            self._set_function_module(
                self._side_len - 1 - i, 8, _getBit(bits, i))
        for i in range(8, 15):
            self._set_function_module(
                8, self._side_len - 15 + i, _getBit(bits, i))
        self._set_function_module(8, self._side_len - 8, True)  # Always black

    def _draw_version(self):
        """
        Draws two copies of the version bits (with its own error correction
        code), based on this object's version field, iff 7 <= version <= 40.
        """
        if self._version >= 7:
            # Calculate error correction code and pack bits
            rem = self._version  # version is uint6, in the range [7, 40]
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self._version << 12 | rem  # uint18
            assert bits >> 18 == 0

            # Draw two copies
            for i in range(18):
                bit = _getBit(bits, i)
                a = self._side_len - 11 + i % 3
                b = i // 3
                self._set_function_module(a, b, bit)
                self._set_function_module(b, a, bit)

    def _draw_codewords(self, data):
        """
        Draws the given sequence of 8-bit codewords (data and error
        correction) onto the entire data area of this QR Code. Function modules
        need to be marked off before this is called.
        """
        assert len(data) == countRawDataModules(self._version) // 8

        i = 0  # Bit index into the data
        # Do the funny zigzag scan
        for right in range(self._side_len - 1, 0,
                           -2):  # Index of right column in each column pair
            if right <= 6:
                right -= 1
            for vert in range(self._side_len):  # Vertical counter
                for j in range(2):
                    x = right - j  # Actual x coordinate
                    upward = (right + 1) & 2 == 0
                    y = (self._side_len - 1 - vert) if upward else vert
                    if not self._isfunction[y][x] and i < len(data) * 8:
                        self._modules[y][x] = _getBit(data[i >> 3], 7 - (i & 7))
                        i += 1
        # If this QR Code has any remainder bits (0 to 7), they were assigned as
        # 0/false/white by the constructor and are left unchanged by this method
        assert i == len(data) * 8

    def _finder_penalty_count_patterns(self, runhistory):
        """ Can only be called immediately after a white run is added, and
        returns either 0, 1, or 2. """
        n = runhistory[1]
        assert n <= self._side_len * 3
        core = n > 0 and \
               (runhistory[2] == runhistory[4] == runhistory[5] == n) and \
               (runhistory[3] == n * 3)
        return (1 if (
                core and runhistory[0] >= n * 4 and runhistory[6] >= n)
                 else 0) \
               + (1 if (
                core and runhistory[6] >= n * 4 and runhistory[0] >= n)
                  else 0)

    def _get_penalty_score(self):
        """
        Calculates and returns the penalty score based on state of this QR
        Code's current modules.

        This is used by the automatic mask choice algorithm to find the mask
        pattern that yields the lowest score.

        The four penalty rules can be summarized as follows:
        -3 for each group of 5 or more same-colored modules in a row or column
        -3 for each 2x2 area of same-colored modules in the matrix
        -40 if there are patterns that look similar to the finder patterns
        -10 if more than half of the modules are dark or light, with a larger
            penalty for a larger difference.
        """
        result = 0
        size = self._side_len
        modules = self._modules
        # Adjacent modules in row having same color, and finder-like patterns
        for y in range(size):
            runcolor = False
            runx = 0
            runhistory = deque([0] * 7, 7)
            padrun = size  # Add white border to initial run
            for x in range(size):
                if modules[y][x] == runcolor:
                    runx += 1
                    if runx == 5:
                        result += _PENALTIES[0]
                    elif runx > 5:
                        result += 1
                else:
                    runhistory.appendleft(runx + padrun)
                    padrun = 0
                    if not runcolor:
                        result += self._finder_penalty_count_patterns(
                            runhistory) * _PENALTIES[2]
                    runcolor = modules[y][x]
                    runx = 1
            result += self._finder_penalty_terminate_and_count(
                runcolor, runx + padrun, runhistory) * _PENALTIES[2]
        # Adjacent modules in column having same color, and finder-like patterns
        for x in range(size):
            runcolor = False
            runy = 0
            runhistory = deque([0] * 7, 7)
            padrun = size  # Add white border to initial run
            for y in range(size):
                if modules[y][x] == runcolor:
                    runy += 1
                    if runy == 5:
                        result += _PENALTIES[0]
                    elif runy > 5:
                        result += 1
                else:
                    runhistory.appendleft(runy + padrun)
                    padrun = 0
                    if not runcolor:
                        result += self._finder_penalty_count_patterns(
                            runhistory) * _PENALTIES[2]
                    runcolor = modules[y][x]
                    runy = 1
            result += self._finder_penalty_terminate_and_count(
                runcolor, runy + padrun, runhistory) * _PENALTIES[2]
        # 2*2 blocks of modules having same color
        for y in range(size - 1):
            for x in range(size - 1):
                if modules[y][x] == modules[y][x + 1] == modules[y + 1][x] == \
                        modules[y + 1][x + 1]:
                    result += _PENALTIES[0]

        # Balance of black and white modules
        black = sum((1 if cell else 0) for row in modules for cell in row)
        total = size ** 2  # Note that size is odd, so black/total != 1/2
        # Compute the smallest integer k >= 0 such that
        # (45-5k)% <= black/total <= (55+5k)%
        k = (abs(black * 20 - total * 10) + total - 1) // total - 1
        result += k * _PENALTIES[1]
        return result

    def _finder_penalty_terminate_and_count(
            self, currentruncolor, currentrunlength, runhistory):
        """ Must be called at the end of a line (row or column) of modules. """
        if currentruncolor:  # Terminate black run
            runhistory.appendleft(currentrunlength)
            currentrunlength = 0
        currentrunlength += self._side_len  # Add white border to final run
        runhistory.appendleft(currentrunlength)
        return self._finder_penalty_count_patterns(runhistory)
