import json
import six

from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.forms.util import flatatt
from django.utils.encoding import force_text
from django import forms


class ReadOnlyWidget(forms.Widget):

    def __init__(self, attrs=None, **kwargs):
        self.show_text = kwargs.pop('show_text', None)
        super(ReadOnlyWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        content = ''
        if value is not None:
            content = value
        if self.show_text is not None:
            content = self.show_text
        final_attrs = self.build_attrs(attrs)
        # TODO: Django >1.4:
        # return format_html('<span{0}>{1}</span>',
        #    flatatt(final_attrs),
        #    force_text(content))
        return mark_safe('<span{0}>{1}</span>'.format(
            conditional_escape(flatatt(final_attrs)),
            conditional_escape(force_text(content))
        ))


class InfoWidget(forms.Widget):
    def __init__(self, attrs=None, **kwargs):
        self.show_text = kwargs.pop('show_text', None)
        super(InfoWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        content = ''
        if value is not None:
            content = value
        if self.show_text is not None:
            content = self.show_text
        final_attrs = self.build_attrs(attrs)

        return mark_safe('<span{0}>{1}</span>'.format(
            flatatt(final_attrs),
            force_text(content)
        ))


class OptionsWidget(forms.MultiWidget):

    def __init__(self, option_names, widgets, attrs=None):
        self.option_names = option_names
        super(OptionsWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        mapping = json.loads(value) if value else {}
        return [mapping.get(key, None) for key in self.option_names]

    def format_output(self, rendered_widgets, id_):
        output = []
        i = 0
        for n, (r, w) in six.moves.zip(self.option_names, rendered_widgets):
            # TODO: Django >1.4:
            #output.append(format_html('<label for="{0}_{1}">{2}:</label>{3}',
            #    w.id_for_label(id_), i, n, r))
            output.append(
                mark_safe('<label for="{0}_{1}">{2}:</label>{3}'.format(
                    conditional_escape(w.id_for_label(id_)),
                    conditional_escape(i),
                    conditional_escape(n),
                    conditional_escape(r)
                )))

            i += 1
        return mark_safe('<div style="display:inline-block;">' +
            ('<br />\n'.join(output)) + '</div>')

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            rendered = widget.render(name + '_%s' % i, widget_value,
                final_attrs)
            output.append((rendered, widget))
        return mark_safe(self.format_output(output, id_))
