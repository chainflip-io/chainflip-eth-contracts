import sys, os

import Tick
import TickMath
import SwapMath
import LiquidityMath
import Position
import SqrtPriceMath
import SafeMath

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *

from Account import Account
from dataclasses import dataclass


class ChainflipPool(Account):
    def mintLinearOrder(self, recipient, tickLower, tickUpper, amount):
        checkInputTypes(
            accounts=(recipient), int24=(tickLower, tickUpper), uint128=(amount)
        )