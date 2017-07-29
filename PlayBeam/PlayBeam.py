from __future__ import absolute_import
# TD what's the purpose of this?

# functional libraries used
from datetime import date, datetime
from dateutil.relativedelta import *

# technical distribution libraries used
import apache_beam as beam
import argparse
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions


# feedback 170705 meeting with Svetlana, Gilbert
# separate between back and new volume (and other reporting dimension tagging)
# get full list of metrics / dimensions needed (Ghaz?)
# product control will produce projected YC values on daily basis, need to establish working process
# interpolation methods (eg if input projected curves are not complete)
# defaults / simplifications in LIQ must not affect IRR


'''==================================== Overarching Design Principles =============================='''
# clarity
# functional transparency before performance / system optimisation

# business friendly
# users / business should be able to read code blocks at high level and relate to functional feature

# flexibility
# aim to allow maximal "externally fed in" setup instead of "internally hard coded"

# consistency
# variable naming should be standardised and self explanatory, abbreviations should only be used when there is absolutely no ambiguity

# no duplication
# the same funcationality should be implemented only once, avoid the need to deploy the same changes multiple places

# unification
# all sites should be able to run with the same build, only differ by input data, avoid need to maintain multiple versions for sites

# one finance
# over lapping processes between IRR / LIQ should be built so they can both utilise this cashflow engine
'''==================================== Python / Google Best Practice =============================='''
# module_name,package_name,method_name,function_name,global_var_name,instance_var_name,function_parameter_name,local_var_name
# ClassName, ExceptionName
# GLOBAL_CONSTANT_NAME

# dictionary literal:
# instead of dic = {} then dic['aaa'] = 5, use dic = {'aaa': 5}

# return multiple results from a function using named tuples:
# using namedtuple allows for both results[0] and results.sample_data references
# import collections
# results = collections.namedtuple('point', 'sample_data,base_volume')(sample_data, base_volume)

# p.run().wait_until_finish() is needed if next step depends on full pipeline completion

# shadowing names defined in outer scopes should be avoided
# functions should generally not refer to global variables
# or local variables with same names as global (ie outter) variables

# code management usnig github
# 

'''==================================== Transaction, Market, Behavioural Input Module =============================='''


# load run time parameters
def loadRunParameters():
    runParameters = {
        'reportingDate': date(2016, 12, 31),
        'projectionPeriod': 24,
        'maxHorizon': 480,
        'cashflowOutputPath': "C:\IRR_CF_Results\cashflows_output_",
        'cashflowOutputHeader': "Deal_ID,Payment_Date,Beginning_Balance,Interest_Rate,Scheduled_Total,Interest_Payment,Principal_Payment,Prepayment,Remaining_Balance",
        'incomeOutputPath': "C:\IRR_CF_Results\income_output_",
        'incomeOutputHeader': "Deal_ID,Month_End_Date,Income_Accrual,Payment_Date,Interest_Paid",
        'outputFormat': ".csv",
        'logOutputPath': "C:\IRR_CF_Results\log_output_",
        'logOutputHeader': "Start_Time,End_Time,Duration,Product,Existing_Deal_Count,New_Deal_Count,Cashflow_Lines,Income_Lines,Cashflow_File_Size(MB),Income_File_Size(MB)",
        'shock': 0,
        # data definition format: product, volume, shock
        # TD for now, assuming each run is only for a specific market shock, consider whether we want to define shock at the deal level
        'dataDefinitions': [
            DataDefinition("IBCA", 10),
            DataDefinition("NIBCA", 10),
            DataDefinition("Mortgage", 10),
            ],
        # runner options: DirectRunner, DataflowRunner
        # for each runner, a different input / output path is defined in run()
        'runner': "DataflowRunner",
        # data options: GenerateData, LoadData
        'dataSource': "LoadData",
        'transactionMeta': [('dealID','string'),('reportingDate', 'date'), ('productName','string'), ('settlementDate', 'date'), ('maturityDate', 'date'), ('paymentFrequency', 'integer'), ('spread', 'float'), ('currentCoupon', 'float'), ('remainingAmount', 'float'), ('amortizationType','string'), ('prepaymentModel','string'), ('rateIndex','string'), ('dayCount','string')],
        'localTransactionData': 'C:/Users/charl/Google Drive/10. Coding/9. IRR CF Engine Python/Google Cloud/input data/10-2017-07-29-05-56-27/*',
        'localCashflowOutput': 'C:/Users/charl/Google Drive/10. Coding/9. IRR CF Engine Python/Google Cloud/output results/cashflow-',
        'localIncomeOutput': 'C:/Users/charl/Google Drive/10. Coding/9. IRR CF Engine Pythoin/Google Cloud/output results/income-',
        'cloudTransactionDate': 'gs://sweet-gooseberry-upload/IRR_CF_Engine/input/30x100000-2017-07-29-07-19-02/*',
        'cloudCashflowOutput': 'gs://sweet-gooseberry-upload/IRR_CF_Engine/output/cashflow-results-30x100k-',
        'cloudIncomeOutput': 'gs://sweet-gooseberry-upload/IRR_CF_Engine/output/income-results-30x100k-',
        'jobName': 'sweetgooseberry-145819-irr-test-30x100k-',
        'autoscaling': 'NONE',  # options NONE, THROUGHPUT_BASED, google's' autoscaling is suited for much (much) larger datasets
        'num_workers': '25',  # this should be conservative vs resourse quota (24-25 on us-central1, as of 201707), if over limit can create errors
    }
    return runParameters

class Object(object):
    pass


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
    result = Curve("GBP_LIBOR_1M", reportingDate, tenors)
    return result


def createCurveDict(reportingDate, shock):
    YC_GBP_LIBOR_1M = getCurve(reportingDate).shock("GBP_LIBOR_1M", shock)

    curveDict = {
        'YC_GBP_LIBOR_1M': YC_GBP_LIBOR_1M
    }
    return curveDict


def createIndexDict(reportingDate, curveDict):
    indexDict = {}
    RI_Zero_Rate = ZeroIndex("RI_Zero_Rate")
    indexDict['RI_Zero_Rate'] = RI_Zero_Rate
    RI_GBP_LIBOR_1M = StandardRateIndex("RI_GBP_LIBOR_1M", 'YC_GBP_LIBOR_1M', 1, curveDict, date(2017, 1, 15), 0.00364435205)
    indexDict['RI_GBP_LIBOR_1M'] = RI_GBP_LIBOR_1M
    RI_IBCA_Pass_On = PassOnIndex("RI_IBCA_Pass_On", "RI_GBP_LIBOR_1M", 0.2, indexDict, date(2017, 1, 15), 0.5/100)
    indexDict['RI_IBCA_Pass_On'] = RI_IBCA_Pass_On
    return indexDict


