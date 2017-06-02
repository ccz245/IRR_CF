from pyxll import xl_func
import PlayBeam

@xl_func("cached_object cfs, cached_object curve: float")
def eve(cfs, curve):
    result = 0
    for cf in cfs:
        result = result + curve.df(cf.paymentDate) * (cf.interest +  cf.principal)
    return result


@xl_func("cached_object curve, string id, float bps: cached_object")
def shockCurve(curve, id, bps):
    result = curve.shock(id, bps)
    return result


@xl_func("string name, date[] dates, float[] rates: cached_object")
def createCurve(name, dates, rates):
    """
    Create a yield curve with a given reference name.

    :param name:  Reference name of the curve. e.g. GBP LIBOR
    :param dates: An array of tenor dates.
    :param rates: An array of interest rates.
    """
    tenors = []
    for dte, rate in zip(dates, rates):
        tenor = Tenor(dte[0], rate[0])
        tenors.append(tenor)
    result = Curve(name, dates[0][0], tenors)
    return result


@xl_func("cached_object curve, date dte")
def getRate(curve, dte):
    """
    Retrieve an interpolated rate for a specific date from a reference curve.

    :param name: A curve Reference
    :param dte:  A tenor date for which the interpolated rate should be returned.
    """
    return curve.tenorDict[dte]

@xl_func("cached_object curve, date fromDate, date toDate: float")
def getForwardRate(curve, fromDate, toDate):
    result = curve.fr(fromDate, toDate)
    return result

@xl_func("string id, date settlementDate, date maturityDate, int paymentFrequency, float notional, float spread, float firstCoupon: cached_object")
def createLevelPay(id, settlementDate, maturityDate, paymentFrequency, notional = 1, spread = 0, firstCoupon = None):
    result = LevelPay(id, settlementDate, maturityDate, paymentFrequency, notional, spread, firstCoupon)
    return result


@xl_func("cached_object leg, date reportingDate, float remainingAmount, cached_object curve: cached_object")
def getCashflows(leg, reportingDate, remainingAmount, curve):
    result = leg.getCashflows(reportingDate, remainingAmount, curve)
    return result


@xl_func("cached_object obj, string method, cached_list_or_vals pars: cached_object")
def invoke(obj, method, pars):
    attr = getattr(obj, method)
    if attr is None:
        return "Attribute not found: %s" % (method)

    result = attr(pars)
    return result    


@xl_func("cached_object_or_val p0, cached_object_or_val p1, cached_object_or_val p2, cached_object_or_val p3, cached_object_or_val p4, cached_object_or_val p5, cached_object_or_val p6, cached_object_or_val p7, cached_object_or_val p8, cached_object_or_val p9 : cached_object")
def createArray(p0, p1, p2, p3, p4, p5, p6, p7, p8, p9):
    result = []
    if p0:
        result.append(p0)
    if p1:
        result.append(p1)
    if p2:
        result.append(p2)
    if p3:
        result.append(p3)
    if p4:
        result.append(p4)
    if p5:
        result.append(p5)
    if p6:
        result.append(p6)
    if p7:
        result.append(p7)
    if p8:
        result.append(p8)
    if p9:
        result.append(p9)
    return result


@xl_func("cached_object obj", auto_resize = True)
def getMethods(obj):
    result = []
    for method in dir(obj): 
        if callable(getattr(obj, method)):
            result.append([method])
    return result


@xl_func("cached_object obj", auto_resize = True)
def getProperties(obj):
    result = []
    for attr in dir(obj): 
        if not callable(getattr(obj, attr)):
            result.append([attr])
    return result


@xl_func("cached_object obj, string propName: string")
def getProp(obj, propName):
    result = getattr(obj, propName)
    return result


@xl_func("cached_object obj")
def getHelp(obj):
    result = getattr(obj, "__doc__")
    return result


@xl_func("cached_object obj, int index: cached_object")
def getArrayItem(obj, index):
    result = obj[index]
    return result


@xl_func("cached_object obj, string method", auto_resize = True)
def getArgs(obj, method):
    attr = getattr(obj, method)
    result = []
    for name in attr.__code__.co_varnames:    
        result.append([name])
    return result