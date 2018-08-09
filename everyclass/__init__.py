import logging

from flask import Flask, g, render_template, send_from_directory, current_app
from flask_cdn import CDN
from htmlmin import minify
from termcolor import cprint
from raven.contrib.flask import Sentry
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler

from everyclass.config import load_config

config = load_config()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')

    # load config
    app.config.from_object(config)
    cprint('App created. Running under `{}` config'.format(app.config['CONFIG_NAME']), color='blue')

    # CDN
    CDN(app)

    # Sentry
    sentry = Sentry(app)

    # Elastic APM
    apm = ElasticAPM(app)

    # logging
    handler = LoggingHandler(client=apm.client)
    handler.setLevel(logging.WARN)
    app.logger.addHandler(handler)

    # register blueprints
    from everyclass.cal import cal_blueprint
    app.register_blueprint(cal_blueprint)

    from everyclass.query import query_blueprint
    app.register_blueprint(query_blueprint)

    from everyclass.views import main_blueprint as main_blueprint
    app.register_blueprint(main_blueprint)

    from everyclass.api import api_v1 as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    @app.teardown_appcontext
    def close_db(error):
        """结束时关闭数据库连接"""
        if hasattr(g, 'mysql_db'):
            g.mysql_db.close()

    @app.route('/<student_id>-<semester>.ics')
    def get_ics(student_id, semester):
        """serve ics file"""
        # TODO: if file not exist, try to generate one.(implement after ORM and database adjustment)
        return send_from_directory("ics", student_id + "-" + semester + ".ics",
                                   as_attachment=True,
                                   mimetype='text/calendar')

    @app.after_request
    def response_minify(response):
        """用 htmlmin 压缩 HTML，减轻带宽压力"""
        if app.config['HTML_MINIFY'] and response.content_type == u'text/html; charset=utf-8':
            response.set_data(
                minify(response.get_data(as_text=True))
            )
            return response
        return response

    @app.template_filter('versioned')
    def version_filter(filename):
        """
        模板过滤器。如果 STATIC_VERSIONED，返回类似 'style-v1-c012dr.css' 的文件，而不是 'style-v1.css'

        :param filename: 文件名
        :return: 新的文件名
        """
        if app.config['STATIC_VERSIONED']:
            if filename[:4] == 'css/':
                new_filename = app.config['STATIC_MANIFEST'][filename[4:]]
                return 'css/' + new_filename
            elif filename[:3] == 'js/':
                new_filename = app.config['STATIC_MANIFEST'][filename[3:]]
                return new_filename
            else:
                return app.config['STATIC_MANIFEST'][filename]
        return filename

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('500.html',
                               event_id=g.sentry_event_id,
                               public_dsn=sentry.client.get_public_dsn('https'))

    return app