def loadBehModel(tranModelName):
    # TD add ability to load multiple models into the same instance
    models = []
    models.append(BehModel('Mortgage_CPR', 'CPR', 0.12))
    models.append(BehModel('NIBCA_Beh_Life', 'Beh_Life', 12))
    models.append(BehModel('IBCA_Beh_Life', 'Beh_Life', 6))
    models.append(BehModel('none', 'none', 0))
    # TD can be re-written using next() / list comprehension
    for i in range(0, len(models)):
        if models[i].modelName == tranModelName:
            # TD result should copy directly from the object in list, instead of having to re-instantiate
            result = BehModel(models[i].modelName, models[i].modelType, models[i].modelValue)
    return result


# NIBCA Load
def CreateNIBCAData(reportingDate, count):
    # generate testing data in memory, this is very useful for unit testing
    # the new feature of reading from file should be built in parallel to this, so use can choose data sourcing method
    result = []
    for i in range(0, count):
        item = Object()
        item.reportingDate = reportingDate
        # TD due to parallel processing, synthetic data will not have unique id
        item.dealID = i
        item.settlementDate = date(2016, 12, 15)
        # feasibility test case maturity date is 2046, 12, 15, set to 2017 for unit testing
        # adding attributes and their values to the data instance
        setattr(item, "maturityDate", date(2017, 12, 15))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "spread", 0.0/100)
        setattr(item, "currentCoupon", 0.0/100)
        setattr(item, "remainingAmount", 1500000.0)
        setattr(item, "amortizationType", "Bullet")
        setattr(item, "prepaymentModel", "NIBCA_Beh_Life")
        setattr(item, "rateIndex", "RI_Zero_Rate")
        setattr(item, "dayCount", "30/360")
        setattr(item, "productName", "NIBCA")

        result.append(item)
    return result

def loadNIBCANewBus():
    # target month end total balance for 25 months
    # TD solution for potential negative growth
    targetBalanaces = [BalTarget(1, 1500000),
                      BalTarget(2, 1500000),
                      BalTarget(3, 1500000),
                      BalTarget(4, 1500000),
                      BalTarget(5, 1500000),
                      BalTarget(6, 1500000),
                      BalTarget(7, 1500000),
                      BalTarget(8, 1500000),
                      BalTarget(9, 1500000),
                      BalTarget(9, 1500000),
                      BalTarget(10, 1500000),
                      BalTarget(11, 1500000),
                      BalTarget(12, 1500000),
                      BalTarget(13, 1500000),
                      BalTarget(14, 1500000),
                      BalTarget(15, 1500000),
                      BalTarget(16, 1500000),
                      BalTarget(17, 1500000),
                      BalTarget(18, 1500000),
                      BalTarget(19, 1500000),
                      BalTarget(20, 1500000),
                      BalTarget(21, 1500000),
                      BalTarget(22, 1500000),
                      BalTarget(23, 1500000),
                      BalTarget(24, 1500000),
                      BalTarget(25, 1500000)]
    result = targetBalanaces
    return result


# IBCA Load
def CreateIBCAData(reportingDate, count):
    # generate testing data in memory, this is very useful for unit testing
    # the new feature of reading from file should be built in parallel to this, so use can choose data sourcing method
    result = []
    for i in range(0, count):
        item = Object()
        item.reportingDate = reportingDate
        item.dealID = i
        item.settlementDate = date(2016, 12, 15)
        # feasibility test case maturity date is 2046, 12, 15, set to 2017 for unit testing
        # adding attributes and their values to the data instance
        setattr(item, "maturityDate", date(2017, 6, 15))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "spread", 0.0/100)
        setattr(item, "currentCoupon", 0.5/100)
        setattr(item, "remainingAmount", 1000000.0)
        setattr(item, "amortizationType", "Bullet")
        setattr(item, "prepaymentModel", "IBCA_Beh_Life")
        # IBCA Index IBCA_Pass_On, test index USD_1M_LIBOR
        setattr(item, "rateIndex", "RI_IBCA_Pass_On")
        setattr(item, "dayCount", "30/360")
        setattr(item, "productName", "IBCA")

        result.append(item)
    return result

def loadIBCANewBus():
    # target month end total balance for 25 months
    targetBalanaces = [BalTarget(1, 1000000),
                      BalTarget(2, 1000000),
                      BalTarget(3, 1000000),
                      BalTarget(4, 1000000),
                      BalTarget(5, 1000000),
                      BalTarget(6, 1000000),
                      BalTarget(7, 1000000),
                      BalTarget(8, 1000000),
                      BalTarget(9, 1000000),
                      BalTarget(9, 1000000),
                      BalTarget(10, 1000000),
                      BalTarget(11, 1000000),
                      BalTarget(12, 1000000),
                      BalTarget(13, 1000000),
                      BalTarget(14, 1000000),
                      BalTarget(15, 1000000),
                      BalTarget(16, 1000000),
                      BalTarget(17, 1000000),
                      BalTarget(18, 1000000),
                      BalTarget(19, 1000000),
                      BalTarget(20, 1000000),
                      BalTarget(21, 1000000),
                      BalTarget(22, 1000000),
                      BalTarget(23, 1000000),
                      BalTarget(24, 1000000),
                      BalTarget(25, 1000000)]
    result = targetBalanaces
    return result


# Mortgage Load
def CreateMortgageData(reportingDate, count):
    # generate testing data in memory, this is very useful for unit testing
    # the new feature of reading from file should be built in parallel to this, so use can choose data sourcing method
    result = []
    for i in range(0, count):
        item = Object()
        item.reportingDate = reportingDate
        item.dealID = i
        item.settlementDate = date(2016, 12, 15)
        # feasibility test case maturity date is 2046, 12, 15, set to 2017 for unit testing
        # adding attributes and their values to the data instance
        setattr(item, "maturityDate", date(2017, 12, 15))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "spread", 2.5/100)
        setattr(item, "currentCoupon", 3.5/100)
        setattr(item, "remainingAmount", 1000000.0)
        setattr(item, "amortizationType", "Level Pay")
        setattr(item, "prepaymentModel", "Mortgage_CPR")
        setattr(item, "rateIndex", "RI_GBP_LIBOR_1M")
        setattr(item, "dayCount", "30/360")
        setattr(item, "productName", "Mortgage_Floating")

        result.append(item)
    return result

