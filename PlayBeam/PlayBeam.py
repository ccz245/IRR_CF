import apache_beam as beam
# from beam_utils.sources import CsvFileSource
from datetime import timedelta, date, datetime
from dateutil.relativedelta import *
from pyxll import xl_func

# TD 170608 Melvin
# TD keep deposit in mind, behaviouralisation
# TD key is maintenance, upgrade, clarity
# TD conversion from business logic to code
# TD deposits, with pass through assumptions
# Stephen: you are right, it's not ..., it's ...
# purpose to comment to the working group, what we need for clear choice decision
# ie scope is sufficient as acceptance criteria
# show NII & EVE number


'''==================================== Transaction, Market, Behavioural Input Module =============================='''


class Object(object):
    pass


def CreateData(reportingDate, count):
    # generate testing data in memory, this is very useful for unit testing
    # the new feature of reading from file should be built in parallel to this, so use can choose data sourcing method
    result = []
    for i in range(0, count):
        item = Object()
        item.reportingDate = reportingDate
        item.id = i
        item.settlementDate = date(2016, 12, 15)
        # feasibility test case maturity date is 2046, 12, 15, set to 2017 for unit testing
        # adding attributes and their values to the data instance
        setattr(item, "maturityDate", date(2017, 12, 15))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "notional", 1000000)
        setattr(item, "spread", 0.025/12)
        setattr(item, "firstCoupon", 0.035/12)
        setattr(item, "remainingAmount", 1000000)
        setattr(item, "prepaymentModel", 'varMortgageCPR')
        result.append(item)
    return result


def getCurve(reportingDate):
    tenors = []
    tenors.append(Tenor(date(2016, 12, 31), 0.00364435205))
    tenors.append(Tenor(date(2017, 1, 1), 0.00364435205))
    tenors.append(Tenor(date(2017, 1, 7), 0.003644387568))
    tenors.append(Tenor(date(2017, 1, 14), 0.003644395463))
    tenors.append(Tenor(date(2017, 1, 31), 0.003644403779))
    tenors.append(Tenor(date(2017, 2, 28), 0.003644419784))
    tenors.append(Tenor(date(2017, 3, 31), 0.00364221997))
    tenors.append(Tenor(date(2017, 4, 30), 0.003692321723))
    tenors.append(Tenor(date(2017, 5, 31), 0.003744481203))
    tenors.append(Tenor(date(2017, 6, 30), 0.003791257403))
    tenors.append(Tenor(date(2017, 7, 31), 0.003828763813))
    tenors.append(Tenor(date(2017, 8, 31), 0.003866626073))
    tenors.append(Tenor(date(2017, 9, 30), 0.003904232464))
    tenors.append(Tenor(date(2017, 10, 31), 0.003942089057))
    tenors.append(Tenor(date(2017, 11, 30), 0.003982239562))
    tenors.append(Tenor(date(2017, 12, 31), 0.004021743672))
    tenors.append(Tenor(date(2018, 3, 31), 0.004150962226))
    tenors.append(Tenor(date(2018, 6, 30), 0.004305536813))
    tenors.append(Tenor(date(2018, 12, 31), 0.004683066614))
    tenors.append(Tenor(date(2019, 12, 31), 0.005615948801))
    tenors.append(Tenor(date(2020, 12, 31), 0.006617650115))
    tenors.append(Tenor(date(2021, 12, 31), 0.007595409253))
    tenors.append(Tenor(date(2022, 12, 31), 0.008550615831))
    tenors.append(Tenor(date(2023, 12, 31), 0.009458566427))
    tenors.append(Tenor(date(2026, 12, 31), 0.011694956257))
    tenors.append(Tenor(date(2031, 12, 31), 0.013881670005))
    tenors.append(Tenor(date(2036, 12, 31), 0.014513760689))
    tenors.append(Tenor(date(2046, 12, 31), 0.014258652999))
    result = Curve("abc", reportingDate, tenors)
    return result


def loadBehModel(tranModelName):
    # TD add ability to load multiple models into the same instance
    models = []
    models.append(BehModel('varMortgageCPR', 'CPR', 0.12))
    models.append(BehModel('IBCA_Beh_Life', 'Beh_Life', 12))
    # TD can be re-written using next() / list comprehension
    for i in range(0,len(models)):
        if models[i].modelName == tranModelName:
            # TD result should copy directly from the object in list, instead of having to re-instantiate
            result = BehModel(models[i].modelName, models[i].modelType, models[i].modelValue)
    return result



'''=========================================== Market Projection Module ============================================'''


def linearDistance(x2, x1):
    result = x2 - x1
    return result
    

