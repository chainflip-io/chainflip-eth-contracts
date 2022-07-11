class Account:
    def __init__(self, name, tokens, balances):
        self.name = name
        assert len(tokens) == len(balances)
        # Check uniquness of tokens list
        assert len(set(tokens)) == len(tokens)
        self.tokens = tokens
        self.balances = {}
        for i in range(len(tokens)):
            self.balances[tokens[i]] = balances[i]

    # Add transfer and receive tokens functions
    def transferToken(self, recipient, token, amount):
        # Safeguard checks
        assert amount >= 0
        assert self.balances[token] >= amount, "Insufficient balance"

        self.balances[token] -= amount
        recipient.receiveToken(token, amount)

    def receiveToken(self, token, amount):
        # Safeguard check
        assert amount >= 0

        self.balances[token] += amount