def loadMortgageNewBus():
    # target month end total balance for 25 months
    targetBalanaces = [BalTarget(1, 1000000),
                      BalTarget(2, 1000000),
                      BalTarget(3, 1000000),
                      BalTarget(4, 1000000),
                      BalTarget(5, 1000000),
                      BalTarget(6, 1000000),
                      BalTarget(7, 1000000),
                      BalTarget(8, 1000000),
                      BalTarget(9, 1000000),
                      BalTarget(9, 1000000),
                      BalTarget(10, 1000000),
                      BalTarget(11, 1000000),
                      BalTarget(12, 1000000),
                      BalTarget(13, 1000000),
                      BalTarget(14, 1000000),
                      BalTarget(15, 1000000),
                      BalTarget(16, 1000000),
                      BalTarget(17, 1000000),
                      BalTarget(18, 1000000),
                      BalTarget(19, 1000000),
                      BalTarget(20, 1000000),
                      BalTarget(21, 1000000),
                      BalTarget(22, 1000000),
                      BalTarget(23, 1000000),
                      BalTarget(24, 1000000),
                      BalTarget(25, 1000000)]
    result = targetBalanaces
    return result



'''=========================================== Market Projection Module ============================================'''


def linearDistance(x2, x1):
    result = float(x2 - x1)
    return result


def datediff(d2, d1):
    result = float((d2 - d1).days)
    return result


def diff_month(start_date, end_date):
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month


def linear_interpolation(x1, y1, x2, y2, x, distanceMeasure = linearDistance):
    result = y1 + (y2 - y1)*distanceMeasure(x, x1)/distanceMeasure(x2, x1)
    return result


def exponential_interpolation(x1, y1, x2, y2, x, distanceMeasure = datediff):
    result = y1 * pow((y2 / y1), distanceMeasure(x, x1) / distanceMeasure(x2, x1))
    return result


def isLeap(date):
    year = date.year
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def incrementalActAct(fromdate, todate):
    if isLeap(fromdate)==False and isLeap(todate)==False:
        result = (todate.toordinal() - fromdate.toordinal())/365.0
    elif isLeap(fromdate)==True and isLeap(todate)==True:
        result = (todate.toordinal() - fromdate.toordinal()) / 366.0
    elif isLeap(fromdate) == False and isLeap(todate) == True:
        result = 1/365.0 + (todate.toordinal() - fromdate.toordinal() -1) / 366.0
    else:
        result = 1 / 366.0 + (todate.toordinal() - fromdate.toordinal() - 1) / 365.0
    return result


def act356(fromDate, toDate):
    result = (toDate.toordinal() - fromDate.toordinal()) / 365.0
    return result


def discfactor(spotRate, yearFraction):
    """Discount factor"""
    return 1.0/pow((1.0 + spotRate), yearFraction)


def discToForward(curDate, discCurDate, nextDate, discNextDate):
    result = pow(discCurDate / discNextDate, 1 / incrementalActAct(curDate, nextDate)) - 1
    return result


class Tenor:

    def __init__(self, date, rate):
        self.date = date
        self.rate = rate


class Curve:

    def __init__(self, dealID, reportingDate, tenorList, dayCountFunc = act356, interpFunc = linear_interpolation):
        self.dealID = dealID
        self.reportingDate = reportingDate
        self.tenorList = tenorList
        self.dayCountFunc = dayCountFunc
        self.tenorDict = { x.date: x.rate for x in tenorList }
        # tenor dictionary to capture all month end spot rate
        self.tenorDict = {}
        # discount factor dictionary to capture all month end
        self.discDict = {}
        # forward rate dictionary to capture all month end
        self.forwardDict = {}
        self.interpFunc = interpFunc
        # trigger the init method of the class when initiating a new instance
        self.init()


    def shock(self, curveID, bps):
        """Instant Parallel Shock to Spot Curve"""
        # TD this shock approach only works for parallel shock for EVE
        # to be revised with flexibility to imply then shock and none parallel shock
        shockedTenors = map(lambda x: Tenor(x.date, x.rate + bps), self.tenorList)
        result = Curve(curveID, self.reportingDate, shockedTenors, self.dayCountFunc, self.interpFunc)
        return result


    def init(self):
        """Expand the spot curve to monthly tenor until 30 years, generate month end discount factors and forward rates"""
        curDate = self.reportingDate
        endDate = curDate.replace(year = curDate.year + 30)
        prevIndex = 0
        nextIndex = 1
        prevTenor = self.tenorList[prevIndex]
        nextTenor = self.tenorList[nextIndex]
        maxIndex = len(self.tenorList) - 1
        while curDate <= endDate:
            if curDate >= self.tenorList[nextIndex].date and nextIndex < maxIndex:
                nextIndex += 1
                prevIndex += 1
                prevTenor = nextTenor
                nextTenor = self.tenorList[nextIndex]
            else:
                # Perform interpolation on rate
                self.tenorDict[curDate] = self.interpFunc(prevTenor.date,prevTenor.rate,nextTenor.date,nextTenor.rate,curDate,self.dayCountFunc)
                self.discDict[curDate] = discfactor(self.tenorDict[curDate], self.dayCountFunc(self.reportingDate, curDate))
                if curDate > self.reportingDate:
                    self.forwardDict[prevDate] = discToForward(prevDate, self.discDict[prevDate], curDate, self.discDict[curDate])

                prevDate = curDate
                curDate = curDate + relativedelta(day = 1, months = 2, days=-1)


    def discfactor(self, curDate):
        """Returns the annualised forward rate between two dates"""
        prevMEDate = curDate + relativedelta(day=1, days=-1)
        curMEDate = curDate + relativedelta(day=1, months=1, days=-1)
        prevMEDict = self.discDict[prevMEDate]
        curMEDict = self.discDict[curMEDate]
        result = exponential_interpolation(prevMEDate, prevMEDict, curMEDate, curMEDict, curDate, distanceMeasure=datediff)
        return result

    def forwardRate(self, fromDate, toDate):
        result = discToForward(fromDate, self.discfactor(fromDate), toDate, self.discfactor(toDate))
        return result

    def __add__(self, other):
        """Defines addition of two curves - used to for instant non parallel shock"""
        # curve1.__add__(curve2) defines the behaviour of curve1 + curve2
        pass


