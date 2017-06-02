from __future__ import absolute_import

import apache_beam as beam
import argparse
import logging
import re

from apache_beam.io.gcp.internal.clients import bigquery
from datetime import timedelta, date, datetime
from dateutil.relativedelta import *
from apache_beam.io import ReadFromText
from apache_beam.io import WriteToText
from apache_beam.metrics import Metrics
from apache_beam.metrics.metric import MetricsFilter
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions

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
        self.init()


    def shock(self, id, bps):
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
        result = 1.0/pow((1.0 + self.tenorDict[date]), self.dayCountFunc(date, self.reportingDate))
        return result

    def fr(self, fromDate, toDate, annualise = True):
        """Returns the annualised forward rate between two dates"""
        if annualise:
            annualisationFactor = 1.0/self.dayCountFunc(toDate, fromDate)
        else:
            annualisationFactor = 1.0
        result = pow(self.df(fromDate) / self.df(toDate) , annualisationFactor) - 1
        return result

    def __add__(self, other):
        """Defines addition of two curves - used to shock"""
        pass


class Scenario:
    
    def __init__(self, reportingDate, curve):
        self.reportingDate = reportingDate
        self.curve = curve


class FloatLeg:

    def __init__(self, id, settlementDate, maturityDate, paymentFrequency, notional = 1, spread = 0):
        self.id = id
        self.settlementDate = settlementDate
        self.maturityDate = maturityDate
        self.paymentFrequency = paymentFrequency
        self.notional = notional
        self.spread = spread
        self.payDates = []
        self.initPayDates()

    def initPayDates(self):
        stopDate = self.settlementDate
        curDate = self.maturityDate
        while curDate > stopDate:
            curDate = curDate + relativedelta(months = -self.paymentFrequency)
            # Add modified following
            if curDate >= stopDate:
                self.payDates.append(curDate)
        self.payDates.reverse()

    def getCashflows(self, reportingDate, curve):
        cashflows = []
        for i in range(0, len(self.payDates) - 1):
            curDate = self.payDates[i]
            if curDate <= reportingDate:
                continue
            prevDate = self.payDates[i-1]
            if prevDate < reportingDate:
                prevDate = reportingDate
            payment = curve.fr(prevDate, curDate) * self.notional
            cashflows.append(Cashflow(self.id, curDate, payment, None, None))
        return cashflows


class LevelPay(FloatLeg):

    def __init__(self, id, settlementDate, maturityDate, paymentFrequency, notional = 1, spread = 0, firstCoupon = None):
        FloatLeg.__init__(self, id, settlementDate, maturityDate, paymentFrequency, notional, spread)
        self.firstCoupon = firstCoupon

    def getCashflows(self, reportingDate, remainingAmount, curve):
        cashflows = []
        n = len(self.payDates)
        for i in range(0, n - 1):
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
                r = self.firstCoupon
            else:
                r = curve.fr(prevDate, curDate, False) + self.spread
            A = pow(1 + r, n)
            interest = remainingAmount * r
            payment = remainingAmount * r * A / (A-1)
            principal = payment - interest
            remainingAmount = remainingAmount - principal
            n = n - 1

            cashflows.append(Cashflow(self.id, curDate, interest, principal, remainingAmount))
        return cashflows        


class Cashflow:

    def __init__(self, id, paymentDate, interest, principal, remaining):        
        self.id = id
        self.paymentDate = paymentDate
        self.interest = interest
        self.principal = principal
        self.remaining = remaining

    def AsCsv(self):
        result = "{0},{1},{2},{3},{4}".format(self.id, self.paymentDate, self.interest, self.principal, self.remaining)
        return [result]

    def AsDict(self):
        dict = {}
        dict['id'] = self.id
        dict['paymentDate'] = str(self.paymentDate)
        dict['interest'] = self.interest
        dict['principal'] = self.principal
        dict['remaining'] = self.remaining
        return dict

class Object(object):
    pass


def CreateData(reportingDate, count):
    result = []
    for i in range(0, count):
        item = Object()
        item.id = i
        item.settlementDate = date(2016, 7, 15)
        setattr(item, "maturityDate", date(2046,12,15))
        setattr(item, "paymentFrequency", 1)
        setattr(item, "notional", 1000000)
        setattr(item, "spread", 0.025/12)
        setattr(item, "firstCoupon", 0.035/12)
        setattr(item, "remainingAmount", 1000000)
        result.append(item)
    return result


