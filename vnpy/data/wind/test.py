# encoding: UTF-8

from vnpy.data.wind.vnwind import WindApi


start_date="20171205"
end_date = "20171211"

api = WindApi()

# a = api.get_minute_bar(symbol="T1803", start_date="2017-12-05 09:00:00", end_date="2017-12-11 09:02:01")
a = api.download_minute_bar(symbol="T1803", start_date=start_date, end_date=end_date)
print(a)