def linear_interpolation(x1, y1, x2, y2, x, distanceMeasure = linearDistance):
    result = y1 + (y2 - y1)/distanceMeasure(x2, x1)*distanceMeasure(x, x1)
    return result


def act356(toDate, fromDate):
    result = (toDate.toordinal() - fromDate.toordinal()) / 365.0
    return result


class Tenor:

    def __init__(self, date, rate):
        self.date = date
        self.rate = rate


class Curve:

    def __init__(self, id, reportingDate, tenorList, dayCountFunc = act356, interpFunc = linear_interpolation):
        self.id = id
        self.reportingDate = reportingDate
        self.tenorList = tenorList
        self.dayCountFunc = dayCountFunc
        self.tenorDict = { x.date: x.rate for x in tenorList }
        self.tenorDict = {}
        self.interpFunc = interpFunc
        # trigger the init method of the class when initiating a new instance
        self.init()


    def shock(self, id, bps):
        # TD this shock approach only works for parallel shock for EVE
        # to be revised with flexibility to imply then shock and none parallel shock
        shockedTenors = map(lambda x: Tenor(x.date, x.rate + bps), self.tenorList)
        result = Curve(id, self.reportingDate, shockedTenors, self.dayCountFunc, self.interpFunc)
        return result


    def init(self):
        curDate = self.reportingDate
        endDate = curDate.replace(year = curDate.year + 30)
        nextIndex = 0
        prevTenor = self.tenorList[nextIndex-1]
        nextTenor = self.tenorList[nextIndex] 
        maxIndex = len(self.tenorList) - 1
        while curDate <= endDate:
            if curDate >= self.tenorList[nextIndex].date and nextIndex < maxIndex:
                nextIndex += 1
                prevTenor = nextTenor
                nextTenor = self.tenorList[nextIndex]

            # Perform interpolation
            self.tenorDict[curDate] = self.interpFunc(
                prevTenor.date, 
                prevTenor.rate, 
                nextTenor.date, 
                nextTenor.rate, 
                curDate,
                self.dayCountFunc)
            curDate = curDate + timedelta(days = 1)

    def df(self, date):
        """Discount factor"""
        # pow(x,y) returns x to the power of y
        result = 1.0/pow((1.0 + self.tenorDict[date]), self.dayCountFunc(date, self.reportingDate))
        return result

    def fr(self, fromDate, toDate, annualise = True):
        """Returns the annualised forward rate between two dates"""
        if annualise:
            annualisationFactor = 1.0/self.dayCountFunc(toDate, fromDate)
        else:
            annualisationFactor = 1.0
        result = pow(self.df(fromDate) / self.df(toDate), annualisationFactor) - 1
        return result

    def cr(self, spread, fromDate, toDate, annualise):
        result = self.fr(fromDate, toDate, annualise) + spread
        return result

    def __add__(self, other):
        """Defines addition of two curves - used to shock"""
        # curve1.__add__(curve2) defines the behaviour of curve1 + curve2
        pass


class Scenario:
    
    def __init__(self, reportingDate, curve):
        self.reportingDate = reportingDate
        self.curve = curve


'''=========================================== Contractual Cashflow Module ========================================='''


class FloatLeg:

    def __init__(self, id, settlementDate, maturityDate, paymentFrequency, prepaymentModel, notional = 1, spread = 0):
        self.id = id
        # TD revise this to originationDate to align with terminology
        self.settlementDate = settlementDate
        self.maturityDate = maturityDate
        # paymentFrequency is read as an integer for number of months
        self.paymentFrequency = paymentFrequency
        self.notional = notional
        self.spread = spread
        self.payDates = []
        self.initPayDates()

    def initPayDates(self):
        # TD should this be reporting date instead, since we won't go back into the past?
        # consider the need to work out previous pay date for the first payment calculation
        # pay dates should be shared between fixed / variable products
        stopDate = self.settlementDate
        curDate = self.maturityDate
        # TD 0604 added the maturityDate to the payDates list
        self.payDates.append(curDate)
        while curDate > stopDate:
            curDate = curDate + relativedelta(months = -self.paymentFrequency)
            # Add modified following
            # TD when will this condition be false? given the parent while condition
            if curDate >= stopDate:
                self.payDates.append(curDate)
        self.payDates.reverse()

    def getCashflows(self, reportingDate, curve):
        # TBC how is this used? given we have the same method under LevelPay
        cashflows = []
        for i in range(0, len(self.payDates) - 1):
            curDate = self.payDates[i]
            if curDate <= reportingDate:
                # continue to the next for iteration, break will break out the loop completely
                continue
            # at this point curDate > reportingDate
            prevDate = self.payDates[i-1]
            if prevDate < reportingDate:
                prevDate = reportingDate
            # need to separate out logic on payment dates from reset dates
            # TD this sees to be forward rate * notional, does that include customer margin?
            payment = curve.fr(prevDate, curDate) * self.notional
            cashflows.append(Cashflow(self.id, curDate, payment, None, None))
        return cashflows


