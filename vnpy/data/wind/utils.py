# encoding: UTF-8

import datetime


def get_modified_date():
    '''
    获取当前时间的字符串形式
    :return:
    '''
    modified_date = datetime.datetime.now()
    modified_date = modified_date.strftime("%Y-%m-%d %H:%M:%S")
    return modified_date

def split_dt_list(start_dt, end_dt):
    '''
    根据输入的日期,输出分割的日期，按照月分割
    :param dt:
    :return:
    '''
    # s = datetime.datetime.strptime(start_dt, "%Y-%m-%d %H:%S:%M")
    # end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d %H:%S:%M")
    s = datetime.datetime.strptime(start_dt, "%Y%m%d")
    end_dt = datetime.datetime.strptime(end_dt, "%Y%m%d")
    r_data = []
    while True:
        e = s + datetime.timedelta(days=30)
        if e >= end_dt:
            e = end_dt
            e = e.replace(hour=23, minute=59)
            r_data.append((s.strftime("%Y-%m-%d %H:%M:%S"), e.strftime("%Y-%m-%d %H:%M:%S")))
            break

        e = e.replace(hour=23, minute=59)
        r_data.append((s.strftime("%Y-%m-%d %H:%M:%S"), e.strftime("%Y-%m-%d %H:%M:%S")))
        s = e.replace(hour=0, minute=0) + datetime.timedelta(days=1)
    return r_data