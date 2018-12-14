"""
日历相关函数
"""

import elasticapm
from flask import Blueprint


cal_blueprint = Blueprint('calendar', __name__)


@cal_blueprint.route('/calendar/<string:url_sid>/<string:url_semester>')
def cal_page(url_sid, url_semester):
    """课表导出页面视图函数"""
    from werkzeug.wrappers import Response
    from flask import current_app as app, render_template

    from everyclass.server.db.model import Semester
    from everyclass.server.utils.rpc import HttpRpc

    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_error_handle('{}/v1/student/{}/{}'.format(app.config['API_SERVER'],
                                                                                 url_sid,
                                                                                 url_semester))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

        # todo generate calendar token

        return render_template('ics.html',
                               calendar_token='token',
                               semester=Semester(url_semester).to_str(simplify=True)
                               )


@cal_blueprint.route('/calendar/_ics/<calendar_token>.ics')
def ics_download(calendar_token):
    """
    iCalendar ics file download
    """
    from flask import flash, redirect, send_from_directory, url_for

    from everyclass.server.calendar import ics_generator
    from everyclass.server.db.dao import check_if_stu_exist, get_my_semesters, get_classes_for_student
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import IllegalSemesterException
    from everyclass.server import logger

    # todo ics download

    # 学号检测

    if not check_if_stu_exist(student_id):
        flash("{} 学号不存在".format(student_id))
        logger.warning("[ics] {} 学号不存在".format(student_id))
        return redirect(url_for("main.main"))

    # 学期检测
    my_available_semesters, student_name = get_my_semesters(student_id)
    try:
        semester = Semester(semester_str)
    except IllegalSemesterException:
        flash("{} 学期格式错误".format(semester_str))
        logger.warning("{} 学期格式错误".format(semester_str))
        return redirect(url_for("main.main"))
    if semester not in my_available_semesters:
        flash("{} 学期不适用于此学生".format(semester_str))
        logger.warning("{} 学期不适用于此学生".format(semester_str))
        return redirect(url_for("main.main"))

    student_classes = get_classes_for_student(student_id, semester)
    ics_generator.generate(student_id,
                           student_name,
                           student_classes,
                           semester.to_str(simplify=True),
                           semester.to_tuple()
                           )

    return send_from_directory("../../calendar_files", student_id + "-" + semester_str + ".ics",
                               as_attachment=True,
                               mimetype='text/calendar')


@cal_blueprint.route('/calendar/_ics/androidClient/<url_xh>.ics')
def android_client_get_ics(url_xh):
    """android client get ics"""
    pass


@cal_blueprint.route('/<student_id>-<semester_str>.ics')
def get_ics(student_id, semester_str):
    """
    legacy iCalendar download
    """
    from flask import flash, redirect, send_from_directory, url_for

    from everyclass.server.calendar import ics_generator
    from everyclass.server.db.dao import check_if_stu_exist, get_my_semesters, get_classes_for_student
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import IllegalSemesterException
    from everyclass.server import logger

    # fix parameters
    place = student_id.find('-')
    semester_str = student_id[place + 1:len(student_id)] + '-' + semester_str
    student_id = student_id[:place]

    # 学号检测
    if not check_if_stu_exist(student_id):
        flash("{} 学号不存在".format(student_id))
        logger.warning("[ics] {} 学号不存在".format(student_id))
        return redirect(url_for("main.main"))

    # 学期检测
    my_available_semesters, student_name = get_my_semesters(student_id)
    try:
        semester = Semester(semester_str)
    except IllegalSemesterException:
        flash("{} 学期格式错误".format(semester_str))
        logger.warning("{} 学期格式错误".format(semester_str))
        return redirect(url_for("main.main"))
    if semester not in my_available_semesters:
        flash("{} 学期不适用于此学生".format(semester_str))
        logger.warning("{} 学期不适用于此学生".format(semester_str))
        return redirect(url_for("main.main"))

    student_classes = get_classes_for_student(student_id, semester)
    ics_generator.generate(student_id,
                           student_name,
                           student_classes,
                           semester.to_str(simplify=True),
                           semester.to_tuple()
                           )

    return send_from_directory("../../calendar_files", student_id + "-" + semester_str + ".ics",
                               as_attachment=True,
                               mimetype='text/calendar')