class LevelPay(FloatLeg):
    # LevelPay is a subclass of the FloatLeg class, can use print(help(LevelPay)) to see resolution order
    # variables re-specified in subclass will overwrite their values in the parent class

    def __init__(self, id, settlementDate, maturityDate, paymentFrequency, prepaymentModel, notional = 1, spread = 0, firstCoupon = None):
        # added so the LevelPay class can take in additional parameters than its parent class FloatLeg
        # alternative is super().__init__(id, settlementDate, maturityDate, paymentFrequency, notional, spread)
        FloatLeg.__init__(self, id, settlementDate, maturityDate, paymentFrequency, prepaymentModel, notional, spread)
        # new parameter added
        # TD should this be curCoupon?
        self.firstCoupon = firstCoupon
        self.prepaymentModel = prepaymentModel


    def getCashflows(self, reportingDate, remainingAmount, curve):
        # getCashflows method is re-defined for Level Pay product
        cashflows = []
        # TD consider to count from reporting date forward as deals can be started 20 yrs ago
        n = len(self.payDates)
        # TD 0607 instantiate prepayment model for the transaction, to cater for behavioural life, need to input age
        behModel = loadBehModel(self.prepaymentModel)
        smm = behModel.smm()
        # TD 0604 changed end range to n, as n-1 was giving 2 less cashflows vs required
        for i in range(0, n):
            curDate = self.payDates[i]
            if curDate <= reportingDate:
                continue
            if i == 0:
                prevDate = reportingDate
            else:
                prevDate = self.payDates[i-1]
            if prevDate < reportingDate:
                prevDate = reportingDate
            
            if i == 1:
                # TD this works if we count from reporting date, not origination, change to use current coupon
                # conversion to monthly equivalent is done at data load
                r = self.firstCoupon
            else:
                # customer rate from the previous period
                # conversion of spread to monthly equivalent is done at data load
                r = curve.cr(self.spread, prevDate, curDate, False)
            # TD 0604 changed formula from n to n-1 to correct level pay result
            A = pow(1 + r, n-1)
            # TD consider keeping these results (eg as lists?)
            # kept beginning month balance for later output
            beginningAmount = remainingAmount
            interest = remainingAmount * r
            payment = remainingAmount * r * A / (A-1)
            principal = payment - interest
            remainingBeforePrepay = remainingAmount - principal
            # TD 0608 removed hard coded smm
            # smm = 1.0 - ((1.0 - 0.12) ** (1.0 / 12.0))
            prepayment = smm * remainingBeforePrepay
            remainingAmount = remainingBeforePrepay - prepayment
            n = n - 1
            # 0604 added more output values for testing
            cashflows.append(Cashflow(self.id, curDate, beginningAmount, r, principal, prepayment, interest, remainingAmount))
        return cashflows        


def ToLevelPay(line):
    # TD what's the difference between this ToLevelPay and the one below?
    return None


'''=========================================== Behavioural Cashflow Module ========================================='''


class BehModel:

    def __init__(self, modelName, modelType, modelValue):
        self.modelName = modelName
        self.modelType = modelType
        self.modelValue = modelValue

    def smm(self, age = 1):
        result = 0.0
        if self.modelType == "CPR":
            result = 1.0 - pow((1.0 - self.modelValue), 1.0 /12.0)
        if self.modelType == "Beh_Life":
            # age here is assumed to be updated after the cashflow cal
            result = 1.0 / (self.modelValue - age)
        return result


'''=============================================== New Business Module ============================================='''


class NewBusiness:

    def __init__(self, payDate, remainingBalance, targetBalance, originalMaturity, paymentFrequency, resetFrequency, index, spread = 0):
        self.payDate = payDate
        self.remainingBalance = remainingBalance
        self.targetBalance = targetBalance
        self.originalMaturity = originalMaturity
        self.paymentFrequency = paymentFrequency
        self.resetFrequency = resetFrequency
        self.index = index
        self.spread = spread

    def generateNew(self, period, curve):
        # used the same logic as dummy deal creation
        # TD merge dummy deal creation with new business generation
        item = Object()
        # TD consistent way to generate new deal it across the new business run
        item.id = period
        item.origDate = self.payDate
        item.settlementDate = self.payDate
        # feasibility test case maturity date is 2046, 12, 15, set to 2017 for unit testing
        # adding attributes and their values to the data instance
        setattr(item, "maturityDate", self.origDate + relativedelta(months = self.originalMaturity))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "notional", self.targetBalance - self.remainingBalance)
        setattr(item, "spread", self.spread / 12)
        setattr(item, "firstCoupon", curve.cr(self.spread, self.origDate, self.origDate + relativedelta(months = self.resetFrequency), False))
        setattr(item, "remainingAmount", self.targetBalance - self.remainingBalance)
        setattr(item, "prepaymentModel", 'varMortgageCPR')

        return item