class Scenario:

    def __init__(self, reportingDate, curve):
        self.reportingDate = reportingDate
        self.curve = curve


class StandardRateIndex:
    # create rate index object to store month end index values
    # if index object already contains rate for a repricing date, then read directly, otherwise calculate
    # TD performance expansion to only caluculate month end, then linearly interpolate
    def __init__(self, rateIndexName, marketCurve, tenorPoint, curveDict, startingDate = None, startingRate = None):
        self.rateIndexName = rateIndexName
        # a index object dictionary is created first to convert strings into objects
        self.marketCurve = curveDict[marketCurve]
        self.tenorPoint = tenorPoint
        self.rateIndexType = 'standard'
        self.startingDate = startingDate
        self.startingRate = startingRate
        self.projection = {}
        self.projection[self.startingDate] = self.startingRate

    def calculateNew(self, projectionDate):
        """Add period ending rate on the projection date to rate projection results"""
        fromDate = projectionDate + relativedelta(months=-self.tenorPoint)
        toDate = projectionDate
        newRate = self.marketCurve.forwardRate(fromDate, toDate)
        self.projection[projectionDate] = newRate

    def rateExist(self, projectionDate):
        """Check if rate forecast already exists for the projection date"""
        if projectionDate in self.projection:
            return True
        else:
            return False

    def getRate(self, projectionDate):
        """Generate the period ending rate on the projection date"""
        if self.rateExist(projectionDate) == False:
            # if no rate exists for the required date, calculated the rate and store into projection dict then output rate
            self.calculateNew(projectionDate)
        return self.projection[projectionDate]


class ZeroIndex(StandardRateIndex):
    def __init__(self, rateIndexName):
        self.rateIndexName = rateIndexName
        self.rateIndexType = 'fixed'

    def getRate(self, projectionDate):
        return 0


class PassOnIndex(StandardRateIndex):

    def __init__(self, rateIndexName, baseIndex, passOn, indexDict, startingDate = None, startingRate = None):
        self.rateIndexName = rateIndexName
        self.baseIndex = indexDict[baseIndex]
        self.rateIndexType = 'pass on'
        self.passOn = passOn
        self.startingDate = startingDate
        self.startingRate = startingRate
        self.projection = {}
        self.projection[self.startingDate] = self.startingRate

    def calculateNew(self, projectionDate):
        """Rate passthrough derivation"""
        previousProjectionDate = projectionDate + relativedelta(months=-1)
        if previousProjectionDate in self.projection:
            # if previous managed rate value exists in projection dict, then calculate for current period
            previousBaseRate = self.baseIndex.getRate(previousProjectionDate)
            currentBaseRate = self.baseIndex.getRate(projectionDate)
            baseRateMove = currentBaseRate - previousBaseRate
            newRate = self.projection[previousProjectionDate] + self.passOn * baseRateMove
            # add rate for projectoin date into projection dictionary
            self.projection[projectionDate] = newRate
        else:
            # find the rate value for the latest known date, then iterate until reaching projectionDate
            lastKnownDate = max(self.projection.iterkeys())
            intermediateDate = lastKnownDate + relativedelta(months=1)
            while intermediateDate <= projectionDate:
                self.calculateNew(intermediateDate)
                intermediateDate = intermediateDate + relativedelta(months=1)


class Rate():

    def __init__(self, annualRate, dayCount):
        self.annualRate = annualRate
        self.dayCount = dayCount

    def convertByConvention(self):
        if self.dayCount == "30/360":
            return self.annualRate / 12


'''=========================================== Cashflow Module ========================================='''

def TransactionToProduct(transaction):

    if transaction.amortizationType == "Level Pay":
        product = LevelPay(transaction)
    else:
        product = Bullet(transaction)
    return product


class Product:

    def __init__(self, transaction):
        self.dealID = transaction.dealID
        # TD revise this to originationDate to align with terminology
        self.settlementDate = transaction.settlementDate
        self.maturityDate = transaction.maturityDate
        # paymentFrequency is read as an integer for number of months
        self.paymentFrequency = transaction.paymentFrequency
        self.remainingAmount = transaction.remainingAmount
        self.spread = transaction.spread
        self.rateIndex = transaction.rateIndex
        self.payDates = []
        self.initPayDates()
        self.currentCoupon = transaction.currentCoupon
        self.prepaymentModel = transaction.prepaymentModel
        self.dayCount = transaction.dayCount


    def initPayDates(self):
        # TD consider separate logic for pay / repricing date derivation
        stopDate = self.settlementDate
        curDate = self.maturityDate
        # TD 0604 added the maturityDate to the payDates list
        self.payDates.append(curDate)
        while curDate > stopDate:
            curDate = curDate + relativedelta(months = -self.paymentFrequency)
            # Add modified following
            # TD when will this condition be false? given the parent while condition
            self.payDates.append(curDate)
        self.payDates.reverse()

    def getCashflows(self, reportingDate, curve):
        # TBC what should be the default method here? (Bullet or Security Schedule?)
        cashflows = []
        return cashflows


class LevelPay(Product):
    # LevelPay is a subclass of the Product class, can use print(help(LevelPay)) to see resolution order
    # variables re-specified in subclass will overwrite their values in the parent class

    def __init__(self, transaction):
        # added so the LevelPay class can take in additional parameters than its parent class Product
        # alternative is super().__init__(transaction)
        Product.__init__(self, transaction)


    def getCashflows(self, reportingDate, indexDict):
        remainingAmount = self.remainingAmount
        # getCashflows method is re-defined for Level Pay product
        cashflows = []
        # TD consider to count from reporting date forward as deals can be started 20 yrs ago
        n = len(self.payDates)
        # TD 0607 instantiate prepayment model for the transaction, to cater for behavioural life, need to input age
        behModel = loadBehModel(self.prepaymentModel)
        smm = behModel.smm()


        for i in range(0, n):
            curDate = self.payDates[i]
            if i == 0:
                # TD purpose?
                prevDate = reportingDate
            else:
                prevDate = self.payDates[i-1]
            if curDate <= reportingDate:
                continue
            elif prevDate <= reportingDate:
                # TD need to separate reset from payment timing
                # for first payment, use currentCoupon from data, derive from curve for later coupons
                annualRate = self.currentCoupon
            else:
                # customer rate from the previous period
                # conversion of spread to monthly equivalent is done at data load
                annualRate = indexDict[self.rateIndex].getRate(curDate) + self.spread

            r = Rate(annualRate,  self.dayCount).convertByConvention()

            A = pow(1 + r, n-1)
            # TD consider keeping these intermediate results
            # kept beginning month balance for later output
            beginningAmount = remainingAmount
            interest = beginningAmount * r
            payment = beginningAmount * r * A / (A-1)
            principal = payment - interest
            remainingBeforePrepay = beginningAmount - principal
            prepayment = smm * remainingBeforePrepay
            remainingAmount = remainingBeforePrepay - prepayment
            n = n - 1
            # 0604 added more output values for testing
            cashflows.append(Cashflow(self.dealID, curDate, beginningAmount, r, principal, prepayment, interest, remainingAmount))
        return cashflows


