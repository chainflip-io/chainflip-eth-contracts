
### @title Math library for liquidity

### @notice Add a signed liquidity delta to liquidity and revert if it overflows or underflows
### @param x The liquidity before change
### @param y The delta by which liquidity should be changed
### @return z The liquidity delta
def addDelta(x, y):
    if (y < 0):
        z = x - abs(y)
        assert z < x , 'LS'
    else:
        z = x + abs(y)
        assert z >= x, 'LA'
    return z