'''============================================== Results Output Module ============================================'''


class Cashflow:
    # takes output of the getCashflow function and write to csv
    # TD write out with csv headings, will this affect how pyxll reads the results?
    # 0604 added more output values for testing

    def __init__(self, id, paymentDate, beginning, rate, principal, prepayment, interest, remaining):
        self.id = id
        self.paymentDate = paymentDate
        self.beginning = beginning
        self.rate = rate * 100 * 12     # rate is converted from decimal to % for testing
        self.scheduled = principal + interest
        self.interest = interest
        self.principal = principal
        self.prepayment = prepayment
        self.remaining = remaining

    def AsCsv(self):
        result = "{0},{1},{2},{3},{4},{5},{6},{7},{8}".format(self.id, self.paymentDate, self.beginning, self.rate, self.scheduled, self.interest, self.principal, self.prepayment, self.remaining)
        return [result]


'''======================================== Google Cloud Integration Module ========================================='''


def ToLevelPay(data):
    value = LevelPay(data.id, data.settlementDate, data.maturityDate, data.paymentFrequency, data.prepaymentModel, data.notional, data.spread, data.firstCoupon)
    # set will only affect the instance not the class that created the instance
    setattr(data, "product", value)
    return data


def runCF():
    runTime = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    reportingDate = date(2016, 12, 31)
    # spot curve generated in memory, TD load from local / how to switch easily
    curve = getCurve(reportingDate)
    # dummy data generated in memory, changed data volume to 1 transaction for unit testing, , TD load from local / how to switch easily
    data = CreateData(reportingDate, 1)
    # load the behavioural model assumptions
    # behModel = loadBehModel()
    pp = beam.Pipeline('DirectRunner')

    '''
    the overall flow of the cashflow processes
    1. load in market data
    2. load in transaction data
    3. load in business assumption (eg behaviouralisation, prepayment, new business ...) 
    4. calculate contractual cashflow
    5. calculate behavioural cashflow
    6. calculate FTP (not in scope for initial feasibility assessment)
    7. generate new business (for NII runs only)
    '''
    # no comments can be added in between the pipeline process below
    # each row in pipeline takes the output from previous
    # 0603 change results save to generic C drive with a time stamp in the output file name
    # | 'Save results' >> beam.io.WriteToText('C:\Users\huibr\Documents\Visual Studio 2015\Projects\PlayBeam\cashflows.csv')

    pp \
        | 'Create products' >> beam.Create(data) \
        | 'Convert to LevelPay' >> beam.Map(ToLevelPay) \
        | 'Generate cashflows' >> beam.FlatMap(lambda data: data.product.getCashflows(data.reportingDate, data.remainingAmount, curve)) \
        | 'To text' >> beam.FlatMap(lambda x: x.AsCsv()) \
        | 'Save results' >> beam.io.WriteToText('C:\IRR_CF_Results\cashflows_' + runTime + '.csv')

    pp.run();

'''
#        | 'Read products' >> beam.io.Read(CsvFileSource('C:\Users\huibr\Documents\Visual Studio 2015\Projects\PlayBeam\products.csv')) \
#        | 'Read products' >> beam.io.ReadFromText('C:\Users\huibr\Documents\Visual Studio 2015\Projects\PlayBeam\products.csv') \
    #pc = beam.Pipeline('DirectRunner')

    #pc \
    #    | 'Read Tenors' >> beam.io.ReadFromText('C:\Users\huibr\Documents\Visual Studio 2015\Projects\PlayBeam\tenors.csv') \
    #    | 'Convert to Tenor' >> beam.Map(ToTenor) \
    #    | 'Group tenors by curve' >> beam.GroupByKey(lambda t: t.curveName)
#        | 'Calculate Cashflows' >> beam.FlatMap(lambda x: x.toCashflows())

    #products = [LevelPay(1, 100, 0.001, 'GBP', 60), LevelPay(2, 200, 0.02, 'GBP', 120)]
    #res = products | beam.FlatMap(lambda x: x.getCashflows([1, 2, 3]))
    #print res
'''
'''======================================== Excel Plugin Integration Module ========================================='''
'''
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
'''

if __name__ == "__main__":
    runCF()




