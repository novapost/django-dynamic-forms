# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import six

from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from dynamic_forms.formfields import dynamic_form_field_registry
from dynamic_forms.models import (FormFieldModel, FormModel, FormModelData,
                                  FormFieldSetModel)
from dynamic_forms.widgets import ReadOnlyWidget, OptionsWidget
from django.core.exceptions import ValidationError


class TextMultipleChoiceField(forms.MultipleChoiceField):

    def to_python(self, value):
        return ','.join(value)

    def validate(self, value):
        """
        Validates that the input is a list or tuple.
        """
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')


class OptionsField(forms.MultiValueField):

    def __init__(self, meta, *args, **kwargs):
        self.option_names = []
        self.option_fields = []
        self.option_widgets = []
        initial = {}
        for name, option in sorted(meta.items()):
            self.option_names.append(name)
            initial[name] = option[1]
            formfield = option[2]
            if isinstance(formfield, forms.Field):
                self.option_fields.append(formfield)
                self.option_widgets.append(formfield.widget)
            elif isinstance(formfield, (tuple, list)):
                if isinstance(formfield[0], forms.Field):
                    self.option_fields.append(formfield[0])
                else:
                    self.option_fields.append(formfield[0]())
                if isinstance(formfield[1], forms.Widget):
                    self.option_widgets.append(formfield[1])
                else:
                    self.option_widgets.append(formfield[1]())
            elif isinstance(formfield, type):
                self.option_fields.append(formfield())
                self.option_widgets.append(formfield.widget)
        kwargs['widget'] = OptionsWidget(self.option_names,
            self.option_widgets)
        if 'initial' in kwargs:
            kwargs['initial'].update(initial)
        else:
            kwargs['initial'] = initial
        super(OptionsField, self).__init__(self.option_fields, *args, **kwargs)

    def compress(self, data_list):
        data = {}
        for name, value in six.moves.zip(self.option_names, data_list):
            if value is not None:
                data[name] = value
        return json.dumps(data)


class AdminFormFieldInlineForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        meta = None
        if instance:
            df = dynamic_form_field_registry.get(instance.field_type)
            if df:
                meta = df._meta
        super(AdminFormFieldInlineForm, self).__init__(*args, **kwargs)
        if meta is not None:
            self.fields['_options'] = OptionsField(meta, required=False,
                label=_('Options'))
        else:
            self.fields['_options'].widget = ReadOnlyWidget(show_text=_(
                'The options for this field will be available once it has '
                'been stored the first time.'
            ))


class AdminFormFieldSetInlineForm(forms.ModelForm):

    class Meta:
        model = FormFieldSetModel

    def __init__(self, *args, **kwargs):
        super(AdminFormFieldSetInlineForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)
        if instance:
            self.initial["_fields"] = instance._fields.split(',')
            # first get the fields available for this form
            available_fields = [
                a.name for a in self.instance.parent_form.fields.all()]
            #used fields are fields already in a fieldset
            used_fields = []
            for fieldset in self.instance.parent_form.fieldsets.all():
                for f in fieldset._fields.split(","):
                    if f not in self.initial["_fields"]:
                        used_fields.append(f.strip())
            available_fields = [
                f for f in available_fields if f not in used_fields]

            self.fields['_fields'] = TextMultipleChoiceField(
                choices=[(f, f) for f in available_fields])
        else:
            self.fields['_fields'].widget = ReadOnlyWidget(show_text=_(
                    'The fields will be available once it has '
                    'been stored the first time.'
                    ))


class FormFieldModelInlineAdmin(admin.StackedInline):
    extra = 3
    form = AdminFormFieldInlineForm
    list_display = ('field_type', 'name', 'label')
    model = FormFieldModel
    prepopulated_fields = {"name": ("label",)}


class FormFieldSetModelInlineAdmin(admin.StackedInline):
    extra = 1
    form = AdminFormFieldSetInlineForm
    model = FormFieldSetModel


class FormModelAdmin(admin.ModelAdmin):
    inlines = (FormFieldModelInlineAdmin, FormFieldSetModelInlineAdmin)
    list_display = ('name', 'submit_url', 'success_url')
    model = FormModel

admin.site.register(FormModel, FormModelAdmin)


class FormModelDataAdmin(admin.ModelAdmin):
    list_display = ('form', 'pretty_value', 'submitted')
    model = FormModelData

admin.site.register(FormModelData, FormModelDataAdmin)
