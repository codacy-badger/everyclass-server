"""
This is module to generate .ics file. Should follow RFC2445 standard.
https://tools.ietf.org/html/rfc2445
"""
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Tuple

import pytz
from icalendar import Alarm, Calendar, Event, Timezone, TimezoneStandard

from everyclass.server.config import get_config
from everyclass.server.db.model import Semester
from everyclass.server.utils import get_time

tzc = Timezone()
tzc.add('tzid', 'Asia/Shanghai')
tzc.add('x-lic-location', 'Asia/Shanghai')
tzs = TimezoneStandard()
tzs.add('tzname', 'CST')
tzs.add('dtstart', datetime(1970, 1, 1, 0, 0, 0))
tzs.add('TZOFFSETFROM', timedelta(hours=8))
tzs.add('TZOFFSETTO', timedelta(hours=8))


def generate(student_name: str, courses: Dict[Tuple[int, int], list], semester: Semester, ics_token: str):
    """
    生成 ics 文件并保存到目录

    :param ics_token: ics 令牌
    :param student_name: 姓名
    :param courses: classes student are taking
    :param semester: 当前导出的学期
    :return: None
    """
    semester_string = semester.to_str(simplify=True)
    semester = semester.to_tuple()

    # 创建 calender 对象
    cal = Calendar()
    cal.add('prodid', '-//Admirable//EveryClass//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', student_name + '的' + semester_string + '课表')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')

    # 时区
    tzc.add_component(tzs)
    cal.add_component(tzc)

    # 创建 events
    for time in range(1, 7):
        for day in range(1, 8):
            if (day, time) in courses:
                for course in courses[(day, time)]:
                    for week in course['week']:
                        dtstart = _get_datetime(week, day, get_time(time)[0], semester)
                        dtend = _get_datetime(week, day, get_time(time)[1], semester)

                        if dtstart.year == 1984:
                            continue

                        cal.add_component(_build_event(course_name=course['name'],
                                                       times=(dtstart, dtend),
                                                       classroom=course['classroom'],
                                                       teacher=course['teacher'],
                                                       week_string=course['week_string'],
                                                       current_week=week,
                                                       cid=course['cid']))

    # 写入文件
    import os

    with open(os.path.join(os.path.dirname(__file__),
                           '../../../calendar_files/{}.ics'.format(ics_token)),
              'w') as f:
        f.write(cal.to_ical().decode(encoding='utf-8'))


def _get_datetime(week: int, day: int, time: Tuple[int, int], semester: Tuple[int, int, int]) -> datetime:
    """
    输入周次，星期、时间tuple（时,分），输出datetime类型的时间

    :param week: 周次
    :param day: 星期
    :param time: 时间tuple（时,分）
    :param semester: 学期
    :return: datetime 类型的时间
    """
    config = get_config()
    tz = pytz.timezone("Asia/Shanghai")
    dt = datetime(*(config.AVAILABLE_SEMESTERS[semester]['start'] + time), tzinfo=tz)  # noqa: T484
    dt += timedelta(days=(week - 1) * 7 + (day - 1))  # 调整到当前周

    if 'adjustments' in config.AVAILABLE_SEMESTERS[semester]:
        ymd = (dt.year, dt.month, dt.day)
        adjustments = config.AVAILABLE_SEMESTERS[semester]['adjustments']
        if ymd in adjustments:
            if adjustments[ymd]['to']:
                # 调课
                dt = dt.replace(year=adjustments[ymd]['to'][0],
                                month=adjustments[ymd]['to'][1],
                                day=adjustments[ymd]['to'][2])
            else:
                # 冲掉的课年份设置为1984，返回之后被抹去
                dt = dt.replace(year=1984)

    return dt


def _build_event(course_name: str, times: Tuple[datetime, datetime], classroom: str, teacher: str, current_week: int,
                 week_string: str, cid: str) -> Event:
    """
    生成 `Event` 对象

    :param course_name: 课程名
    :param times: 开始和结束时间
    :param classroom: 课程地点
    :param teacher: 任课教师
    :return: `Event` 对象
    """

    event = Event()
    event.add('transp', 'TRANSPARENT')
    summary = course_name
    if classroom != 'None':
        summary = course_name + '@' + classroom
        event.add('location', classroom)

    description = week_string
    if teacher != 'None':
        description += '\n教师：' + teacher
    description += '\n由 EveryClass 每课 (https://everyclass.xyz) 导入'

    event.add('summary', summary)
    event.add('description', description)
    event.add('dtstart', times[0])
    event.add('dtend', times[1])
    event.add('last-modified', datetime.now())

    # 使用"cid-当前周"作为事件的超码
    event_sk = cid + '-' + str(current_week)
    event['uid'] = hashlib.md5(event_sk.encode('utf-8')).hexdigest() + '@everyclass.xyz'
    alarm = Alarm()
    alarm.add('action', 'none')
    alarm.add('trigger', datetime(1980, 1, 1, 3, 5, 0))
    event.add_component(alarm)
    return event
