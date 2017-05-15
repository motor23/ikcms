# coding: utf8
import datetime
from pytz import timezone

from babel.support import Format
import babel.dates
from babel import Locale
from jinja2 import Markup
from iktomi.utils import cached_property

from .. import base
from . import handlers
from .translation import get_translations


class Lang(str):

    def __new__(cls, component, name):
        self = str.__new__(cls, name)
        self.component = component
        self.translations = component.translations[name]
        self.format = Format(name)
        self.locale = Locale(name)
        return self

    @cached_property
    def root(self):
        return getattr(self.component.app.root, self)

    @cached_property
    def models(self):
        return {db_id: getattr(models, self, None) \
            for db_id, models in self.component.app.db.models.items()}

    @cached_property
    def url_for(self):
        return self.root.build_url

    def months(self, type='stand-alone', form='wide'):
        return self.locale.months[type][form]

    def gettext(self, msgid):
        message = self.translations.gettext(unicode(msgid))
#XXX
        if isinstance(msgid, Markup):
            message = Markup(message)
        return message

    def ngettext(self, msgid1, msgid2, n):
        message = self.translations.ngettext(
            unicode(msgid1),
            unicode(msgid2),
            n,
        )
        if isinstance(msgid1, Markup):
            message = Markup(message)
        return message

    def _(self, msgid):
        return self.gettext(msgid)

    def format_date(self, dt, format):
        return self.component.format_date(self, dt, format)

    def format_datetime(self, dt, format):
        return self.component.format_datetime(self, dt, format)

    def date(self, dt, **kwargs):
        return self.component.date(self, dt, **kwargs)

    def datetime(self, dt, **kwargs):
        return self.component.datetime(self, dt, **kwargs)

    def daterange(self, start_dt, end_dt, **kwargs):
        return self.component.daterange(self, start_dt, end_dt, **kwargs)

    def isodate(self, dt):
        return self.component.isodate(dt)



class Component(base.Component):

    name = 'i18n'
    langs = ['ru', 'en']
    translations_dir = '{ROOT_DIR}/i18n'
    categories = []
    lang_class = Lang

    DATE_FORMATS = {
        'ru': u"d MMMM y 'года'",
        'en': u"MMMM d, y",
    }

    DATE_FORMATS_NO_YEAR = {
        'ru': u"d MMMM",
        'en': u"MMMM d",
    }

    DATETIME_FORMATS = {
        'ru': u"d MMMM y 'года', HH:mm",
        'en': u"MMMM d, y, HH:mm",
    }

    DATETIME_FORMATS_NO_YEAR = {
        'ru': u"d MMMM, HH:mm",
        'en': u"MMMM d, HH:mm",
    }

    DATERANGE_FORMATS = {
        'ru': {
            # y1=?y2, m1=?m2, d1=?d2 : (format1, format2)
            ''   : (u'd MMMM y \N{EN DASH} ', u"d MMMM y 'года'"),
            'y'  : (u'd MMMM \N{EN DASH} ', u"d MMMM y 'года'"),
            'ym' : (u'd\N{EN DASH}', u"d MMMM y 'года'"),
            'ymd': (u"d MMMM y 'года'", u''),
        },
        'en': {
            ''   : (u'MMMM d, y \N{EN DASH} ', u'MMMM d, y'),
            'y'  : (u'MMMM d \N{EN DASH} ', u'MMMM d, y'),
            'ym' : (u'MMMM d\N{EN DASH}', u'd, y'),
            'ymd': (u'MMMM d, y', u''),
        },
    }

    def __init__(self, app):
        super(Component, self).__init__(app)
        self.timezone = timezone(app.cfg.TIMEZONE)
        self.translations_dir = self.translations_dir.format(**app.cfg.as_dict())
        self.translations = {lang: self._get_translations(lang) \
            for lang in self.langs}
        self.langs = {lang: self.lang_class(self, lang) for lang in self.langs}

    def _get_translations(self, lang):
        return get_translations(
            self.translations_dir,
            lang,
            self.categories,
        )

    def set_lang(self, env, lang):
        assert lang in self.langs
        setattr(env, 'lang', self.langs[lang])

    def h_lang(self, lang):
        return handlers.HLang(self, lang)

    def h_for_langs(self, *langs):
        return handlers.HForLangs(self, *langs)

    def format_date(self, locale, dt, format):
        return babel.dates.format_date(dt, format, locale=locale)

    def format_datetime(self, locale, dt, format):
        return babel.dates.format_datetime(dt, format, locale=locale)

    def date(self, locale, dt, **kwargs):
        optional_year = kwargs.get('optional_year', False)
	format = self.DATE_FORMATS[locale]
        if optional_year:
            today = datetime.date.today()
            if today.year == dt.year and (today.month, dt.month) != (12, 1):
		format = self.DATE_FORMATS_NO_YEAR[locale]
        return babel.dates.format_date(dt, format, locale=locale)

    def datetime(self, locale, dt, **kwargs):
        optional_year = kwargs.get('optional_year', False)
	format = self.DATETIME_FORMATS[locale]
        relative = kwargs.get('relative', False)
        if relative:
            delta = datetime.datetime.now() - dt
            if not delta.days:
                return babel.dates.format_timedelta(
                    -delta,
                    locale=locale,
                    add_direction=True,
                )
        if optional_year:
            today = datetime.date.today()
            if today.year == dt.year and (today.month, dt.month) != (12, 1):
		format = self.DATETIME_FORMATS_NO_YEAR[locale]
        return babel.dates.format_datetime(dt, format, locale=locale)

    def daterange(self, locale, start_dt, end_dt, **kwargs):
        if end_dt is None:
            end_dt = start_dt
        key = ''
        for attr in ['year', 'month', 'day']:
            if getattr(start_dt, attr)!=getattr(end_dt, attr):
                break
            key += attr[0]
        start_format, end_format = self.RANGE_FORMATS[locale][key]
        return self.format_date(locale, start_dt, start_format) + \
            self.format_date(lcoale, end_dt, end_format)

    def isodate(self, dt):
        return self.timezone.localize(dt).isoformat()


component = Component.create_cls