class Bullet(Product):

    def __init__(self, transaction):
        # alternative is super().__init__(transaction)
        Product.__init__(self, transaction)


    def getCashflows(self, reportingDate, indexDict):
        remainingAmount = self.remainingAmount
        cashflows = []
        n = len(self.payDates)
        # TD 0607 instantiate prepayment model for the transaction, to cater for behavioural life, need to input age
        # TD different approach from loading YC / RI, to establish consistency
        behModel = loadBehModel(self.prepaymentModel)

        # TD 0604 changed end range to n, as n-1 was giving 2 less cashflows vs required
        for i in range(0, n):
            curDate = self.payDates[i]
            if i == 0:
                prevDate = reportingDate
            else:
                prevDate = self.payDates[i - 1]

            if curDate <= reportingDate:
                continue
            elif prevDate <= reportingDate:
                # for first payment, use currentCoupon from data, derive from curve for later coupons
                annualRate = self.currentCoupon
            else:
                annualRate = indexDict[self.rateIndex].getRate(curDate) + self.spread

            r = Rate(annualRate, self.dayCount).convertByConvention()
            beginningAmount = remainingAmount
            interest = beginningAmount * r
            if curDate < self.maturityDate:
                principal = 0
            else:
                principal = beginningAmount
            age = diff_month(self.settlementDate, self.payDates[i])
            remainingAmount = beginningAmount - principal
            smm = behModel.smm(age)
            prepayment = smm * remainingAmount
            remainingAmount = remainingAmount - prepayment
            n = n - 1
            # 0604 added more output values for testing
            cashflows.append(Cashflow(self.dealID, curDate, beginningAmount, r, principal, prepayment, interest, remainingAmount))
        return cashflows

def ToLevelPay(line):
    # TD what's the difference between this ToLevelPay and the one below?
    return None


'''=========================================== Behavioural Model Module ========================================='''


class BehModel:

    def __init__(self, modelName, modelType, modelValue):
        self.modelName = modelName
        self.modelType = modelType
        self.modelValue = modelValue

    def smm(self, age = 1):
        result = 0.0
        # TD have model types as sub classes so we don't need to change existing class, instead of expanding existing, just create new sub objects
        if self.modelType == "CPR":
            result = 1.0 - pow((1.0 - self.modelValue), 1.0 /12.0)
        elif self.modelType == "Beh_Life":
            # age here is assumed to be number of months since origination
            result = 1.0 / (self.modelValue - age + 1)
        else:
            result = 0
        return result


'''============================================== Income Conversion Module ============================================'''


class IncomeAccrual:

    # 170720 modified to take in cashflows list and output incomes list, instead of only taking in a single cashflow
    def __init__(self, cashflows, transaction):

        self.cashflows = cashflows
        self.paymentFrequency = transaction.paymentFrequency

    def getIncomes(self):

        incomes = []
        for cashflow in self.cashflows:
            dealID = cashflow.dealID
            paymentDate = cashflow.paymentDate
            interest = cashflow.interest
    
            currentPaymentDate = cashflow.paymentDate
            previousPaymentDate = currentPaymentDate + relativedelta(months=- self.paymentFrequency)
            paymentDays = (currentPaymentDate - previousPaymentDate).days
    
            perDayIncome = interest / paymentDays
        
            # first month end date is the month end date of the previous payment
            monthEndDate = previousPaymentDate + relativedelta(day=1, months=+1, days=-1)

            # 0613 the accrual system will back calculate monthly income even for months prior to reporting date
            # this is useful during build, but can build a stopper condition for better performance
            # payment frequency is the number of months between payments
            for i in range(0, self.paymentFrequency + 1):
                if monthEndDate < previousPaymentDate + relativedelta(day=1, months=+2, days=-1):
                    # accrual in the previous payment month
                    daysAccrued = monthEndDate.day - previousPaymentDate.day
                elif monthEndDate >= currentPaymentDate:
                    # if next month end is the current payment month, then proportional accrual
                    daysAccrued = currentPaymentDate.day
                else:
                    # if next month is before the current payment month, then full month accrual
                    daysAccrued = monthEndDate.day
                monthAccrual = daysAccrued * perDayIncome
                # write output to incomes list
                incomes.append(Income(dealID, monthEndDate, monthAccrual, paymentDate, interest))
                monthEndDate = monthEndDate + relativedelta(day=1, months=+2, days=-1)

        return incomes


'''=============================================== New Business Module ============================================='''


class NewBusiness:

    def __init__(self, payDate, remainingBalance, targetBalance, transaction, indexDict):
        # input attributes
        self.payDate = payDate
        self.remainingBalance = remainingBalance
        self.targetBalance = targetBalance

        # derived attributes
        # contractual features for new vol is data driven, can add feature to switch between assumption and adta driven
        self.dealID = payDate.strftime('%Y%m%d')
        self.origDate = self.payDate
        self.settlementDate = self.payDate
        self.originalMaturity = diff_month(transaction.settlementDate, transaction.maturityDate)
        self.maturityDate = self.origDate + relativedelta(months = self.originalMaturity)
        self.remainingAmount = self.targetBalance - self.remainingBalance
        self.settlementDate = self.payDate

        self.paymentFrequency = transaction.paymentFrequency
        self.dayCount = transaction.dayCount
        self.rateIndex = transaction.rateIndex
        self.spread = transaction.spread
        # TD 170628 temp work around to force new NML to be bullets
        if transaction.prepaymentModel in ('NIBCA_Beh_Life', 'IBCA_Beh_Life'):
            self.prepaymentModel = 'none'
        else:
            self.prepaymentModel = transaction.prepaymentModel
        self.amortizationType = transaction.amortizationType

        self.currentCoupon = indexDict[transaction.rateIndex].getRate(self.origDate + relativedelta(months=self.paymentFrequency)) + self.spread


