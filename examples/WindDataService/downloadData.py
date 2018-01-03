# encoding: UTF-8

"""
立即下载数据到数据库中，并且清洗数据，用于手动更新数据的操作
"""
from dataService import downloadAllMinuteBar
from cleanData import cleanData, repairData

if __name__ == '__main__':
    start_date = "20171201"
    end_date = None
    # 下载数据
    downloadAllMinuteBar(start_date=start_date, end_date=end_date)
    # 清洗数据
    cleanData(start_date, end_date)
    # 修复数据
    repairData(start_date, end_date)
