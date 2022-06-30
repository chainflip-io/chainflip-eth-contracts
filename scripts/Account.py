
class Account:
    balanceToken0 = 0
    balanceToken1 = 0

    def __init__(self, name, balanceToken0, balanceToken1):
        self.name = name
        self.balanceToken0 = balanceToken0
        self.balanceToken1 = balanceToken1

    # Add transfer and receive tokens functions
    def transferTokens(self, recipient, amount0, amount1):
        # Safeguard checks
        assert amount0 >= 0 and amount1 >= 0
        assert self.balanceToken0 >= amount0, "Insufficient balance"
        assert self.balanceToken1 >= amount1, "Insufficient balance"

        self.balanceToken0 -= amount0
        self.balanceToken1 -= amount1
        recipient.receiveTokens(amount0, amount1)

    def receiveTokens(self, amount0, amount1):
        # Safeguard check
        assert amount0 > 0 and amount1 > 0
        
        self.balanceToken0 += amount0
        self.balanceToken1 += amount1