# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six


try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from django.utils.datastructures import SortedDict as OrderedDict

from django import forms

from dynamic_forms.formfields import dynamic_form_field_registry


class FieldSet(object):
    def __init__(self, form, title, fields, classes):
        self.form = form
        self.title = title
        self.fields = fields
        self.classes = classes

    def __iter__(self):
        # Similar to how a form can iterate through it's fields...
        for field in self.fields:
            yield field


class MultiSelectFormField(forms.MultipleChoiceField):
    # http://djangosnippets.org/snippets/2753/

    widget = forms.CheckboxSelectMultiple

    def __init__(self, *args, **kwargs):
        self.widget = kwargs.pop('widget', self.widget)
        self.separate_values_by = kwargs.pop('separate_values_by', ',')
        super(MultiSelectFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and self.required:
            raise forms.ValidationError(self.error_messages['required'])
        return value

    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value.split(self.separate_values_by)


class FormModelForm(forms.Form):

    def __init__(self, model, *args, **kwargs):
        self.model = model
        if hasattr(self.model, "fieldsets"):
            self._fieldsets = self.model.fieldsets.all()
        super(FormModelForm, self).__init__(*args, **kwargs)
        self.model_fields = OrderedDict()
        for field in self.model.fields.all():
            self.model_fields[field.name] = field
            field.generate_form_field(self)

    def get_mapped_data(self, exclude_missing=False):
        """
        Returns an dictionary sorted by the position of the respective field
        in its form.

        :param boolean exclude_missing: If ``True``, non-filled fields (those
            whose value evaluates to ``False`` are not present in the returned
            dictionary. Default: ``False``
        """
        data = self.cleaned_data
        mapped_data = OrderedDict()
        for key, field in six.iteritems(self.model_fields):
            df = dynamic_form_field_registry.get(field.field_type)
            if df and df.do_display_data():
                name = field.label
                value = data.get(key, None)
                if exclude_missing and not bool(value):
                    continue
                mapped_data[name] = value
        return mapped_data

    @property
    def fieldsets(self):
        if not hasattr(self, "fieldsets"):
            return

        for elem in self._fieldsets:
            yield FieldSet(
                form=self,
                title=elem.title,
                fields=[self[f] for f in elem._fields.split(',')],
                classes=elem.classes
                )