class BalTarget:

    def __init__(self, period, balance):
        self.period = period
        self.balance = balance


# migration functionality postponed 170626 as per Stephen / Arnau's comment
# class BalMigration:
#
#     def __init__(self, migrationSource, migrationTarget,  )


'''============================================== Results Output Module ============================================'''


class Cashflow:
    # takes output of the getCashflow function and write to csv
    # TD write out with csv headings, will this affect how pyxll reads the results?
    # 0604 added more output values for testing

    def __init__(self, dealID, paymentDate, beginning, rate, principal, prepayment, interest, remaining):
        self.dealID = dealID
        self.paymentDate = paymentDate
        self.beginning = beginning
        self.rate = rate * 100 * 12     # rate is converted from decimal to % for testing
        self.scheduled = principal + interest
        self.interest = interest
        self.principal = principal
        self.prepayment = prepayment
        self.remaining = remaining

    def AsCsv(self):
        result = "{0},{1},{2},{3},{4},{5},{6},{7},{8}".format(self.dealID, self.paymentDate, self.beginning, self.rate, self.scheduled, self.interest, self.principal, self.prepayment, self.remaining)
        # 0610 removed [] around result to be tested
        # TD ability to define output fields differently for runs, via user parameter file
        return [result]


class Income:

    def __init__(self, dealID, monthEndDate, incomeAccrued, paymentDate, interest):
        self.dealID = dealID
        self.monthEndDate = monthEndDate
        self.incomeAccrued = incomeAccrued
        self.paymentDate = paymentDate
        self.interest = interest

    def AsCsv(self):
        result = "{0},{1},{2},{3},{4}".format(self.dealID, self.monthEndDate, self.incomeAccrued, self.paymentDate, self.interest)
        # 0610 removed [] around result to be tested
        return [result]


def ListToCSV(results_list):
    # this function should cover both cashflow and income results
    # it will read in a list of result objects, then apply object.AsCsv() to each, then product the combined results
    csv_results = []
    for result in results_list:
        csv_result = result.AsCsv()
        csv_results += csv_result
    return csv_results





'''======================================== Create Testing Data ========================================='''

class DataDefinition:

    def __init__(self, product, volume):
        self.product = product
        self.volume = volume


def CreateData(reportingDate, dataDefinitions):

    # master lists to store transaction data and their corresponding target balances
    localTransactionData = []
    localTargetBalanceData = []

    for dataDefinition in dataDefinitions:
        product = dataDefinition.product
        volume = dataDefinition.volume
        if product == "NIBCA":
            newData = CreateNIBCAData(reportingDate, volume)
            # list of balance target instances
            # this should be a deal level data load later on
            newTargetBal = [loadNIBCANewBus()]*volume
        elif product == "IBCA":
            newData = CreateIBCAData(reportingDate, volume)
            newTargetBal = [loadIBCANewBus()]*volume
        elif product == "Mortgage":
            newData = CreateMortgageData(reportingDate, volume)
            newTargetBal = [loadMortgageNewBus()]*volume
        localTransactionData = localTransactionData + newData
        localTargetBalanceData = localTargetBalanceData + newTargetBal


    # create combined list of objects, so each object of the master data list has the transaction and traget data
    masterDataList = []
    # pair up transaction data with its target balance, into a list of inputs, ready for ingestion by beam
    # beam requires each element in the list to contain full set of inputs required for parallel distribution
    for i in range(0, len(localTransactionData)):
        transactionLevelData = Object()
        # transactions is a list of transactions with position 0 the existing the new
        setattr(transactionLevelData, "transactions", [localTransactionData[i]])
        # target balance is stored at the existing deal level
        # each existing deal and its child deals share the same target balance list
        setattr(transactionLevelData, "targetBalance", localTargetBalanceData[i])
        masterDataList.append(transactionLevelData)
    return masterDataList


'''======================================== Load Input Data ========================================='''

def CreateRunObjects(csvData, runParameters):

    # working assumption is that csvData is a single line from the csv file, separated by ,
    # convert csv string into list
    data_list = csvData.split(",")
    # meta data is a list of tuples, each tuple has (field name, field type)
    transaction_meta = runParameters['transactionMeta']
    headers_count = len(transaction_meta)

    # initiate transaction level object to hold results
    transactionLevelData = Object()
    # load contractual features into transaction object
    transaction = Object()
    for i in range(headers_count):
        string_value = str(data_list[i])
        if transaction_meta[i][1] == 'string':
            data_value = string_value
        elif transaction_meta[i][1] == 'date':
            data_value = datetime.strptime(string_value, '%d/%m/%Y').date()
        elif transaction_meta[i][1] == 'float':
            data_value = float(string_value)
        elif transaction_meta[i][1] == 'integer':
            data_value = int(string_value)
        else:
            data_value = string_value
        setattr(transaction, transaction_meta[i][0], data_value)
    setattr(transactionLevelData, "transactions", [transaction])

    # load target balances into target balance object
    # the extra columns in the csv data beyond the contractual feature headers are target balances by period
    data_count = len(data_list)
    targetBalanaces = []
    for i in range(headers_count, data_count):
        string_value = str(data_list[i])
        data_value = float(string_value)
        targetBalanaces.append(BalTarget(i - headers_count + 1, data_value))
    setattr(transactionLevelData, "targetBalance", targetBalanaces)

    return transactionLevelData


'''======================================== Google Cloud Integration Module ========================================='''

# the overarching design is that the transactionLevelData object gets passed through the pipeplie
# at each stage of the pipeline, additional attributes are added containing results from that stage

def AddTransaction(transactionLevelData, transaction):
    if hasattr(transactionLevelData, 'transactions'):
        transactionLevelData.transactions.append(transaction)
    else:
        setattr(transactionLevelData, "transactions", [transaction])
    return transactionLevelData


def AddProduct(transactionLevelData, i):
    # initiate transaction level data, only the data (at position 0) is requried as the target balance is for FutureProduct
    transaction = transactionLevelData.transactions[i]
    product = TransactionToProduct(transaction)

    if hasattr(transactionLevelData, 'Products'):
        transactionLevelData.Products.append(product)
    else:
        setattr(transactionLevelData, "Products", [product])
    return transactionLevelData