def ToLevelPay(data):
    value = LevelPay(data.id, data.settlementDate, data.maturityDate, data.paymentFrequency, data.notional, data.spread, data.firstCoupon)
    setattr(data, "product", value)
    return data

def CsvToData(line):
    (id, settlementDate, maturityDate, paymentFrequency, notional, spread, firstCoupon, remainingAmount) = line.split(',')
    data = Object()
    data.id = id
    data.settlementDate = datetime.strptime(settlementDate, '%Y-%m-%d').date()
    data.maturityDate = datetime.strptime(maturityDate, '%Y-%m-%d').date()
    data.paymentFrequency = int(paymentFrequency)
    data.notional = float(notional)
    data.spread = float(spread)
    data.firstCoupon = float(firstCoupon)
    data.remainingAmount = float(remainingAmount)
    return data

def DictToData(dict):
    data = Object()
    data.id = str(dict['id'])
    data.settlementDate = datetime.strptime(dict['settlementDate'], '%Y-%m-%d').date()
    data.maturityDate = datetime.strptime(dict['maturityDate'], '%Y-%m-%d').date()
    data.paymentFrequency = dict['paymentFrequency']
    data.notional = dict['notional']
    data.spread = dict['spread']
    data.firstCoupon = dict['firstCoupon']
    data.remainingAmount = dict['remainingAmount']
    return data

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

def addParameter(obj, name, value):
    setattr(obj, name, value)
    return obj

def addField(schema, name, type = 'string', nullability = 'nullable'):
    field = bigquery.TableFieldSchema()
    field.name = name
    field.type = type
    field.mode = nullability
    schema.fields.append(field)    

def getSchema():
    schema = bigquery.TableSchema()
    addField(schema, 'id')
    addField(schema, 'paymentDate', 'STRING')
    addField(schema, 'principal', 'FLOAT')
    addField(schema, 'interest', 'FLOAT')
    addField(schema, 'remaining', 'FLOAT')
    return schema        

def run(runner):
    reportingDate = date(2016, 12, 31)
    curve = getCurve(reportingDate)
    parser = argparse.ArgumentParser()
    known_args, pipeline_args = parser.parse_known_args(None)
    pipeline_args.extend([
        '--runner={0}'.format(runner),
        '--project=igneous-primacy-146120',
        '--staging_location=gs://igneous-primacy-146120-test-bucket/staging',
        '--temp_location=gs://igneous-primacy-146120-test-bucket/temp',
        '--job_name=irrbb2',
        '--num_workers=50',
    ])
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True
    schema = getSchema()
    pp = beam.Pipeline(options = pipeline_options)
#        | 'Read products' >> beam.io.ReadFromText('gs://igneous-primacy-146120-test-bucket/temp/products.csv', skip_header_lines = 1) \
#        | 'Read products' >> beam.io.Read(beam.io.BigQuerySource(query='SELECT * FROM cashflow.bq_products LIMIT 100', use_standard_sql = True)) \
    pp \
        | 'Read products' >> beam.io.Read(beam.io.BigQuerySource(dataset='cashflow', table='bq_products')) \
        | 'Line to data' >> beam.Map(DictToData) \
        | 'Add reporting date' >> beam.Map(lambda x: addParameter(x, "reportingDate", reportingDate)) \
        | 'Convert to LevelPay' >> beam.Map(ToLevelPay) \
        | 'Generate cashflows' >> beam.FlatMap(lambda data: data.product.getCashflows(data.reportingDate, data.remainingAmount, curve)) \
        | 'To text' >> beam.Map(lambda x: x.AsDict()) \
        | 'Save results' >> beam.io.Write(beam.io.BigQuerySink(schema = schema, table='irrbb_results', dataset='cashflow', create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED, write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE))
#        | 'Save results' >> beam.io.WriteToText('gs://igneous-primacy-146120-test-bucket/temp/cashflows', file_name_suffix='csv')

    pp.run();

if __name__ == "__main__":
    #run('DirectRunner')
    run('DataflowRunner')