def AddCashflows(transactionLevelData, i, evaluationDate, indexDict):
    product = transactionLevelData.Products[i]
    # cashflows is a list of cashlfow object, each object has pay date, pay amount, etc
    cashflows = product.getCashflows(evaluationDate, indexDict)

    if hasattr(transactionLevelData, 'CashflowResults'):
        transactionLevelData.CashflowResults.append(cashflows)
    else:
        setattr(transactionLevelData, "CashflowResults", [cashflows])
    return transactionLevelData

def AddIncomes(transactionLevelData, i):
    cashflows = transactionLevelData.CashflowResults[i]
    transaction = transactionLevelData.transactions[i]
    # incomes is a list of income object, each object has calendar date, accrual amount, etc
    incomes = IncomeAccrual(cashflows, transaction).getIncomes()

    if hasattr(transactionLevelData, 'IncomesResults'):
        transactionLevelData.IncomesResults.append(incomes)
    else:
        setattr(transactionLevelData, "IncomesResults", [incomes])
    return transactionLevelData

def AddNewVolumes(transactionLevelData, runParameters, indexDict):
    projectionPeriod = runParameters['projectionPeriod']
    maxHorizon = runParameters['maxHorizon']
    reportingDate = runParameters['reportingDate']
    evaluationDate = reportingDate
    # cashflowsResults is the Cashflows attribute of the transaction level data object
    # it's a list (by individual existing / new deals) of lists (by payment timing) of object (individual cashflow)
    cashflowsResults = transactionLevelData.CashflowResults
    transaction = transactionLevelData.transactions[0]

    # create list to contain remaining balance
    remainingTotal = [0]*maxHorizon

    # loop through future projection periods, creating new business each period
    # complete projection of each deal is calculated at the period of its origination
    # TD this deal by deal method should be evaluated against period by period
    NIItargetBal = transactionLevelData.targetBalance
    for i in range(0, projectionPeriod):

        monthEndTarget = NIItargetBal[i].balance
        cashflows = cashflowsResults[i]
        # payment date is the first
        # TD how does this work if payment frequency is quarterly or longer?
        payDate = cashflows[0].paymentDate

        # store remaining amounts of  transaction into remaining total list
        for j in range(i, len(cashflows) + i):
            remainingTotal[j] += cashflows[j - i].remaining
        remaining = remainingTotal[i]

        # create new business transaction data
        newTransaction = NewBusiness(payDate, remaining, monthEndTarget, transaction, indexDict)
        # set current transaction to new transaction for next iteration
        transaction = newTransaction

        # TD rebuild reporting date dependency (eg a separate evaluation date)
        evaluationDate += relativedelta(day=1, months=+2, days=-1)

        AddTransaction(transactionLevelData, transaction)
        AddProduct(transactionLevelData, i+1)
        AddCashflows(transactionLevelData, i+1, evaluationDate, indexDict)
        AddIncomes(transactionLevelData, i+1)

    return transactionLevelData



# to dos
'''
def ToDo():


    # output income results
    incomeOutput.write(incomes[l].AsCsv()[0] + "\n")

    # update log variable for existing deal count
    existingDealCount += 1

    # add counter to log variable
    cashflowLineCount += 1

    # add counter to log variable
    incomeLineCount += 1

    # update log variable for new deal count
    newDealCount += 1


    endTime = datetime.now()
    duration = endTime - startTime

    #close output file after all cashflows are appended
    cashflowOutput.close()
    incomeOutput.close()

    #calculate output file size, in MB
    cashflowFileSize = float(stat(cashflowFile).st_size) / (1024 ** 2)
    incomeFileSize = float(stat(incomeFile).st_size) / (1024 ** 2)

    #update log file
    logContent = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(str(startTime), str(endTime), str(duration), product,
                                                                  existingDealCount, newDealCount, cashflowLineCount,
                                                                  incomeLineCount, cashflowFileSize, incomeFileSize)
    logOuput.write(logContent + "\n")
    # TD write output file size into log

    logOuput.close()

    # initiate csv files to store output
    outputFormat = runParameters['outputFormat']
    cashflowFile = runParameters['cashflowOutputPath'] + product + "_" + runTime + outputFormat
    cashflowOutput = open(cashflowFile, "a+")
    incomeFile = runParameters['incomeOutputPath'] + product + "_" + runTime + outputFormat
    incomeOutput = open(incomeFile, "a+")
    # initiate csv file for logging at the product level
    # TD consider what variables to log and at what level
    logFile = runParameters['logOutputPath'] + outputFormat
    logOuput = open(logFile, "a+")

    # add field names to output files
    cashflowOutput.write(runParameters['cashflowOutputHeader'] + "\n")
    incomeOutput.write(runParameters['incomeOutputHeader'] + "\n")
    logOuput.write(runParameters['logOutputHeader'] + "\n")
'''

def run():
    # initial log variables
    existingDealCount = 0
    newDealCount = 0
    cashflowLineCount = 0
    incomeLineCount = 0

    startTime = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print('run start time: ' + startTime)

    '''initiate run time variables'''
    runParameters = loadRunParameters()
    reportingDate = runParameters['reportingDate']
    shock = runParameters['shock']
    runner = runParameters['runner']
    job_name = runParameters['jobName']
    data_source = runParameters['dataSource']
    num_worker = int(runParameters['num_workers'])
    autoscaling = runParameters['autoscaling']

    # initiate curve and index objects
    curveDict = createCurveDict(reportingDate, shock)
    indexDict = createIndexDict(reportingDate, curveDict)


    # create test data
    # TD replace by a data load / processing step
    dataDefinitions = runParameters['dataDefinitions']
    data = CreateData(reportingDate, dataDefinitions)

    # configure output / runner options based on user input
    if runner == 'DataflowRunner':
        inputTransactionData = runParameters['cloudTransactionDate']
        outputCashflowPath = runParameters['cloudCashflowOutput'] + startTime + '/cashflow_output.csv'
        outputIncomePath = runParameters['cloudIncomeOutput'] + startTime + '/income_output.csv'
    else:
        inputTransactionData = runParameters['localTransactionData']
        outputCashflowPath = runParameters['localCashflowOutput'] + startTime + '.csv'
        outputIncomePath = runParameters['localIncomeOutput'] + startTime + '.csv'

    parser = argparse.ArgumentParser()

    # input not required
    # parser.add_argument('--input',
    # dest='input',
    # default='gs://dataflow-samples/shakespeare/kinglear.txt',
    # help='Input file to process.')
    parser.add_argument('--inputTransactionData',
                        dest='inputTransactionData',
                        # CHANGE 1/5: The Google Cloud Storage path is required
                        # for outputting the results.
                        # output paths for dataflow / direct runner are configured above
                        default=inputTransactionData,
                        help='input transaction data file.')
    parser.add_argument('--outputCashflow',
                        dest='outputCashflow',
                        # CHANGE 1/5: The Google Cloud Storage path is required
                        # for outputting the results.
                        # output paths for dataflow / direct runner are configured above
                        default=outputCashflowPath,
                        help='Output file to write Cashflow results to.')
    parser.add_argument('--outputIncome',
                        dest='outputIncome',
                        # CHANGE 1/5: The Google Cloud Storage path is required
                        # for outputting the results.
                        # output paths for dataflow / direct runner are configured above
                        default=outputIncomePath,
                        help='Output file to write Income results to.')
    

    known_args, pipeline_args = parser.parse_known_args(None)
    # '--num_workers=500' can be used to force higher distribution, must not have any spaces in the parameter def
    pipeline_args.extend([
        '--runner={0}'.format(runner),
        '--project=sweetgooseberry-145819',
        '--staging_location=gs://sweet-gooseberry-upload/IRR_CF_Engine/staging',
        '--temp_location=gs://sweet-gooseberry-upload/IRR_CF_Engine/temp/',
        '--job_name={0}'.format(job_name + startTime),
        '--autoscaling_algorithm={0}'.format(autoscaling),
        '--num_workers={0}'.format(num_worker)
    ])
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True

    # TD when reading / writing with BigQuery, need to have explicit schema

    p = beam.Pipeline(options=pipeline_options)

    # no comments can be added in between the pipeline process below
    # each row in pipeline takes the output from previous
    # 170725 1230 output options CashflowResults, IncomesResults

    # 170726 1548 ability to choose either generate data in memory or load from csv
    # both data methods generate PCollection, a large "bag" (ie un-ordered) of elements, which can be distributed freely
    if data_source == "GenerateData":
        load_transaction_data = p | 'Create transaction level data' >> beam.Create(data)
    else:
        load_transaction_data = (p
                                 | 'Load csv transaction data' >> beam.io.ReadFromText(known_args.inputTransactionData)
                                 | 'Convert into objects' >> beam.Map(lambda csvData: CreateRunObjects(csvData, runParameters)))

    # run existing volume cashflow and income
    run_existing_volume = (load_transaction_data
                           | 'Add existing vol product' >> beam.Map(lambda transactionLevelData: AddProduct(transactionLevelData, 0))
                           | 'Add existing vol cashflows' >> beam.Map(
        lambda transactionLevelData: AddCashflows(transactionLevelData, 0, reportingDate, indexDict))
                           | 'Add existing vol incomes' >> beam.Map(lambda transactionLevelData: AddIncomes(transactionLevelData, 0)))

    # run new volume projection (ie create new transactions, calculate their cashflow and income)
    run_new_volume = run_existing_volume | 'Add new vol cashflows and incomes' >> beam.Map(lambda transactionLevelData: AddNewVolumes(transactionLevelData, runParameters, indexDict))

    # convert to output format for writing to storage
    output_results = (run_new_volume
                      | 'Generate existing vol income results' >> beam.FlatMap(lambda transactionLevelData: transactionLevelData.CashflowResults)
                      | 'To text' >> beam.FlatMap(lambda results: ListToCSV(results)))

    # write output to storage
    output_results | 'Save results' >> beam.io.WriteToText(known_args.outputCashflow)

    p.run();

    endTime = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print('run end time: ' + endTime)

'''======================================== Execution Module ========================================='''

if __name__ == "__main__":

    run()


# performance
# data volume       dataflow(min)       direct(mins)
# 30                5                   0.1 (instant)
# 300000            8 / 9               3
# consecutaive runs can be triggered without noticable effect on run time
# when triggering from the same laptop, runs can be 4 min apart, no change in per run performance

# triggering python script takes 3m to start running 300k on gcp
# running on cloud takes 8 mins per 300k records

# trigger python script takes 8m to start running 600k on gcp (seems to be max limit)
# running on cloud takes 12 mins per 600k records

# local initiation of 300 lines is 1 min
# income generation for 300 lines is 5 mins

# income generate on gcp for 300k is 12 mins

# full planning run 30k existing for 15 mins

# 1500000
# 3000000


'''
job name    sweetgooseberry-145819-irr-test-2017-07-27-22-48-39
workers     15
time        22 min
volume      3x100k 90 MB (uploaded data)
cf size     6.2 GB

job name    sweetgooseberry-145819-irr-test-2017-07-28-06-00-22     
workers     15
time        2.5 hr
volume      3x1 mil 900 MB (uploaded data)
cf size     62 GB

job name    sweetgooseberry-145819-irr-test-2017-07-28-07-52-34
workers     15 (even if num_works is set to 500)
time        2.25 hr
volume      3x1 mil 900 MB (uploaded data)

job name    sweetgooseberry-145819-irr-test-100-2017-07-28-22-19-21
workers     23 (autoscaler turned off)
time        1.25 hr
volume      3x1 mil (uploaded data)

job name    sweetgooseberry-145819-irr-test-30x100-2017-07-29-06-59-00
workers     22 (target 23)
time        4.5 min
volume      3x100 900 KB (cloud generated data)
cf size     64 MB

job name    sweetgooseberry-145819-irr-test-30x100k-2017-07-29-07-33-52
workers     22 (target 23)
time        1.5 hr
volume      30x100k 900MB (cloud generated data)
cf size     129 files 64GB


distribution limitation
- environment used (sweetgoosberry) doesn't seem to distribute beyong 15 workers
- in contrast to millions of data, this distribution is minimal
- could consider less distributed methods (eg reinvest at the node level instead of existing deal level)
- although distribution can be manually set, this has high risks, especially when total use approaches limit, better let google's autoscaler set it

cloud file management
- similar to hadoop big data cluster, files (in the common sense) should be folders on google cloud
- wild card is then used to refer to  all files in that folder (eg /*)
- if output files are unique (at the batch level) then folders should be used as deleting 50 out of 400 files is hard



'''